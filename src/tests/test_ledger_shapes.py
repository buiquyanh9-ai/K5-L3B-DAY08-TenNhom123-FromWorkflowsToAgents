"""TC13-TC20: approval and ledger behaviour, run end to end through the three student shapes.

The host tests (test_refund_idempotency, test_order_cap_and_approval_binding,
test_authorization) call durability.issue_refund directly. These tests check the
same rules through run_claim, so they also catch a shape that forwards the wrong
amount, swallows InjectedCrash, or calls the ledger more than once.
"""

from __future__ import annotations

import pytest

from lab8.db import connect, init_store
from lab8.durability import InjectedCrash
from lab8.shapes import SHAPES
from tests.conftest import CLAIMS, WORLD

SHAPES_UNDER_TEST = ["workflow", "single", "orchestrator"]
SEED = 11


def _store(tmp_path, shape: str, name: str) -> str:
    path = tmp_path / f"{shape}-{name}.sqlite"
    init_store(path, WORLD, CLAIMS).close()
    return str(path)


def _rows(store: str, claim_id: str) -> int:
    conn = connect(store)
    try:
        return conn.execute("SELECT COUNT(*) AS n FROM refund_ledger WHERE claim_id = ?", (claim_id,)).fetchone()["n"]
    finally:
        conn.close()


def _amount(store: str, claim_id: str):
    conn = connect(store)
    try:
        row = conn.execute("SELECT amount_vnd FROM refund_ledger WHERE claim_id = ?", (claim_id,)).fetchone()
        return int(row["amount_vnd"]) if row else None
    finally:
        conn.close()


def _audits(store: str, claim_id: str, event_type: str) -> int:
    conn = connect(store)
    try:
        return conn.execute(
            "SELECT COUNT(*) AS n FROM audit_events WHERE claim_id = ? AND event_type = ?",
            (claim_id, event_type),
        ).fetchone()["n"]
    finally:
        conn.close()


def _exec(store: str, sql: str, params: tuple = ()) -> None:
    conn = connect(store)
    try:
        conn.execute(sql, params)
        conn.commit()
    finally:
        conn.close()


def _approval_id(store: str, claim_id: str) -> str:
    conn = connect(store)
    try:
        return conn.execute("SELECT approval_id FROM claims WHERE claim_id = ?", (claim_id,)).fetchone()["approval_id"]
    finally:
        conn.close()


@pytest.mark.parametrize("shape", SHAPES_UNDER_TEST)
def test_tc13_no_approval_writes_no_refund(tmp_path, shape):
    store = _store(tmp_path, shape, "tc13")
    _exec(store, "UPDATE claims SET approval_id = NULL WHERE claim_id = 'C-001'")
    result = SHAPES[shape]("C-001", seed=SEED, store_path=store)
    assert result.status == "denied"
    assert _rows(store, "C-001") == 0
    assert _audits(store, "C-001", "refund_committed") == 0
    assert _audits(store, "C-001", "policy_denied") >= 1


@pytest.mark.parametrize("shape", SHAPES_UNDER_TEST)
def test_tc14_expired_approval_writes_no_refund(tmp_path, shape):
    store = _store(tmp_path, shape, "tc14")
    _exec(store, "UPDATE approvals SET expires_at = '2026-01-01' WHERE claim_id = 'C-001'")
    result = SHAPES[shape]("C-001", seed=SEED, store_path=store)
    assert result.status == "denied"
    assert _rows(store, "C-001") == 0
    assert _audits(store, "C-001", "policy_denied") >= 1


@pytest.mark.parametrize("shape", SHAPES_UNDER_TEST)
def test_tc15_approval_of_another_claim_is_rejected(tmp_path, shape):
    store = _store(tmp_path, shape, "tc15")
    other = _approval_id(store, "C-003")
    assert other and other != _approval_id(store, "C-001")
    _exec(store, "UPDATE claims SET approval_id = ? WHERE claim_id = 'C-001'", (other,))
    result = SHAPES[shape]("C-001", seed=SEED, store_path=store)
    assert result.status == "denied"
    assert _rows(store, "C-001") == 0
    assert _audits(store, "C-001", "policy_denied") >= 1


@pytest.mark.parametrize("shape", SHAPES_UNDER_TEST)
def test_tc16_quote_above_approved_amount_is_capped(tmp_path, shape):
    store = _store(tmp_path, shape, "tc16")
    _exec(store, "UPDATE approvals SET approved_vnd = 100000 WHERE claim_id = 'C-003'")
    result = SHAPES[shape]("C-003", seed=SEED, store_path=store)
    assert result.status == "resolved"
    assert result.proposal_amount == 150000  # the shape reports the full quote
    assert _amount(store, "C-003") == 100000  # the host pays only what was approved
    assert _rows(store, "C-003") == 1


@pytest.mark.parametrize("shape", SHAPES_UNDER_TEST)
def test_tc17_prior_refund_is_subtracted_once(tmp_path, shape):
    store = _store(tmp_path, shape, "tc17")
    result = SHAPES[shape]("C-014", seed=SEED, store_path=store)
    assert result.status == "resolved"
    assert result.proposal_amount == 150000  # full quote, not 120000
    assert _amount(store, "C-014") == 120000  # 150000 entitlement - 30000 already refunded
    assert _rows(store, "C-014") == 1


@pytest.mark.parametrize("shape", SHAPES_UNDER_TEST)
def test_tc18_repeated_calls_keep_one_refund(tmp_path, shape):
    store = _store(tmp_path, shape, "tc18")
    results = [SHAPES[shape]("C-001", seed=SEED, store_path=store) for _ in range(3)]
    assert [r.status for r in results] == ["resolved"] * 3
    assert _rows(store, "C-001") == 1
    assert _amount(store, "C-001") == 35000
    assert _audits(store, "C-001", "refund_committed") == 1


@pytest.mark.parametrize("shape", SHAPES_UNDER_TEST)
@pytest.mark.parametrize("crash_at", ["before_effect", "after_effect_before_checkpoint", "after_checkpoint"])
def test_tc19_crash_then_resume_pays_once(tmp_path, shape, crash_at):
    store = _store(tmp_path, shape, f"tc19-{crash_at}")
    with pytest.raises(InjectedCrash):
        SHAPES[shape]("C-012", seed=SEED, store_path=store, crash_at=crash_at)
    expected_before_resume = 0 if crash_at == "before_effect" else 1
    assert _rows(store, "C-012") == expected_before_resume
    result = SHAPES[shape]("C-012", seed=SEED, store_path=store)
    assert result.status == "resolved"
    assert _rows(store, "C-012") == 1
    assert _audits(store, "C-012", "refund_committed") == 1


@pytest.mark.parametrize("shape", SHAPES_UNDER_TEST)
def test_tc20_retry_with_a_different_amount_keeps_the_committed_one(tmp_path, shape):
    store = _store(tmp_path, shape, "tc20")
    _exec(store, "UPDATE approvals SET approved_vnd = 100000 WHERE claim_id = 'C-003'")
    first = SHAPES[shape]("C-003", seed=SEED, store_path=store)
    assert first.status == "resolved"
    assert _amount(store, "C-003") == 100000
    # The approval is raised after the refund was committed, so a retry now computes 150000.
    _exec(store, "UPDATE approvals SET approved_vnd = 150000 WHERE claim_id = 'C-003'")
    retry = SHAPES[shape]("C-003", seed=SEED, store_path=store)
    assert retry.status == "failed"
    assert _amount(store, "C-003") == 100000
    assert _rows(store, "C-003") == 1
    assert _audits(store, "C-003", "amount_conflict") == 1
