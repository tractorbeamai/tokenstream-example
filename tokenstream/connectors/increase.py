"""Increase — payout (sponsor) bank. ACH payouts and status.

Models Increase's ``ach_transfers`` resource. The live feed uses integer-cent
amounts (no ``direction`` field — direction is implicit in the transfer kind)
and a rich status enum; this maps Increase's statuses onto the shared ACH
lifecycle (``pending_submission`` → initiated, ``submitted`` → settled,
``returned``/``rejected`` → returned) and adds the explicit direction.

Docs:   https://increase.com/documentation/api/ach-transfers
Spec:   https://increase.com/openapi.json
Auth:   Bearer API key (Authorization: Bearer)
Limits: not publicly documented
"""

import random
import uuid
from collections.abc import Iterator
from datetime import date, timedelta

import tractorbeam as tb

from tokenstream.connectors import _auth
from tokenstream.connectors._schemas import ACH
from tokenstream.connectors._transport import Request, secret_value, send

_BASE = "https://api.increase.com"
_STATUS = {
    "pending_approval": "initiated",
    "pending_submission": "initiated",
    "submitted": "settled",
    "returned": "returned",
    "rejected": "returned",
}
_RETURN_CODES = ("R01", "R02", "R03", "R29")


@tb.Connector()
class Increase:
    """Increase ACH payouts and their status."""

    api: tb.Secret = tb.Secret("increase_api_key")

    @tb.output(
        "ach_transfers",
        trigger=tb.Schedule("*/15 * * * *"),
        primary_key="payout_id",
        description="Outbound ACH payouts in the shared ACH shape.",
        columns=ACH,
    )
    def ach_transfers(self) -> Iterator[dict]:
        # GET /ach_transfers — https://increase.com/documentation/api/ach-transfers#list-ach-transfers
        request = Request(
            "GET",
            f"{_BASE}/ach_transfers",
            headers=_auth.bearer(secret_value(self.api)),
            params={"limit": "100"},
        )
        mock = {"data": [_mock_transfer() for _ in range(random.randint(2, 6))]}
        effective_on = (date.today() + timedelta(days=1)).isoformat()
        for transfer in send(request, mock=mock).json()["data"]:
            status = _STATUS.get(transfer["status"], "initiated")
            returned = transfer["status"] in ("returned", "rejected")
            yield {
                "payout_id": transfer["id"],
                "direction": "CREDIT",
                "amount": transfer["amount"],
                "currency": transfer["currency"],
                "status": status,
                "effective_on": effective_on,
                "merchant_id": transfer["company_entry_description"],
                "trace_number": transfer["submission"]["trace_number"],
                "return_code": random.choice(_RETURN_CODES) if returned else None,
            }


def _mock_transfer() -> dict:
    return {
        "id": f"ach_transfer_{uuid.uuid4().hex[:22]}",
        "amount": random.randrange(50_00, 200_000_00),
        "currency": "USD",
        "status": random.choice(["pending_submission", "submitted", "submitted", "returned"]),
        "company_entry_description": f"m_{random.randint(1, 312):03d}",
        "submission": {"trace_number": f"{random.randrange(10**14, 10**15)}"},
    }
