"""Reference — neither stock nor flow.

``FXPair`` is the rate Tokenstream prices conversions against, sourced from
OANDA's closeout bid/ask. Tight freshness keeps conversion decisions on a
current rate.
"""

from typing import Annotated

import tractorbeam as tb


@tb.Object(freshness="5m")
class FXPair:
    """A currency pair and its latest closeout rate."""

    pair: Annotated[str, tb.PrimaryKey, tb.Required]  # e.g. EUR_USD
    base: Annotated[str, tb.Required]
    quote: Annotated[str, tb.Required]
    closeout_bid: Annotated[float, tb.Required]
    closeout_ask: Annotated[float, tb.Required]
    as_of: Annotated[str, tb.Required]
