"""The normalized output shapes every connector maps its feed into.

Many feeds, one shape: each acquirer's settlement file becomes ``SETTLEMENT``,
each exchange/custodian balance snapshot becomes ``BALANCE``, each sponsor
bank's ACH feed becomes ``ACH``. The schemas are passed to ``@tb.output`` as
``columns=`` so the manifest carries column types and descriptions; the row
bodies in each connector yield exactly these keys.

Monetary amounts are stored as integer minor units (cents). Most providers
report decimal *major* units (e.g. Circle, the exchanges, the acquirer
reports); the per-connector docstrings note where the live feed differs and
the connector body would scale on the way in.
"""

SETTLEMENT = {
    "settlement_id": {
        "column_type": "string",
        "description": "Settlement batch id; one row per currency per day.",
    },
    "acquiring_bank_id": {
        "column_type": "string",
        "description": "Acquirer key; links to the AcquiringBank entity.",
    },
    "batch_date": {
        "column_type": "date",
        "description": "Processing date the batch covers (ISO 8601).",
    },
    "gross": {"column_type": "int64", "description": "Gross processed volume, minor units."},
    "fees": {
        "column_type": "int64",
        "description": "Interchange, scheme fees, and processor markup, minor units.",
    },
    "net": {
        "column_type": "int64",
        "description": "Settled to Tokenstream, minor units (gross minus fees).",
    },
    "currency": {"column_type": "string", "description": "ISO 4217 settlement currency."},
    "transaction_count": {
        "column_type": "int64",
        "description": "Number of card transactions in the batch.",
    },
    "available_on": {
        "column_type": "date",
        "description": "Date settled funds land in the bank account.",
    },
}

BALANCE = {
    "account_id": {"column_type": "string", "description": "Per-venue, per-asset account key."},
    "venue": {
        "column_type": "string",
        "description": "Custody/exchange venue holding the balance.",
    },
    "currency": {
        "column_type": "string",
        "description": "Asset code; ISO 4217 fiat or stablecoin symbol.",
    },
    "available_balance": {
        "column_type": "int64",
        "description": "Spendable balance, minor units (total minus holds).",
    },
    "unsettled_balance": {
        "column_type": "int64",
        "description": "Held/pending balance, minor units.",
    },
    "as_of": {
        "column_type": "timestamptz",
        "description": "Snapshot time the balance was read (RFC 3339).",
    },
}

ACH = {
    "payout_id": {
        "column_type": "string",
        "description": "Provider transfer id; maps to Payout.payout_id.",
    },
    "direction": {
        "column_type": "string",
        "description": "ACH direction; CREDIT for an outbound payout.",
    },
    "amount": {"column_type": "int64", "description": "Transfer amount, minor units (cents)."},
    "currency": {"column_type": "string", "description": "ISO 4217 currency; USD for ACH."},
    "status": {
        "column_type": "string",
        "description": "Normalized: initiated | submitted | settled | returned.",
    },
    "effective_on": {
        "column_type": "date",
        "description": "Effective (settlement) date of the ACH entry.",
    },
    "merchant_id": {
        "column_type": "string",
        "description": "Merchant being paid; links to the Merchant entity.",
    },
    "trace_number": {
        "column_type": "string",
        "description": "15-digit ACH trace number from the ODFI.",
    },
    "return_code": {
        "column_type": "string",
        "description": "NACHA return code (e.g. R01) when returned, else null.",
    },
}

BANK_BALANCE = {
    "account_id": {"column_type": "string", "description": "Bank account identifier."},
    "currency": {"column_type": "string", "description": "ISO 4217 currency of the account."},
    "available_balance": {
        "column_type": "int64",
        "description": "Available balance, minor units (cents).",
    },
    "unsettled_balance": {
        "column_type": "int64",
        "description": "Pending/holds not yet available, minor units.",
    },
    "as_of": {
        "column_type": "timestamptz",
        "description": "Snapshot time the balance was read (RFC 3339).",
    },
}

STABLECOIN_BALANCE = {
    "account_id": {"column_type": "string", "description": "Issuer wallet/profile account key."},
    "currency": {"column_type": "string", "description": "Stablecoin symbol (e.g. USDC, USDP)."},
    "available_balance": {"column_type": "int64", "description": "Available balance, minor units."},
    "unsettled_balance": {
        "column_type": "int64",
        "description": "Reserved/unsettled balance, minor units.",
    },
    "as_of": {
        "column_type": "timestamptz",
        "description": "Snapshot time the balance was read (RFC 3339).",
    },
}

STABLECOIN_TRANSFER = {
    "transfer_id": {"column_type": "string", "description": "Issuer transfer id (UUID)."},
    "amount": {"column_type": "int64", "description": "Transfer amount, minor units."},
    "currency": {"column_type": "string", "description": "Stablecoin symbol (e.g. USDC)."},
    "chain": {
        "column_type": "string",
        "description": "Settlement blockchain (ETH, BASE, SOL, ARB, ...).",
    },
    "status": {
        "column_type": "string",
        "description": "Transfer state: pending | complete | failed.",
    },
    "tx_hash": {
        "column_type": "string",
        "description": "On-chain transaction hash once mined, else null.",
    },
    "created_at": {
        "column_type": "timestamptz",
        "description": "Transfer creation time (RFC 3339).",
    },
}

FX_RATE = {
    "pair": {
        "column_type": "string",
        "description": "Instrument in base_quote form (e.g. EUR_USD).",
    },
    "base": {"column_type": "string", "description": "Base currency (ISO 4217)."},
    "quote": {"column_type": "string", "description": "Quote currency (ISO 4217)."},
    "closeout_bid": {
        "column_type": "numeric",
        "description": "Closeout bid; OANDA returns a decimal string.",
    },
    "closeout_ask": {
        "column_type": "numeric",
        "description": "Closeout ask; OANDA returns a decimal string.",
    },
    "as_of": {
        "column_type": "timestamptz",
        "description": "Quote time from the pricing snapshot (RFC 3339).",
    },
}
