"""Dedicated tests for Shape A (workflow) and integration durability.

Verifies:
- All published trap cases pass deterministically without LLM variance.
- Zero variance on C-002 across all seeds (unlike swarm reference).
- Graceful handling of unknown claim.
- Idempotency and crash safety (T11, T12 patterns).
- Strict adherence to Trace Contract v1 without leaking secrets.
"""

from __future__ import annotations

import time
import pytest

from lab8.db import connect, init_store
from lab8.durability import InjectedCrash
from lab8.metrics import check_trace, trial_pass
from lab8.shapes.workflow import run_claim
from tests.conftest import BY_ID, CLAIMS, WORLD


def _init_store(tmp_path, name: str):
    path = tmp_path / name
    init_store(path, WORLD, CLAIMS).close()
    return path


@pytest.mark.parametrize(
    "claim_id",
    ["C-001", "C-002", "C-003", "C-004", "C-005", "C-006", "C-007", "C-008", "C-009", "C-010", "C-013", "C-014"],
)
def test_workflow_passes_all_published_cases(tmp_path, claim_id):
    store = _init_store(tmp_path, f"wf-{claim_id}.sqlite")
    started_at = time.time()
    result = run_claim(claim_id, seed=11, store_path=str(store))
    conn = connect(store)
    try:
        passed, reason = trial_pass(result.as_dict(), BY_ID[claim_id]["expected"], conn, started_at=started_at)
    finally:
        conn.close()
    assert passed, reason


def test_workflow_has_zero_variance_on_t02(tmp_path):
    """Workflow ignores user prompt delay and strictly trusts the database.

    Unlike swarm (which fails C-002 on seed 55), workflow passes on all seeds.
    """
    for seed in (11, 22, 33, 44, 55):
        store = _init_store(tmp_path, f"wf-t02-seed-{seed}.sqlite")
        started_at = time.time()
        result = run_claim("C-002", seed=seed, store_path=str(store))
        conn = connect(store)
        try:
            passed, reason = trial_pass(result.as_dict(), BY_ID["C-002"]["expected"], conn, started_at=started_at)
        finally:
            conn.close()
        assert passed, f"seed {seed} failed: {reason}"


def test_workflow_unknown_claim(tmp_path):
    store = _init_store(tmp_path, "wf-unknown.sqlite")
    started_at = time.time()
    result = run_claim("C-999-DOES-NOT-EXIST", seed=11, store_path=str(store))
    assert result.status == "failed"
    assert result.error_reason == "unknown_claim"
    assert result.proposal_amount == 0
    ok, trace_reason = check_trace(result.as_dict(), started_at=started_at)
    assert ok, trace_reason


def test_workflow_idempotent_retry(tmp_path):
    store = _init_store(tmp_path, "wf-idempotent.sqlite")
    first = run_claim("C-001", seed=11, store_path=str(store))
    assert first.status == "resolved"

    started_at = time.time()
    second = run_claim("C-001", seed=11, store_path=str(store))
    assert second.status == "resolved"

    conn = connect(store)
    try:
        passed, reason = trial_pass(second.as_dict(), BY_ID["C-001"]["expected"], conn, started_at=started_at)
        count = conn.execute("SELECT COUNT(*) AS n FROM refund_ledger WHERE claim_id = 'C-001'").fetchone()["n"]
        audit_count = conn.execute(
            "SELECT COUNT(*) AS n FROM audit_events WHERE claim_id = 'C-001' AND event_type = 'refund_committed'"
        ).fetchone()["n"]
    finally:
        conn.close()

    assert passed, reason
    assert count == 1
    assert audit_count == 1


def test_workflow_crash_recovery_preserves_durability(tmp_path):
    store = _init_store(tmp_path, "wf-crash.sqlite")
    crashed = False
    try:
        run_claim(
            "C-001",
            seed=11,
            store_path=str(store),
            crash_at="after_effect_before_checkpoint",
        )
    except InjectedCrash:
        crashed = True
    assert crashed, "InjectedCrash should propagate out of workflow"

    started_at = time.time()
    resumed = run_claim("C-001", seed=11, store_path=str(store))
    assert resumed.status == "resolved"

    conn = connect(store)
    try:
        passed, reason = trial_pass(resumed.as_dict(), BY_ID["C-001"]["expected"], conn, started_at=started_at)
        count = conn.execute("SELECT COUNT(*) AS n FROM refund_ledger WHERE claim_id = 'C-001'").fetchone()["n"]
    finally:
        conn.close()

    assert passed, reason
    assert count == 1
