"""Counterparty entities Tokenstream moves money through.

Each is a distinct ontology object in the team's own language — an
acquiring bank, a payout (sponsor) bank, a crypto exchange/custodian, the
stablecoin issuer, and the merchants Tokenstream collects for and pays out
to. Accounts and flows link back to these.
"""

from typing import Annotated

import tractorbeam as tb


@tb.Object()
class AcquiringBank:
    """A bank that acquires card payments and drops Tokenstream daily settlement files."""

    bank_id: Annotated[str, tb.PrimaryKey, tb.Required]
    name: Annotated[str, tb.Required]
    bic: str | None


@tb.Object()
class PayoutBank:
    """A sponsor bank Tokenstream pushes ACH payouts through."""

    bank_id: Annotated[str, tb.PrimaryKey, tb.Required]
    name: Annotated[str, tb.Required]
    routing_number: str | None


@tb.Object()
class Exchange:
    """A crypto exchange / custodian where Tokenstream holds fiat and stablecoin balances.

    Per-currency balances are fields on this entity, not separate accounts.
    """

    exchange_id: Annotated[str, tb.PrimaryKey, tb.Required]
    name: Annotated[str, tb.Required]
    usdc_balance: Annotated[int, tb.Required]
    eur_balance: Annotated[int, tb.Required]


@tb.Object()
class StablecoinIssuer:
    """The issuer Tokenstream mints and redeems its stablecoin through (e.g. Circle / USDC)."""

    issuer_id: Annotated[str, tb.PrimaryKey, tb.Required]
    name: Annotated[str, tb.Required]
    stablecoin: Annotated[str, tb.Required]


@tb.Object()
class Merchant:
    """A merchant Tokenstream collects card payments for and pays out to."""

    merchant_id: Annotated[str, tb.PrimaryKey, tb.Required]
    legal_name: Annotated[str, tb.Required]
    region: Annotated[str, tb.Marking("region")]
