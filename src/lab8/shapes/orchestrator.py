"""Shape C — orchestrator plus read-only investigators.

Signature (do not change):

    run_claim(claim_id, *, seed, store_path, crash_at=None) -> RunResult

Implementation details:
1. Build a handoff with `lab8.handoff.make_handoff`. Allowed tools are strictly read-only.
   Never put parent_secret, raw headers, or the full claim row into facts.
2. `lab8.runtime.run_readonly_investigators` runs those tools.
3. The orchestrator quotes from the investigator's order view and calls
   `durability.issue_refund`. Investigators have no write registry.
   Pass the full quote; the host subtracts earlier refunds on the same order.
4. Trace the sanitized handoff, not the parent context.
5. Forward crash_at to durability.issue_refund and do not catch InjectedCrash.
"""

from __future__ import annotations

import sqlite3

from lab8.db import connect
from lab8.durability import InjectedCrash, issue_refund
from lab8.handoff import make_handoff
from lab8.mock_llm import complete
from lab8.runtime import run_readonly_investigators
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish, safe_dump
from lab8.tools import get_claim_view, tool_cost
from lab8.trace import Trace


class _Trace:
    """Local wrapper around Trace so a crash can flush to disk immediately."""

    def __init__(self, run_id: str) -> None:
        self._inner = Trace(run_id)

    def add(self, kind: str, payload: dict) -> None:
        self._inner.add(kind, payload)

    def write(self) -> str:
        return self._inner.write()

    @property
    def run_id(self) -> str:
        return self._inner.run_id


def run_claim(
    claim_id: str,
    *,
    seed: int,
    store_path: str,
    crash_at: str | None = None,
) -> RunResult:
    conn = connect(store_path)
    try:
        return _run(conn, claim_id, seed=seed, crash_at=crash_at)
    finally:
        conn.close()


def _run(conn: sqlite3.Connection, claim_id: str, *, seed: int, crash_at: str | None) -> RunResult:
    budget = Budget()
    run_id = make_run_id("orchestrator", claim_id, seed)
    trace = _Trace(run_id)

    # 1. Đọc claim view an toàn qua adapter
    claim = get_claim_view(conn, claim_id)
    budget.add_tool(tool_cost())
    if not claim.get("found"):
        trace.add("error", {"reason": "unknown_claim"})
        return finish(
            conn,
            shape="orchestrator",
            claim_id=claim_id,
            seed=seed,
            status="failed",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason="unknown_claim",
        )

    # 2. Kiểm tra order_id
    if not claim.get("order_id"):
        complete(budget, seed=seed, purpose="draft", prompt="needs_info")
        trace.add("decision", {"status": "needs_info"})
        return finish(
            conn,
            shape="orchestrator",
            claim_id=claim_id,
            seed=seed,
            status="needs_info",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason="missing_order_id",
        )

    # 3. Tạo Handoff an toàn qua allowlist
    handoff = make_handoff(
        request_id=f"REQ-{claim_id}",
        claim_id=claim_id,
        task="investigate_claim_and_policy",
        facts={},
        allowed_tools=["lookup_order", "lookup_policy", "compute_compensation"],
    )
    trace.add("handoff", safe_dump(handoff))

    # 4. Giao việc cho các read-only investigators
    investigated = run_readonly_investigators(
        conn,
        budget,
        handoff,
        principal_id=claim["principal_id"],
    )
    order_view = investigated["tools"].get("lookup_order", {})
    trace.add(
        "investigator",
        {
            "lookup_order": {"visible": order_view.get("visible"), "reason": order_view.get("reason")},
            "policy_count": len((investigated["tools"].get("lookup_policy") or {}).get("policies") or []),
        },
    )

    # 5. Kiểm tra tính hợp lệ của đơn hàng
    if not order_view.get("visible"):
        complete(budget, seed=seed, purpose="draft", prompt="escalated")
        return finish(
            conn,
            shape="orchestrator",
            claim_id=claim_id,
            seed=seed,
            status="escalated",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason=order_view.get("reason"),
        )

    # 6. Lấy kết quả bồi thường từ investigator (hoặc tính từ order row)
    quote_payload = investigated["tools"].get("compute_compensation")
    if not quote_payload:
        from lab8.tools import compute_compensation

        budget.add_tool(tool_cost())
        quote_payload = compute_compensation(conn, order_view["order"])

    proposal = int(quote_payload["amount_vnd"])
    trace.add("quote", quote_payload)

    # 7. Nếu quote = 0 -> Denied, không gọi issue_refund
    if proposal <= 0:
        complete(budget, seed=seed, purpose="draft", prompt="denied_zero")
        return finish(
            conn,
            shape="orchestrator",
            claim_id=claim_id,
            seed=seed,
            status="denied",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason=quote_payload.get("reason"),
        )

    # 8. Orchestrator gọi issue_refund với quote đầy đủ và forward crash_at
    # Không bắt nuốt InjectedCrash
    try:
        outcome = issue_refund(conn, claim_id, proposal, crash_at=crash_at)
    except InjectedCrash:
        trace.add("crash", {"at": crash_at})
        trace.write()
        raise

    if not outcome["ok"]:
        status = "failed" if outcome["conflict"] else "denied"
        return finish(
            conn,
            shape="orchestrator",
            claim_id=claim_id,
            seed=seed,
            status=status,
            proposal_amount=proposal,
            budget=budget,
            trace=trace,
            error_reason=outcome["reason"],
        )

    complete(budget, seed=seed, purpose="draft", prompt=f"proposal={proposal}")
    return finish(
        conn,
        shape="orchestrator",
        claim_id=claim_id,
        seed=seed,
        status="resolved",
        proposal_amount=proposal,
        budget=budget,
        trace=trace,
        error_reason=None,
    )
