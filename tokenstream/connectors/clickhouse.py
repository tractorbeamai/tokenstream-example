"""ClickHouse — a customer-side analytical store, ingested as one more feed.

Many teams already reconcile across counterparties in an internal data warehouse
before adopting an ontology. A plain ``@tb.Connector`` reads the reconciled
balance snapshot over ClickHouse's HTTP interface and lands it in the shared
``BALANCE`` shape, governed alongside every other source. ClickHouse is not a
managed type, so the read is a ``POST`` carrying a ``SELECT`` — the same
authoring surface as any other custom connector here.

Docs:   https://clickhouse.com/docs/en/interfaces/http
Spec:   none
Auth:   HTTP Basic over the HTTP interface (user:password); ClickHouse also
        accepts ``X-ClickHouse-User`` / ``X-ClickHouse-Key`` headers.
Limits: governed by the ClickHouse deployment, not a fixed public quota.
"""

import random
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime

import tractorbeam as tb

from tokenstream.connectors import _auth
from tokenstream.connectors._schemas import BALANCE
from tokenstream.connectors._transport import Request, secret_value, send

_BASE = "https://clickhouse.internal.example"
_QUERY = (
    "SELECT account_id, venue, currency, available_balance, unsettled_balance "
    "FROM reconciliation.balances FINAL FORMAT JSONEachRow"
)
_VENUES = ("coinbase_prime", "fireblocks", "column", "circle", "kraken", "cross_river")
_FIAT = ("USD", "EUR", "GBP")
_STABLE = ("USDC", "USDP")


@tb.Connector()
class ClickHouse:
    """In-house cross-venue reconciled balances, read from ClickHouse."""

    credentials: tb.Secret = tb.Secret("clickhouse_credentials")

    def _auth_headers(self) -> dict[str, str]:
        # The secret is the colon-joined user:password; ClickHouse takes it as HTTP Basic.
        user, password = _auth._split(secret_value(self.credentials), 2)
        return _auth.http_basic(user, password)

    @tb.output(
        "reconciled_balances",
        trigger=tb.Schedule("*/15 * * * *"),
        write_disposition="replace",
        primary_key="account_id",
        description="Cross-venue reconciled balances, ingested from ClickHouse.",
        columns=BALANCE,
    )
    def reconciled_balances(self) -> Iterator[dict]:
        as_of = datetime.now(UTC).isoformat()
        # POST /?query=… — https://clickhouse.com/docs/en/interfaces/http#querying
        request = Request("POST", f"{_BASE}/", headers=self._auth_headers(), json={"query": _QUERY})
        mock = {"data": [_mock_balance() for _ in range(random.randint(4, 9))]}
        for row in send(request, mock=mock).json()["data"]:
            yield {
                "account_id": row["account_id"],
                "venue": row["venue"],
                "currency": row["currency"],
                "available_balance": row["available_balance"],
                "unsettled_balance": row["unsettled_balance"],
                "as_of": as_of,
            }


def _mock_balance() -> dict:
    venue = random.choice(_VENUES)
    currency = random.choice(_STABLE if venue in ("circle", "fireblocks") else _FIAT)
    return {
        "account_id": f"{venue}-{currency.lower()}-{uuid.uuid4().hex[:8]}",
        "venue": venue,
        "currency": currency,
        "available_balance": random.randrange(250_000_00, 25_000_000_00),
        "unsettled_balance": random.randrange(0, 2_000_000_00),
    }
