"""Paxos — stablecoin issuer. USDP balances.

Models Paxos' ``GET /v2/profiles/{id}/balances`` endpoint. The live feed
returns decimal major-unit ``available`` and ``trading`` per asset; this
normalizes to integer minor units, mapping ``trading`` (amounts locked in open
orders) onto the unsettled balance.

Docs:   https://docs.paxos.com/api-reference/introduction
Spec:   https://developer.paxos.com/docs/paxos-v2.openapi.json
Auth:   OAuth2 client credentials; scope funding:read_profile for balance reads
Limits: ~50 req/s per endpoint+IP over a 5-minute window (429 on breach)
"""

import random
from collections.abc import Iterator
from datetime import UTC, datetime

import tractorbeam as tb

from tokenstream.connectors import _auth
from tokenstream.connectors._schemas import STABLECOIN_BALANCE
from tokenstream.connectors._transport import Request, secret_value, send, to_minor

_BASE = "https://api.paxos.com"
_TOKEN_URL = f"{_BASE}/oauth/token"
_PROFILE = "00000000-0000-0000-0000-000000000000"


@tb.Connector()
class Paxos:
    """USDP balances from Paxos."""

    api: tb.Secret = tb.Secret("paxos_api_key")

    @tb.output(
        "usdp_balances",
        trigger=tb.Schedule("*/15 * * * *"),
        write_disposition="replace",
        primary_key="account_id",
        description="USDP balance snapshot in the shared stablecoin-balance shape.",
        columns=STABLECOIN_BALANCE,
    )
    def usdp_balances(self) -> Iterator[dict]:
        credential = secret_value(self.api)
        token = _auth.oauth2_client_credentials(
            _TOKEN_URL, credential, scope="funding:read_profile"
        )
        path = f"/v2/profiles/{_PROFILE}/balances"
        # GET /v2/profiles/{id}/balances — https://docs.paxos.com/api-reference
        request = Request("GET", f"{_BASE}{path}", headers=_auth.bearer(token))
        mock = {"balances": [_mock_balance("USDP")]}
        for balance in send(request, mock=mock).json()["balances"]:
            if balance["asset"] != "USDP":
                continue
            yield {
                "account_id": "paxos-usdp-master",
                "currency": balance["asset"],
                "available_balance": to_minor(balance["available"]),
                "unsettled_balance": to_minor(balance["trading"]),
                "as_of": datetime.now(UTC).isoformat(),
            }


def _mock_balance(asset: str) -> dict:
    return {
        "asset": asset,
        "available": f"{random.uniform(500_000, 15_000_000):.2f}",
        "trading": f"{random.uniform(0, 1_000_000):.2f}",
    }
