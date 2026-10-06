"""The confirm flag prints a ticket. It never transmits."""

from decimal import Decimal
from pathlib import Path

import pytest

from desk.orders import (
    CONFIRM_ENV,
    ConfirmationRequired,
    LiveOrdersDisabled,
    confirm_is_human_yes,
    manual_order_ticket,
    submit_live_order,
)
from desk.risk import AccountSnapshot, OrderPlan


def _plan() -> OrderPlan:
    return OrderPlan(
        symbol="SOLUSDT",
        entry=Decimal("100"),
        stop=Decimal("98"),
        target=Decimal("110"),
    )


def _account() -> AccountSnapshot:
    return AccountSnapshot(equity=Decimal("20"), starting_equity=Decimal("20"))


def test_confirm_defaults_to_closed(monkeypatch):
    monkeypatch.delenv(CONFIRM_ENV, raising=False)
    assert confirm_is_human_yes() is False
    for value in ("false", "False", "true", "1", "YES ", "y", ""):
        assert confirm_is_human_yes(value) is (value.strip().lower() == "yes")
    with pytest.raises(ConfirmationRequired):
        manual_order_ticket(_plan(), _account(), confirm="false")


def test_yes_prints_a_ticket_and_still_refuses_to_send():
    ticket = manual_order_ticket(_plan(), _account(), confirm="yes")
    assert "MANUAL TICKET — NOT SENT" in ticket
    assert "SOLUSDT" in ticket
    assert "spot" in ticket
    with pytest.raises(LiveOrdersDisabled):
        submit_live_order(confirm="yes", plan=_plan())
    with pytest.raises(LiveOrdersDisabled):
        submit_live_order()


def test_package_has_no_order_endpoint():
    root = Path(__file__).resolve().parents[1] / "desk"
    blob = "\n".join(path.read_text(encoding="utf-8") for path in root.rglob("*.py"))
    assert "/v5/order" not in blob
    assert "X-BAPI" not in blob
    assert "hmac" not in blob.lower()
    assert "place_order" not in blob
