"""Manual ticket helper.

LIVE_ORDERS_CONFIRM defaults to false. The only accepted human yes is the
exact word "yes" (any case). That word prints a text ticket for a person
to read. It does not build an HTTP request, sign a payload, or contact Bybit.

`submit_live_order` exists so callers have a single obvious dead end.
It always raises, including when the confirm word is yes.
"""

from __future__ import annotations

import os
from decimal import Decimal

from desk.risk import AccountSnapshot, OrderPlan, evaluate

CONFIRM_ENV = "LIVE_ORDERS_CONFIRM"


class ConfirmationRequired(RuntimeError):
    """The manual ticket stays locked until a human sets the yes-word."""


class LiveOrdersDisabled(RuntimeError):
    """Live order placement is not implemented."""


def confirm_is_human_yes(value: str | None = None) -> bool:
    """True only for the word yes. false, true, 1, and empty all fail."""
    if value is None:
        value = os.environ.get(CONFIRM_ENV, "false")
    return value.strip().lower() == "yes"


def manual_order_ticket(
    plan: OrderPlan,
    account: AccountSnapshot,
    *,
    confirm: str | None = None,
) -> str:
    """Return a human-readable ticket or raise if the yes-word is absent.

    The risk gate still applies. A failing plan does not produce a buy ticket.
    """
    if not confirm_is_human_yes(confirm):
        raise ConfirmationRequired(
            f"Set {CONFIRM_ENV}=yes to print a manual ticket. "
            "That flag does not send an order. A person still has to decide."
        )
    decision = evaluate(plan, account)
    if not decision.allowed:
        raise ConfirmationRequired(f"no ticket: {decision.summary}")
    rr = decision.rr_after_fees
    rr_text = "n/a" if rr is None else format(rr, "f")
    lines = [
        "MANUAL TICKET — NOT SENT",
        "This program did not place an order and has no code path that will.",
        "A person may read the numbers and, separately, type a spot order in the Bybit UI.",
        f"Symbol: {plan.symbol}",
        "Market: spot",
        "Side: Buy (long only)",
        f"Quantity: {format(decision.qty, 'f')}",
        f"Entry reference: {format(plan.entry, 'f')}",
        f"Stop reference: {format(plan.stop, 'f')}",
        f"Target reference: {format(plan.target, 'f')}",
        f"R:R after fees: {rr_text}",
        f"Fee budget: {fee_round_trip_label(account.fee_rate)} round trip",
        f"Risk fraction: {format(decision.risk_fraction, 'f')}",
        f"{CONFIRM_ENV}: yes",
        "Next step is a human decision, not this process.",
    ]
    return "\n".join(lines) + "\n"


def submit_live_order(*_args: object, **_kwargs: object) -> None:
    """Always refuse. The confirm flag cannot turn this into an order."""
    raise LiveOrdersDisabled(
        "Live order placement is not implemented. "
        f"{CONFIRM_ENV}=yes only unlocks manual_order_ticket text. "
        "Nothing is signed and nothing is posted."
    )


def fee_round_trip_label(fee_rate: Decimal = Decimal("0.001")) -> str:
    """Headline round-trip percent, e.g. 0.20%."""
    pct = (fee_rate * Decimal("2") * Decimal("100")).quantize(Decimal("0.01"))
    return f"{format(pct, 'f')}%"
