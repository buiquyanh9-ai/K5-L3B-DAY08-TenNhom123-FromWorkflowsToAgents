"""Shape B — one ReAct agent. Student work.

Use `lab8.runtime.run_react` with max_steps=8. `decide` may pick a read tool.
It must not call `issue_refund`. After the loop, the host validates the quote
and is the only writer.

A decide() that trusts ticket text over the order row will fail hidden claims
where the customer overstates the delay or cites a superseded clause.

Per-order cap: an order may already have been refunded by an earlier claim.
The read tool `lookup_refund_history` shows how much. The host still enforces
the cap, so pass the full quote to `durability.issue_refund`, not a net amount.

Caps: stop at 8 steps. Count model calls in the Budget so cost stays comparable.

Trace contract v1 (docs/contracts.md): return a trace_path to a JSON file written in this run,
{"run_id": <same run_id>, "events": [...]}, on every return path including early
ones. `lab8.trace.Trace` does this; your own tracer is fine if it matches.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from lab8.db import connect
from lab8.durability import InjectedCrash, issue_refund
from lab8.mock_llm import complete
from lab8.runtime import run_react
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish
from lab8.trace import Trace

SHAPE = "single"
MAX_STEPS = 8


def run_claim(
    claim_id: str,
    *,
    seed: int,
    store_path: str,
    crash_at: str | None = None,
) -> RunResult:
    # TODO CP2 (student): thay stub này bằng shape single theo các bước ở docstring đầu file.
    # TODO CP3 (student): truyền crash_at vào durability.issue_refund, không bắt InjectedCrash.
    conn = connect(store_path)
    try:
        return _run(conn, claim_id, seed=seed, crash_at=crash_at)
    finally:
        conn.close()


def _make_decide(budget: Budget, seed: int, claim_id: str, trace: Trace):
    """The "model". Only picks read tools; amounts come from the DB + compute_compensation.

    State lives in this closure because run_react only passes the last tool result.
    Ticket text is never used for numbers (delay, clause, amount).
    """
    state: dict[str, Any] = {}

    def decide(seen: dict[str, Any]) -> dict[str, Any]:
        last_tool = seen.get("last_tool")
        result = seen.get("last_result") or {}
        if last_tool:
            state[last_tool] = result

        # 1. Read the claim (allowlisted view).
        if "get_claim_view" not in state:
            complete(budget, seed=seed, purpose="plan", prompt=f"read claim {claim_id}")
            return {"tool": "get_claim_view", "args": {"claim_id": claim_id}}

        claim = state["get_claim_view"]
        if not claim.get("found"):
            return {"final": {"status": "failed", "error_reason": "unknown_claim"}}
        # The model reads the ticket (cost only); it is data, not instructions.
        if "ticket_read" not in state:
            state["ticket_read"] = True
            complete(budget, seed=seed, purpose="parse", prompt=claim.get("ticket") or "")
        if not claim.get("order_id"):
            return {"final": {"status": "needs_info", "error_reason": "missing_order_id"}}

        principal_id = claim["principal_id"]
        order_id = claim["order_id"]

        # 2. Look up the order under the claimant's scope.
        if "lookup_order" not in state:
            complete(budget, seed=seed, purpose="plan", prompt=f"lookup order {order_id}")
            return {"tool": "lookup_order", "args": {"order_id": order_id, "principal_id": principal_id}}

        order_view = state["lookup_order"]
        if not order_view.get("visible"):
            return {"final": {"status": "escalated", "error_reason": order_view.get("reason")}}

        # 3. Refund history (informational; host enforces the cap).
        if "lookup_refund_history" not in state:
            complete(budget, seed=seed, purpose="plan", prompt=f"refund history {order_id}")
            return {
                "tool": "lookup_refund_history",
                "args": {"order_id": order_id, "principal_id": principal_id},
            }

        # 4. Quote from the order row, never from the ticket.
        if "compute_compensation" not in state:
            complete(budget, seed=seed, purpose="plan", prompt=f"quote {order_id}")
            return {"tool": "compute_compensation", "args": {"order": dict(order_view["order"])}}

        quote_payload = state["compute_compensation"]
        history = state["lookup_refund_history"]
        trace.add(
            "observations",
            {
                "order": order_view["order"],
                "refunded_vnd": history.get("refunded_vnd", 0),
                "refund_count": history.get("refund_count", 0),
            },
        )
        trace.add("quote", quote_payload)
        return {
            "final": {
                "status": "propose",
                "amount_vnd": int(quote_payload["amount_vnd"]),
                "reason": quote_payload.get("reason"),
            }
        }

    return decide


def _run(conn: sqlite3.Connection, claim_id: str, *, seed: int, crash_at: str | None) -> RunResult:
    budget = Budget()
    run_id = make_run_id(SHAPE, claim_id, seed)
    trace = Trace(run_id)

    def done(status: str, proposal: int, reason: str | None) -> RunResult:
        trace.add("decision", {"status": status, "proposal_amount": proposal, "reason": reason})
        return finish(
            conn,
            shape=SHAPE,
            claim_id=claim_id,
            seed=seed,
            status=status,
            proposal_amount=proposal,
            budget=budget,
            trace=trace,
            error_reason=reason,
        )

    decide = _make_decide(budget, seed, claim_id, trace)
    try:
        loop = run_react(
            conn,
            budget,
            observation={"claim": {"claim_id": claim_id}},
            decide=decide,
            max_steps=MAX_STEPS,
            worker=False,
        )
    except Exception as exc:  # run_claim must not raise (except InjectedCrash later)
        trace.add("error", {"reason": f"react_error:{type(exc).__name__}"})
        return done("failed", 0, f"react_error:{type(exc).__name__}")

    trace.add("react", {"stopped": loop["stopped"]})
    final = loop["final"]
    status = final.get("status")

    if status != "propose":
        if status in ("needs_info", "escalated"):
            complete(budget, seed=seed, purpose="draft", prompt=status)
        return done(status or "failed", 0, final.get("error_reason"))

    proposal = int(final["amount_vnd"])
    complete(budget, seed=seed, purpose="draft", prompt=f"proposal={proposal}")
    if proposal <= 0:
        return done("denied", 0, final.get("reason"))

    # Host is the only writer. Full quote, not net of earlier refunds.
    try:
        outcome = issue_refund(conn, claim_id, proposal, crash_at=crash_at)
    except InjectedCrash:
        trace.add("crash", {"at": crash_at})
        trace.write()
        raise

    if not outcome["ok"]:
        status = "failed" if outcome["conflict"] else "denied"
        return done(status, proposal, outcome["reason"])
    return done("resolved", proposal, None)
