"""Column — payout (sponsor) bank. ACH transfers and account balances.

Models Column's ACH transfer and bank-account objects. Column already reports
integer minor units (cents) and lowercase ISO 4217, so amounts pass through;
its status vocabulary already matches the normalized lifecycle. Balances are
split into available / pending / holding / locked amounts.

Docs:   https://docs.column.com/ach/
Spec:   none
Auth:   HTTP Basic — API key as the password with an empty username
Limits: not publicly documented
"""

import random
import uuid
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta

import tractorbeam as tb

from tokenstream.connectors import _auth
from tokenstream.connectors._schemas import ACH, BANK_BALANCE
from tokenstream.connectors._transport import Request, secret_value, send

_BASE = "https://api.column.com"
_RETURN_CODES = ("R01", "R02", "R03", "R29")


@tb.Connector()
class Column:
    """Sponsor-bank ACH transfers and account balances from Column."""

    api: tb.Secret = tb.Secret("column_api_key")

    def _auth_headers(self) -> dict[str, str]:
        # Column authenticates with the API key as the HTTP Basic username.
        return _auth.http_basic(secret_value(self.api))

    @tb.output(
        "ach_transfers",
        trigger=tb.Schedule("*/15 * * * *"),
        primary_key="payout_id",
        description="Outbound ACH payouts in the shared ACH shape.",
        columns=ACH,
    )
    def ach_transfers(self) -> Iterator[dict]:
        # GET /transfers/ach — https://docs.column.com/reference/list-ach-transfers
        request = Request("GET", f"{_BASE}/transfers/ach", headers=self._auth_headers())
        mock = {"transfers": [_mock_ach() for _ in range(random.randint(3, 8))]}
        for transfer in send(request, mock=mock).json()["transfers"]:
            returned = transfer["status"] == "returned"
            yield {
                "payout_id": transfer["id"],
                "direction": transfer["direction"].upper(),
                "amount": transfer["amount"],
                "currency": transfer["currency"].upper(),
                "status": transfer["status"],
                "effective_on": transfer["effective_on"],
                "merchant_id": transfer["metadata"]["merchant_id"],
                "trace_number": transfer["trace_number"],
                "return_code": transfer["return_details"]["code"] if returned else None,
            }

    @tb.output(
        "bank_balances",
        trigger=tb.Schedule("*/15 * * * *"),
        write_disposition="replace",
        primary_key="account_id",
        description="Available and pending balance per Column bank account.",
        columns=BANK_BALANCE,
    )
    def bank_balances(self) -> Iterator[dict]:
        as_of = datetime.now(UTC).isoformat()
        for currency in ("USD", "EUR"):
            account_id = f"column-{currency.lower()}"
            # GET /bank-accounts/{id}/balances — https://docs.column.com/reference/get-bank-account-balance
            request = Request(
                "GET", f"{_BASE}/bank-accounts/{account_id}/balances", headers=self._auth_headers()
            )
            mock = {
                "available_amount": random.randrange(500_000_00, 20_000_000_00),
                "pending_amount": random.randrange(0, 1_000_000_00),
                "holding_amount": random.randrange(0, 1_000_000_00),
                "locked_amount": 0,
            }
            balance = send(request, mock=mock).json()
            yield {
                "account_id": account_id,
                "currency": currency,
                "available_balance": balance["available_amount"],
                "unsettled_balance": balance["pending_amount"]
                + balance["holding_amount"]
                + balance["locked_amount"],
                "as_of": as_of,
            }


def _mock_ach() -> dict:
    status = random.choice(["initiated", "submitted", "settled", "settled", "returned"])
    return {
        "id": f"acht_{uuid.uuid4().hex[:24]}",
        "direction": "credit",
        "amount": random.randrange(50_00, 250_000_00),
        "currency": "usd",
        "status": status,
        "effective_on": (date.today() + timedelta(days=1)).isoformat(),
        "metadata": {"merchant_id": f"m_{random.randint(1, 312):03d}"},
        "trace_number": f"{random.randrange(10**14, 10**15)}",
        "return_details": {"code": random.choice(_RETURN_CODES)} if status == "returned" else None,
    }
