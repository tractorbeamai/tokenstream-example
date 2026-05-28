"""Treasury actions — scheduled checks and event-triggered proposals over the reconciled ontology.

``flag_underfunded`` runs every morning and raises an alert for any payout
account that won't cover the next cycle's payouts. ``propose_rebalance``
fires whenever a settlement lands and proposes moving idle cash to cover
upcoming payouts and trim FX drift. Both read the ontology through the
generated SDK and emit changesets for human approval; nothing here moves
money on its own.
"""

import tractorbeam as tb


@tb.Action(namespace="tokenstream.treasury", trigger=tb.Schedule("0 10 * * *"))
def flag_underfunded() -> None:
    """Flag any payout account whose available balance won't cover the next cycle."""


@tb.Action(namespace="tokenstream.treasury", trigger=tb.On("Settlement"))
def propose_rebalance() -> None:
    """On a new settlement, propose rebalancing idle cash and stablecoin to cover payouts."""
