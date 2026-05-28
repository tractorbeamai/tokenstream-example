"""OANDA — FX rates. Live v20 pricing.

Models OANDA's v20 ``GET /v3/accounts/{accountID}/pricing`` endpoint. The live
feed returns a ClientPrice per instrument with ``closeoutBid``/``closeoutAsk``
as decimal strings and an RFC 3339 ``time``; this keeps the rates as numbers
on the normalized FX shape.

Docs:   https://developer.oanda.com/rest-live-v20/pricing-ep/
Spec:   https://raw.githubusercontent.com/oanda/v20-openapi/master/json/separate/v20_pricing.json
Auth:   Bearer token (Authorization)
Limits: 120 req/s per IP; 20 active streaming connections per IP
"""

import random
from collections.abc import Iterator
from datetime import UTC, datetime

import tractorbeam as tb

from tokenstream.connectors import _auth
from tokenstream.connectors._schemas import FX_RATE
from tokenstream.connectors._transport import Request, secret_value, send

_BASE = "https://api-fxtrade.oanda.com"
_ACCOUNT = "001-001-1234567-001"
_MIDS = {"EUR_USD": 1.085, "GBP_USD": 1.270}


@tb.Connector()
class OANDA:
    """Live FX pricing from OANDA's v20 API."""

    token: tb.Secret = tb.Secret("oanda_token")

    @tb.output(
        "fx_rates",
        trigger=tb.Schedule("*/5 * * * *"),
        write_disposition="replace",
        primary_key="pair",
        description="Closeout bid/ask per pair in the shared FX-rate shape.",
        columns=FX_RATE,
    )
    def fx_rates(self) -> Iterator[dict]:
        instruments = ",".join(_MIDS)
        # GET /v3/accounts/{id}/pricing — https://developer.oanda.com/rest-live-v20/pricing-ep/
        request = Request(
            "GET",
            f"{_BASE}/v3/accounts/{_ACCOUNT}/pricing",
            headers=_auth.bearer(secret_value(self.token)),
            params={"instruments": instruments},
        )
        mock = {
            "time": datetime.now(UTC).isoformat(),
            "prices": [_mock_price(p, m) for p, m in _MIDS.items()],
        }
        for price in send(request, mock=mock).json()["prices"]:
            base, quote = price["instrument"].split("_")
            yield {
                "pair": price["instrument"],
                "base": base,
                "quote": quote,
                "closeout_bid": float(price["closeoutBid"]),
                "closeout_ask": float(price["closeoutAsk"]),
                "as_of": price["time"],
            }


def _mock_price(instrument: str, mid: float) -> dict:
    mid += random.uniform(-0.004, 0.004)
    spread = mid * 0.0001
    return {
        "instrument": instrument,
        "closeoutBid": f"{mid - spread:.5f}",
        "closeoutAsk": f"{mid + spread:.5f}",
        "time": datetime.now(UTC).isoformat(),
        "tradeable": True,
    }
