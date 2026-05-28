"""Kraken — crypto exchange. Account balances.

Models Kraken's REST ``BalanceEx`` endpoint. The live feed keys decimal
major-unit balances by Kraken asset code (ZUSD, ZEUR, USDC) and breaks out
``balance`` and ``hold_trade``; this normalizes asset codes and splits into
available (balance minus held) and unsettled (held) in integer minor units.

Docs:   https://docs.kraken.com/api/docs/rest-api/get-extended-balance
Spec:   none
Auth:   API-Key header + API-Sign (HMAC-SHA512 over path + SHA256(nonce + body))
Limits: tiered counter; +1 per Balance call, decays 0.5-1/s by verification tier
"""

import random
import time
from collections.abc import Iterator
from datetime import UTC, datetime

import tractorbeam as tb

from tokenstream.connectors import _auth
from tokenstream.connectors._schemas import BALANCE
from tokenstream.connectors._transport import Request, secret_value, send, to_minor

_BASE = "https://api.kraken.com"
_ASSETS = {"USDC": "USDC", "ZUSD": "USD", "ZEUR": "EUR"}


@tb.Connector()
class Kraken:
    """Kraken account balances."""

    api: tb.Secret = tb.Secret("kraken_api_key")

    @tb.output(
        "balances",
        trigger=tb.Schedule("*/15 * * * *"),
        write_disposition="replace",
        primary_key="account_id",
        description="Per-asset exchange balances in the shared balance shape.",
        columns=BALANCE,
    )
    def balances(self) -> Iterator[dict]:
        path = "/0/private/BalanceEx"
        data = {"nonce": str(int(time.time() * 1000))}
        request = Request(
            "POST",
            f"{_BASE}{path}",
            headers=_auth.kraken_headers(secret_value(self.api), path=path, data=data),
            json=data,
        )
        mock = {"error": [], "result": {code: _mock_balance() for code in _ASSETS}}
        result = send(request, mock=mock).json()["result"]
        as_of = datetime.now(UTC).isoformat()
        for code, currency in _ASSETS.items():
            entry = result[code]
            yield {
                "account_id": f"kraken-{currency.lower()}",
                "venue": "kraken",
                "currency": currency,
                "available_balance": to_minor(entry["balance"]) - to_minor(entry["hold_trade"]),
                "unsettled_balance": to_minor(entry["hold_trade"]),
                "as_of": as_of,
            }


def _mock_balance() -> dict:
    return {
        "balance": f"{random.uniform(100_000, 10_000_000):.4f}",
        "hold_trade": f"{random.uniform(0, 500_000):.4f}",
    }
