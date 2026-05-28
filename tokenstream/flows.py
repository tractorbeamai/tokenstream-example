"""Flows — value moved.

``Payment`` (card money in), ``Settlement`` (the acquirer's daily net to
Tokenstream), and ``Payout`` (ACH out to a merchant). Flows reference the
stocks and entities they move value between, and inherit the merchant's
``region`` marking via ``through=`` so access control follows the money.
"""

from typing import Annotated

import tractorbeam as tb

from tokenstream.entities import AcquiringBank, Merchant
from tokenstream.stocks import Account


@tb.Object()
class Payment:
    """An inbound card payment captured for a merchant."""

    payment_id: Annotated[str, tb.PrimaryKey, tb.Required]
    merchant_id: Annotated[str, tb.Required]
    gross: Annotated[int, tb.Required]  # minor units
    currency: Annotated[str, tb.Required]
    status: Annotated[str, tb.Required]  # authorized | captured | refunded
    captured_at: Annotated[str, tb.Required]

    merchant: Annotated[Merchant | None, tb.Link(join="merchant_id")]
    region: Annotated[str, tb.Marking("region", through="merchant")]


@tb.Object()
class Settlement:
    """A daily acquirer settlement batch — gross minus fees equals net."""

    settlement_id: Annotated[str, tb.PrimaryKey, tb.Required]
    acquiring_bank_id: Annotated[str, tb.Required]
    batch_date: Annotated[str, tb.Required]
    gross: Annotated[int, tb.Required]
    fees: Annotated[int, tb.Required]
    net: Annotated[int, tb.Required]
    currency: Annotated[str, tb.Required]

    acquiring_bank: Annotated[AcquiringBank | None, tb.Link(join="acquiring_bank_id")]


@tb.Object()
class Payout:
    """An ACH payout pushed to a merchant from a payout account."""

    payout_id: Annotated[str, tb.PrimaryKey, tb.Required]
    merchant_id: Annotated[str, tb.Required]
    account_id: Annotated[str, tb.Required]
    amount: Annotated[int, tb.Required]  # minor units
    currency: Annotated[str, tb.Required]
    status: Annotated[str, tb.Required]  # initiated | submitted | settled | returned
    effective_on: Annotated[str, tb.Required]

    merchant: Annotated[Merchant | None, tb.Link(join="merchant_id")]
    account: Annotated[Account | None, tb.Link(join="account_id")]
    region: Annotated[str, tb.Marking("region", through="merchant")]
