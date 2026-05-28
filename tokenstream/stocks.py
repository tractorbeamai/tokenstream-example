"""Stocks — balances held.

An ``Account`` is value sitting somewhere at a point in time: a fiat
operating or payout account at a bank, or a stablecoin wallet at the
issuer. Exactly one counterparty link is set per account. (Balances held
on an exchange are fields on the ``Exchange`` entity, not their own
accounts.)
"""

from typing import Annotated

import tractorbeam as tb

from tokenstream.entities import (
    AcquiringBank,
    PayoutBank,
    StablecoinIssuer,
)


@tb.Object(freshness="1h")
class Account:
    """A fiat or stablecoin balance Tokenstream holds at a counterparty."""

    account_id: Annotated[str, tb.PrimaryKey, tb.Required]
    purpose: Annotated[str, tb.Required]  # operating | payout | treasury
    currency: Annotated[str, tb.Required]
    available_balance: Annotated[int, tb.Required]  # minor units
    unsettled_balance: Annotated[int, tb.Required]  # minor units
    region: Annotated[str, tb.Marking("region")]

    # Held at exactly one of these counterparties.
    acquiring_bank: Annotated[AcquiringBank | None, tb.Link(join="acquiring_bank_id")]
    payout_bank: Annotated[PayoutBank | None, tb.Link(join="payout_bank_id")]
    issuer: Annotated[StablecoinIssuer | None, tb.Link(join="issuer_id")]
