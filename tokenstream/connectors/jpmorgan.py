"""JPMorgan — acquiring bank. Daily card-settlement files over SFTP.

Models J.P. Morgan Payments' ``SettlementDetails`` report dropped as a daily
CSV over SFTP. The file carries decimal major-unit amounts per currency; this
parses it and normalizes to one settlement row per currency in integer minor
units.

Docs:   https://developer.payments.jpmorgan.com/docs/commerce/optimization-protection/capabilities/reporting/index
Spec:   none — fixed-layout report over SFTP; sample report layouts at
        https://github.com/jpmorgan-payments/online-payments/tree/main/docs/reporting
Auth:   SSH key-based SFTP (OAuth2 client credentials + mTLS for the REST API)
Limits: not publicly documented
"""

import csv
import io
import random
from collections.abc import Iterator
from datetime import date, timedelta

import tractorbeam as tb

from tokenstream.connectors._schemas import SETTLEMENT
from tokenstream.connectors._transport import secret_value, sftp_fetch, to_minor

_HOST = "sftp.jpmorgan.com"
_USERNAME = "tokenstream"


@tb.Connector()
class JPMorganAcquiring:
    """Daily card-settlement files JPMorgan drops over SFTP."""

    sftp: tb.Secret = tb.Secret("jpmorgan_sftp")

    @tb.output(
        "settlement_details",
        trigger=tb.Schedule("0 6 * * *"),
        write_disposition="append",
        primary_key="settlement_id",
        description="Daily acquirer settlement batches in the shared settlement shape.",
        columns=SETTLEMENT,
    )
    def settlement_details(self) -> Iterator[dict]:
        """One settlement batch per currency for the prior day."""
        batch_date = date.today()
        available_on = (batch_date + timedelta(days=1)).isoformat()
        path = f"/outbound/settlement/SETTLEMENT_{batch_date.isoformat()}.csv"
        file = sftp_fetch(
            host=_HOST,
            username=_USERNAME,
            private_key=secret_value(self.sftp),
            path=path,
            mock=_mock_file(batch_date),
        )
        for row in csv.DictReader(io.StringIO(file.text)):
            yield {
                "settlement_id": f"jpm-{row['batch_date']}-{row['currency']}",
                "acquiring_bank_id": "jpmorgan",
                "batch_date": row["batch_date"],
                "gross": to_minor(row["gross"]),
                "fees": to_minor(row["fees"]),
                "net": to_minor(row["net"]),
                "currency": row["currency"],
                "transaction_count": int(row["transaction_count"]),
                "available_on": available_on,
            }


def _mock_file(batch_date: date) -> str:
    rows = ["batch_date,currency,gross,fees,net,transaction_count"]
    for currency in ("USD", "EUR", "GBP"):
        gross = random.uniform(50_000, 5_000_000)
        fees = gross * random.uniform(0.018, 0.029)
        rows.append(
            f"{batch_date.isoformat()},{currency},{gross:.2f},{fees:.2f},"
            f"{gross - fees:.2f},{random.randint(800, 60_000)}"
        )
    return "\n".join(rows)
