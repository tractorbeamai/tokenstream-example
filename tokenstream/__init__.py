"""tokenstream — a stablecoin payments company's treasury, modeled on Tractorbeam.

Tokenstream is a fictional stablecoin payments company. It sits between
merchants, acquiring banks, crypto exchanges, a stablecoin issuer, and
payout banks, and has to reconcile balances across all of them to keep
every account funded for payouts while minimizing idle cash and FX drift.

Submodules are not eagerly imported here. ``tractorbeam apply`` walks the
workspace and ``tb.from_modules`` walks the package; eager imports would
double-fire the decorators when both paths run in the same process. The
manifest is assembled explicitly in ``definitions.py``.
"""
