"""Circle — stablecoin issuer. USDC balances and mint/redeem transfers.

Models Circle Mint's ``businessAccount`` balances and transfers. Circle splits
balances into ``available[]`` and ``unsettled[]`` arrays of decimal major-unit
Money objects, and transfers carry a UUID, a status (pending | complete |
failed), a chain, and a ``transactionHash``; this normalizes to integer minor
units.

Docs:   https://developers.circle.com/circle-mint
Spec:   https://github.com/circlefin/openapi
Auth:   Bearer API key (Authorization: Bearer)
Limits: not publicly documented for Circle Mint endpoints
"""

import random
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime

import tractorbeam as tb

from tokenstream.connectors import _auth
from tokenstream.connectors._schemas import STABLECOIN_BALANCE, STABLECOIN_TRANSFER
from tokenstream.connectors._transport import Request, secret_value, send, to_minor

_BASE = "https://api.circle.com"


def _money(currency: str = "USD") -> dict:
    return {"amount": f"{random.uniform(0, 500_000):.2f}", "currency": currency}


@tb.Connector()
class CircleMint:
    """USDC balances and mint/redeem transfers from Circle Mint."""

    api: tb.Secret = tb.Secret("circle_api_key")

    @tb.output(
        "usdc_balances",
        trigger=tb.Schedule("*/15 * * * *"),
        write_disposition="replace",
        primary_key="account_id",
        description="USDC balance snapshot in the shared stablecoin-balance shape.",
        columns=STABLECOIN_BALANCE,
    )
    def usdc_balances(self) -> Iterator[dict]:
        # GET /v1/businessAccount/balances — https://developers.circle.com/circle-mint/reference/getbusinessaccountbalances
        request = Request(
            "GET",
            f"{_BASE}/v1/businessAccount/balances",
            headers=_auth.bearer(secret_value(self.api)),
        )
        mock = {
            "data": {
                "available": [{"amount": f"{random.uniform(1e6, 5e7):.2f}", "currency": "USD"}],
                "unsettled": [{"amount": f"{random.uniform(0, 2e6):.2f}", "currency": "USD"}],
            }
        }
        data = send(request, mock=mock).json()["data"]
        available = {m["currency"]: m["amount"] for m in data["available"]}
        unsettled = {m["currency"]: m["amount"] for m in data["unsettled"]}
        yield {
            "account_id": "circle-usdc-master",
            "currency": "USDC",
            "available_balance": to_minor(available.get("USD", "0")),
            "unsettled_balance": to_minor(unsettled.get("USD", "0")),
            "as_of": datetime.now(UTC).isoformat(),
        }

    @tb.output(
        "usdc_transfers",
        trigger=tb.Schedule("*/15 * * * *"),
        primary_key="transfer_id",
        description="Mint/redeem and on-chain USDC movements in the shared transfer shape.",
        columns=STABLECOIN_TRANSFER,
    )
    def usdc_transfers(self) -> Iterator[dict]:
        # GET /v1/businessAccount/transfers — https://developers.circle.com/circle-mint/reference/listbusinessaccounttransfers
        request = Request(
            "GET",
            f"{_BASE}/v1/businessAccount/transfers",
            headers=_auth.bearer(secret_value(self.api)),
            params={"pageSize": "50"},
        )
        mock = {"data": [_mock_transfer() for _ in range(random.randint(1, 5))]}
        for transfer in send(request, mock=mock).json()["data"]:
            yield {
                "transfer_id": transfer["id"],
                "amount": to_minor(transfer["amount"]["amount"]),
                "currency": "USDC",
                "chain": transfer["destination"]["chain"],
                "status": transfer["status"],
                "tx_hash": transfer.get("transactionHash"),
                "created_at": transfer["createDate"],
            }


def _mock_transfer() -> dict:
    status = random.choice(["pending", "complete", "complete"])
    return {
        "id": str(uuid.uuid4()),
        "destination": {
            "type": "blockchain",
            "chain": random.choice(["ETH", "BASE", "SOL", "ARB"]),
        },
        "amount": _money(),
        "status": status,
        "transactionHash": f"0x{uuid.uuid4().hex}{uuid.uuid4().hex}"
        if status == "complete"
        else None,
        "createDate": datetime.now(UTC).isoformat(),
    }
