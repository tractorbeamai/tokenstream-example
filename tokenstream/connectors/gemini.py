"""Gemini — crypto exchange. Account balances.

Models Gemini's REST ``/v1/balances`` endpoint. The live feed reports decimal
major-unit ``amount`` and ``available`` per currency; this normalizes to
available and unsettled (amount minus available) balances in integer minor
units.

Docs:   https://developer.gemini.com/rest-api/fund-management
Spec:   none
Auth:   API key + HMAC-SHA384 over a base64 JSON payload (X-GEMINI-* headers)
Limits: private endpoints 600 req/min (~5 req/s recommended)
"""

import random
import time
from collections.abc import Iterator
from datetime import UTC, datetime

import tractorbeam as tb

from tokenstream.connectors import _auth
from tokenstream.connectors._schemas import BALANCE
from tokenstream.connectors._transport import Request, secret_value, send, to_minor

_BASE = "https://api.gemini.com"


@tb.Connector()
class Gemini:
    """Gemini account balances."""

    api: tb.Secret = tb.Secret("gemini_api_key")

    @tb.output(
        "balances",
        trigger=tb.Schedule("*/15 * * * *"),
        write_disposition="replace",
        primary_key="account_id",
        description="Per-asset exchange balances in the shared balance shape.",
        columns=BALANCE,
    )
    def balances(self) -> Iterator[dict]:
        path = "/v1/balances"
        payload = {"request": path, "nonce": int(time.time() * 1000)}
        request = Request(
            "POST",
            f"{_BASE}{path}",
            headers=_auth.gemini_headers(secret_value(self.api), payload=payload),
        )
        mock = [_mock_balance(c) for c in ("USDC", "USD")]
        as_of = datetime.now(UTC).isoformat()
        for balance in send(request, mock=mock).json():
            yield {
                "account_id": f"gemini-{balance['currency'].lower()}",
                "venue": "gemini",
                "currency": balance["currency"],
                "available_balance": to_minor(balance["available"]),
                "unsettled_balance": to_minor(balance["amount"]) - to_minor(balance["available"]),
                "as_of": as_of,
            }


def _mock_balance(currency: str) -> dict:
    amount = random.uniform(100_000, 8_000_000)
    available = amount - random.uniform(0, 300_000)
    return {
        "type": "exchange",
        "currency": currency,
        "amount": f"{amount:.2f}",
        "available": f"{available:.2f}",
        "availableForWithdrawal": f"{available:.2f}",
    }
