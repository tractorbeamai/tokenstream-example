"""Fireblocks — crypto custody. Vault balances.

Models Fireblocks' ``Get Vault Account Asset`` endpoint. The live feed reports
decimal major-unit ``total``, ``available``, ``pending``, ``frozen``, and
``lockedAmount`` per asset id; this normalizes to available and unsettled
(total minus available) balances in integer minor units.

Docs:   https://developers.fireblocks.com/reference/getvaultaccountasset
Spec:   https://raw.githubusercontent.com/fireblocks/fireblocks-openapi-spec/main/api-spec-v2.yaml
Auth:   API key + per-request RSA-signed JWT (X-API-Key + Authorization: Bearer)
Limits: per-endpoint per-minute caps (429 on breach); exact numbers not published
"""

import random
from collections.abc import Iterator
from datetime import UTC, datetime

import tractorbeam as tb

from tokenstream.connectors import _auth
from tokenstream.connectors._schemas import BALANCE
from tokenstream.connectors._transport import Request, secret_value, send, to_minor

_BASE = "https://api.fireblocks.io"
_VAULT = "0"


@tb.Connector()
class Fireblocks:
    """Fireblocks custody vault balances."""

    api: tb.Secret = tb.Secret("fireblocks_api_key")

    @tb.output(
        "balances",
        trigger=tb.Schedule("*/15 * * * *"),
        write_disposition="replace",
        primary_key="account_id",
        description="Per-asset custody balances in the shared balance shape.",
        columns=BALANCE,
    )
    def balances(self) -> Iterator[dict]:
        as_of = datetime.now(UTC).isoformat()
        for currency in ("USDC", "USDP"):
            path = f"/v1/vault/accounts/{_VAULT}/{currency}"
            # JWT is signed per request over the exact path (and body, if any).
            request = Request(
                "GET",
                f"{_BASE}{path}",
                headers=_auth.fireblocks_jwt(secret_value(self.api), path=path),
            )
            asset = send(request, mock=_mock_asset(currency)).json()
            yield {
                "account_id": f"fireblocks-{currency.lower()}",
                "venue": "fireblocks",
                "currency": currency,
                "available_balance": to_minor(asset["available"]),
                "unsettled_balance": to_minor(asset["total"]) - to_minor(asset["available"]),
                "as_of": as_of,
            }


def _mock_asset(asset_id: str) -> dict:
    total = random.uniform(1_000_000, 40_000_000)
    pending = random.uniform(0, 500_000)
    return {
        "id": asset_id,
        "total": f"{total:.2f}",
        "available": f"{total - pending:.2f}",
        "pending": f"{pending:.2f}",
        "frozen": "0",
        "lockedAmount": "0",
    }
