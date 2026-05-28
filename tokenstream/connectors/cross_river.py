"""Cross River — payout (sponsor) bank. ACH payouts and status.

Models Cross River's COS ``/ach/v1/payments`` resource. The live feed uses
integer-cent amounts (no currency field; USD assumed), a YYMMDD effective
date, and its own status vocabulary; this maps those statuses onto the shared
ACH lifecycle and expands the effective date to ISO 8601.

Docs:   https://docs.crossriver.com/apis/payments/ach
Spec:   none
Auth:   OAuth2 client credentials; bearer JWT on each request
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

_BASE = "https://api.crossriver.com"
_TOKEN_URL = f"{_BASE}/connect/token"
_STATUS = {
    "created": "initiated",
    "pending": "initiated",
    "processing": "submitted",
    "completed": "settled",
    "returned": "returned",
}


@tb.Connector()
class CrossRiver:
    """Cross River ACH payouts and their status."""

    api: tb.Secret = tb.Secret("cross_river_key")

    @tb.output(
        "ach_transfers",
        trigger=tb.Schedule("*/15 * * * *"),
        primary_key="payout_id",
        description="Outbound ACH payouts in the shared ACH shape.",
        columns=ACH,
    )
    def ach_transfers(self) -> Iterator[dict]:
        credential = secret_value(self.api)
        token = _auth.oauth2_client_credentials(_TOKEN_URL, credential, scope="ach")
        # GET /ach/v1/payments — https://docs.crossriver.com/apis/payments/ach
        request = Request("GET", f"{_BASE}/ach/v1/payments", headers=_auth.bearer(token))
        mock = {"data": [_mock_payment() for _ in range(random.randint(2, 6))]}
        for payment in send(request, mock=mock).json()["data"]:
            yield {
                "payout_id": payment["id"],
                "direction": "CREDIT",
                "amount": payment["amount"],
                "currency": "USD",
                "status": _STATUS.get(payment["status"], "initiated"),
                "effective_on": _from_yymmdd(payment["effectiveDate"]),
                "merchant_id": payment["addenda"]["merchantId"],
                "trace_number": payment["traceNumber"],
                "return_code": payment["returnCode"],
            }


def _from_yymmdd(value: str) -> str:
    return f"20{value[0:2]}-{value[2:4]}-{value[4:6]}"


def _mock_payment() -> dict:
    status = random.choice(["processing", "completed", "completed", "returned"])
    return {
        "id": str(uuid.uuid4()),
        "amount": random.randrange(50_00, 200_000_00),
        "status": status,
        "effectiveDate": (date.today() + timedelta(days=1)).strftime("%y%m%d"),
        "traceNumber": f"{random.randrange(10**14, 10**15)}",
        "returnCode": random.choice(["R01", "R02", "R03"]) if status == "returned" else None,
        "addenda": {"merchantId": f"m_{random.randint(1, 312):03d}"},
    }
