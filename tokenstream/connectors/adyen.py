"""Adyen — acquiring processor. Settlement-details report.

Models Adyen's settlement detail data from the Balance Platform. Adyen reports
amounts as integer minor units in an ``{value, currency}`` Amount object, so
the values pass through directly; this rolls the report up to one net
settlement row per currency.

Docs:   https://docs.adyen.com/reporting/settlement-reconciliation/transaction-level
Spec:   https://github.com/Adyen/adyen-openapi (the report is a CSV, not REST)
Auth:   API key via X-API-Key header
Limits: not publicly documented for report downloads
"""

import random
from collections.abc import Iterator
from datetime import date, timedelta

import tractorbeam as tb

from tokenstream.connectors import _auth
from tokenstream.connectors._schemas import SETTLEMENT
from tokenstream.connectors._transport import Request, secret_value, send

_BASE = "https://balanceplatform-api-live.adyen.com"


@tb.Connector()
class Adyen:
    """Adyen settlement-details report, pulled once the daily report lands."""

    api: tb.Secret = tb.Secret("adyen_report_key")

    @tb.output(
        "settlement_details",
        trigger=tb.Schedule("0 7 * * *"),
        write_disposition="append",
        primary_key="settlement_id",
        description="Daily acquirer settlement batches in the shared settlement shape.",
        columns=SETTLEMENT,
    )
    def settlement_details(self) -> Iterator[dict]:
        batch_date = date.today()
        available_on = (batch_date + timedelta(days=1)).isoformat()
        # GET /btl/v4/settlements — https://docs.adyen.com/api-explorer/balanceplatform
        request = Request(
            "GET",
            f"{_BASE}/btl/v4/settlements",
            headers=_auth.api_key_header("X-API-Key", secret_value(self.api)),
            params={"batchDate": batch_date.isoformat()},
        )
        mock = {"data": [_mock_batch(c) for c in ("USD", "EUR")]}
        for batch in send(request, mock=mock).json()["data"]:
            currency = batch["amount"]["currency"]
            yield {
                "settlement_id": f"adyen-{batch_date.isoformat()}-{currency}",
                "acquiring_bank_id": "adyen",
                "batch_date": batch_date.isoformat(),
                "gross": batch["amount"]["value"],
                "fees": batch["fees"]["value"],
                "net": batch["amount"]["value"] - batch["fees"]["value"],
                "currency": currency,
                "transaction_count": batch["transactionCount"],
                "available_on": available_on,
            }


def _mock_batch(currency: str) -> dict:
    gross = random.randrange(5_000_00, 4_000_000_00)
    return {
        "batchNumber": random.randint(1, 999),
        "amount": {"value": gross, "currency": currency},
        "fees": {"value": round(gross * random.uniform(0.02, 0.031)), "currency": currency},
        "transactionCount": random.randint(500, 40_000),
    }
