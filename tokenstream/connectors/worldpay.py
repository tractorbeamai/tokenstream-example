"""Worldpay — acquiring bank. Daily settlement files over SFTP.

Models Worldpay's (FIS) eMAF — the Enhanced Merchant Activity File, a daily
fixed-length flat file over SFTP. Amounts use implied-decimal encoding (the
last two digits are cents), so they parse straight to integer minor units;
this slices the fixed-width fields and normalizes one row per currency.

Docs:   https://docs.worldpay.com/apis/reporting/settlement-research
Spec:   none — fixed-length eMAF flat file; reference guide at
        https://docs.worldpay.com/assets/pdf/Worldpay_EMAF_Reference_Guide_V1.40.pdf
Auth:   SSH key-based SFTP (HTTP Basic for the REST reporting APIs)
Limits: not publicly documented
"""

import random
from collections.abc import Iterator
from datetime import date, timedelta

import tractorbeam as tb

from tokenstream.connectors._schemas import SETTLEMENT
from tokenstream.connectors._transport import secret_value, sftp_fetch

_HOST = "sftp.worldpay.com"
_USERNAME = "tokenstream"

# Fixed-width eMAF settlement record: (field, start, end).
_LAYOUT = {
    "record_type": (0, 2),
    "batch_date": (2, 10),
    "currency": (10, 13),
    "gross": (13, 28),
    "fees": (28, 43),
    "net": (43, 58),
    "transaction_count": (58, 66),
}


@tb.Connector()
class Worldpay:
    """Worldpay daily settlement files over SFTP."""

    sftp: tb.Secret = tb.Secret("worldpay_sftp")

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
        path = f"/outbound/eMAF/EMAF_{batch_date.strftime('%Y%m%d')}.txt"
        file = sftp_fetch(
            host=_HOST,
            username=_USERNAME,
            private_key=secret_value(self.sftp),
            path=path,
            mock=_mock_file(batch_date),
        )
        for line in file.text.splitlines():
            fields = {name: line[start:end].strip() for name, (start, end) in _LAYOUT.items()}
            if fields["record_type"] != "ST":
                continue
            ymd = fields["batch_date"]
            iso_date = f"{ymd[0:4]}-{ymd[4:6]}-{ymd[6:8]}"
            yield {
                "settlement_id": f"wp-{iso_date}-{fields['currency']}",
                "acquiring_bank_id": "worldpay",
                "batch_date": iso_date,
                "gross": int(fields["gross"]),
                "fees": int(fields["fees"]),
                "net": int(fields["net"]),
                "currency": fields["currency"],
                "transaction_count": int(fields["transaction_count"]),
                "available_on": available_on,
            }


def _mock_file(batch_date: date) -> str:
    lines = []
    for currency in ("USD", "GBP"):
        gross = random.randrange(5_000_00, 3_000_000_00)
        fees = round(gross * random.uniform(0.019, 0.028))
        count = random.randint(400, 30_000)
        lines.append(
            "ST"
            + batch_date.strftime("%Y%m%d")
            + f"{currency:<3}"
            + f"{gross:015d}{fees:015d}{gross - fees:015d}{count:08d}"
        )
    return "\n".join(lines)
