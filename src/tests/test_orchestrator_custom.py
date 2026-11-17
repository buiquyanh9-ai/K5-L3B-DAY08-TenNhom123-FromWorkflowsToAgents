"""Test suite đóng góp riêng của Thành viên 3: Orchestrator + Handoff.

Mục đích:
- Kiểm tra tính nghiêm ngặt của ranh giới Handoff (từ chối write tool, loại bỏ secret/header).
- Kiểm tra Shape Orchestrator giải quyết claim chính xác, không rò rỉ CANARY_SECRET_ hay PII vào trace.
- Kiểm tra các nhánh phân luồng: needs_info, escalated, resolved.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lab8.db import init_store
from lab8.handoff import HandoffError, make_handoff
from lab8.shapes.orchestrator import run_claim
from tests.conftest import CLAIMS, WORLD


def test_handoff_rejects_write_tools_explicitly():
    """Handoff phải từ chối ngay lập tức nếu caller cố tình cấp write tool cho worker."""
    with pytest.raises(HandoffError) as exc_info:
        make_handoff(
            request_id="REQ-TEST-WRITE",
            claim_id="C-001",
            task="malicious_pay",
            facts={},
            allowed_tools=["issue_refund", "lookup_order"],
        )
    assert "worker tools must be read-only" in str(exc_info.value)


def test_handoff_sanitization_removes_unallowed_keys():
    """Handoff chỉ được giữ các keys trong ALLOWED_FIELDS và FACT_KEYS."""
    dirty_facts = {
        "delay_days": 4,
        "shipping_fee_vnd": 35000,
        "parent_secret": "CANARY_SECRET_LEAK",
        "customer_phone": "0912345678",
    }
    handoff = make_handoff(
        request_id="REQ-CLEAN",
        claim_id="C-001",
        task="check_policy",
        facts=dirty_facts,
        allowed_tools=["lookup_order", "lookup_policy"],
    )
    # facts chỉ giữ delay_days và shipping_fee_vnd
    assert "parent_secret" not in handoff["facts"]
    assert "customer_phone" not in handoff["facts"]
    assert handoff["facts"]["delay_days"] == 4
    assert handoff["facts"]["shipping_fee_vnd"] == 35000


def test_orchestrator_resolves_cleanly_without_secret_leak(tmp_path: Path):
    """Orchestrator xử lý C-001 thành công và trace hoàn toàn sạch, không có CANARY_SECRET_."""
    store = tmp_path / "orch_c001.sqlite"
    init_store(store, WORLD, CLAIMS).close()

    result = run_claim("C-001", seed=11, store_path=str(store))
    assert result.status == "resolved"
    assert result.proposal_amount == 35000
    assert result.error_reason is None
    assert len(result.refund_effects) == 1

    # Kiểm tra trace JSON file
    assert Path(result.trace_path).exists()
    trace_text = Path(result.trace_path).read_text(encoding="utf-8")
    trace_data = json.loads(trace_text)

    assert trace_data["run_id"] == result.run_id
    assert "CANARY_SECRET_" not in trace_text
    # Trace phải có ghi nhận handoff đã sanitize
    handoff_events = [e for e in trace_data["events"] if e["kind"] == "handoff"]
    assert len(handoff_events) >= 1
    assert "parent_secret" not in json.dumps(handoff_events[0]["payload"])


def test_orchestrator_handles_missing_order_id(tmp_path: Path):
    """Khi claim không có order_id (C-004), orchestrator phải trả needs_info."""
    store = tmp_path / "orch_c004.sqlite"
    init_store(store, WORLD, CLAIMS).close()

    result = run_claim("C-004", seed=11, store_path=str(store))
    assert result.status == "needs_info"
    assert result.proposal_amount == 0
    assert result.error_reason == "missing_order_id"
    assert result.refund_effects == []


def test_orchestrator_escalates_on_principal_mismatch(tmp_path: Path):
    """Khi đơn không thuộc về principal (C-005), orchestrator phải trả escalated."""
    store = tmp_path / "orch_c005.sqlite"
    init_store(store, WORLD, CLAIMS).close()

    result = run_claim("C-005", seed=11, store_path=str(store))
    assert result.status == "escalated"
    assert result.proposal_amount == 0
    assert result.error_reason == "outside_principal_scope"
    assert result.refund_effects == []
