"""Coinbase Prime — crypto custody. Per-asset balances.

Models Coinbase Prime's REST ``List Portfolio Balances`` endpoint. The live
feed reports decimal major-unit ``amount``, ``holds``, and
``withdrawable_amount`` per asset; this normalizes to available (amount minus
holds) and unsettled (holds) balances in integer minor units.

Docs:   https://docs.cdp.coinbase.com/api-reference/prime-api/rest-api/balances/list-portfolio-balances
Spec:   none
Auth:   API key + HMAC-SHA256 signature + passphrase (X-CB-ACCESS-* headers)
Limits: 25 req/s per portfolio (burst 50); 100 req/s per IP
"""

import random
from collections.abc import Iterator
from datetime import UTC, datetime

import tractorbeam as tb

from tokenstream.connectors import _auth
from tokenstream.connectors._schemas import BALANCE
from tokenstream.connectors._transport import Request, secret_value, send, to_minor

_BASE = "https://api.prime.coinbase.com"
_PORTFOLIO = "11111111-1111-1111-1111-111111111111"


@tb.Connector()
class CoinbasePrime:
    """Per-asset balances held in Coinbase Prime custody."""

    api: tb.Secret = tb.Secret("coinbase_prime_key")

    @tb.output(
        "balances",
        trigger=tb.Schedule("*/15 * * * *"),
        write_disposition="replace",
        primary_key="account_id",
        description="Per-asset custody balances in the shared balance shape.",
        columns=BALANCE,
    )
    def balances(self) -> Iterator[dict]:
        path = f"/v1/portfolios/{_PORTFOLIO}/balances"
        request = Request(
            "GET",
            f"{_BASE}{path}",
            headers=_auth.coinbase_prime_headers(secret_value(self.api), method="GET", path=path),
        )
        mock = {"balances": [_mock_balance(s) for s in ("USDC", "USD", "EUR")]}
        as_of = datetime.now(UTC).isoformat()
        for balance in send(request, mock=mock).json()["balances"]:
            yield {
                "account_id": f"coinbase_prime-{balance['symbol'].lower()}",
                "venue": "coinbase_prime",
                "currency": balance["symbol"].upper(),
                "available_balance": to_minor(balance["amount"]) - to_minor(balance["holds"]),
                "unsettled_balance": to_minor(balance["holds"]),
                "as_of": as_of,
            }


def _mock_balance(symbol: str) -> dict:
    amount = random.uniform(500_000, 30_000_000)
    holds = random.uniform(0, 1_000_000)
    return {
        "symbol": symbol,
        "amount": f"{amount:.2f}",
        "holds": f"{holds:.2f}",
        "withdrawable_amount": f"{amount - holds:.2f}",
    }
