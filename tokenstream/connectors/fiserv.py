"""Fiserv (First Data) — acquiring bank. Daily settlement files over SFTP.

Models Fiserv acquiring settlement exported from ClientLine Enterprise as a
daily CSV over SFTP. The funding report carries decimal major-unit amounts;
this parses it and normalizes to one settlement row per day in integer minor
units.

Docs:   https://developer.fiserv.com/product/CommerceHub
Spec:   none — Commerce Hub portal is gated; funding reference at
        https://docs.fiserv.dev/public/reference/getfundings
Auth:   SSH key-based SFTP (HMAC-SHA256 request signing for the Commerce Hub API)
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

_HOST = "sftp.fiserv.com"
_USERNAME = "tokenstream"


@tb.Connector()
class Fiserv:
    """Fiserv daily settlement files over SFTP."""

    sftp: tb.Secret = tb.Secret("fiserv_sftp")

    @tb.output(
        "settlement_details",
        trigger=tb.Schedule("0 7 * * *"),
        write_disposition="append",
        primary_key="settlement_id",
        description="Daily acquirer settlement batches in the shared settlement shape.",
        columns=SETTLEMENT,
    )
    def settlement_details(self) -> Iterator[dict]:
        batch_date = date.today()
        available_on = (batch_date + timedelta(days=1)).isoformat()
        path = f"/clientline/funding/FUNDING_{batch_date.strftime('%Y%m%d')}.csv"
        file = sftp_fetch(
            host=_HOST,
            username=_USERNAME,
            private_key=secret_value(self.sftp),
            path=path,
            mock=_mock_file(batch_date),
        )
        for row in csv.DictReader(io.StringIO(file.text)):
            yield {
                "settlement_id": f"fis-{row['funding_date']}-{row['currency']}",
                "acquiring_bank_id": "fiserv",
                "batch_date": row["funding_date"],
                "gross": to_minor(row["gross_amount"]),
                "fees": to_minor(row["fee_amount"]),
                "net": to_minor(row["net_amount"]),
                "currency": row["currency"],
                "transaction_count": int(row["transaction_count"]),
                "available_on": available_on,
            }


def _mock_file(batch_date: date) -> str:
    gross = random.uniform(50_000, 2_000_000)
    fees = gross * random.uniform(0.02, 0.03)
    return (
        "funding_date,currency,gross_amount,fee_amount,net_amount,transaction_count\n"
        f"{batch_date.isoformat()},USD,{gross:.2f},{fees:.2f},{gross - fees:.2f},"
        f"{random.randint(300, 25_000)}"
    )
