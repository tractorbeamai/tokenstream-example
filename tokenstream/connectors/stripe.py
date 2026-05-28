"""Stripe — the one turnkey integration, configured as a managed connector.

The platform implements the Stripe integration; this only references it by
``type``. The data of interest is the Balance and Balance Transactions feed
(integer minor units, lowercase ISO 4217 currency, unix-epoch timestamps).

Docs:   https://docs.stripe.com/api/balance_transactions
Spec:   https://raw.githubusercontent.com/stripe/openapi/master/openapi/spec3.json
Auth:   Bearer secret API key (sk_live_… / sk_test_…)
Limits: 100 req/s in live mode; individual endpoints default to 25 req/s
"""

import tractorbeam as tb

stripe = tb.ManagedConnector(
    name="stripe",
    type="stripe",
    secrets={"api": tb.Secret("stripe_api_key")},
    trigger=tb.Schedule("*/30 * * * *"),
    description="Stripe balance and balance-transaction settlement activity.",
)
