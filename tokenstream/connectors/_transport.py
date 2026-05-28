"""The network boundary — mocked so the example runs without credentials.

A real connector builds an authenticated request, sends it to the provider,
and maps the response into its output rows. Everything around the send is
real here — URL, query params, and the auth headers built in ``_auth`` are
constructed exactly as in production. Only the send itself is stubbed:
``send`` and ``sftp_fetch`` return the ``mock`` payload (shaped like the
provider's real response) instead of going out over the wire, so the
workspace materializes offline. In production you swap the one marked line
for an ``httpx`` (or ``paramiko``) call and delete the ``mock`` argument.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from tractorbeam import Secret


@dataclass(slots=True)
class Request:
    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    params: dict[str, str] = field(default_factory=dict)
    json: dict[str, Any] | None = None


@dataclass(slots=True)
class Response:
    status_code: int
    body: Any

    def json(self) -> Any:
        return self.body

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}: {self.body}")


def send(request: Request, *, mock: Any) -> Response:
    """Send ``request`` and return the response.

    Production body:
        return httpx.request(request.method, request.url, headers=request.headers,
                             params=request.params, json=request.json)
    Mocked: ``request`` is fully built (auth headers included) by the caller;
    this returns a provider-shaped payload so the example runs offline.
    """
    # In production these drive the real call; the mock only needs `mock`.
    _ = (request.method, request.url, request.headers, request.params, request.json)
    return Response(200, mock)


@dataclass(slots=True)
class SftpFile:
    path: str
    text: str


def sftp_fetch(*, host: str, username: str, private_key: str, path: str, mock: str) -> SftpFile:
    """Download ``path`` over SFTP, authenticating with an SSH ``private_key``.

    Production body opens an SSH/SFTP session (e.g. ``paramiko``) keyed by
    ``private_key`` and reads ``path``. Mocked: returns the settlement file
    body so the example runs offline.
    """
    # In production these open and authenticate the SSH session.
    _ = (host, username, private_key)
    return SftpFile(path=path, text=mock)


def secret_value(secret: Secret) -> str:
    """The plaintext the platform mounts for a declared ``tb.Secret``.

    Mirrors the worker's mount convention (``TRACTORBEAM_SECRET_<NAME>``); a
    connector declares the secret as a class attribute and reads its value
    here. Returns "" when unset so the auth code still runs locally.
    """
    return os.environ.get(f"TRACTORBEAM_SECRET_{secret.name.upper()}", "")


def to_minor(amount: str | Decimal, *, places: int = 2) -> int:
    """Decimal major units (``"1234.56"``) to integer minor units (``123456``)."""
    scaled = (Decimal(str(amount)) * (10**places)).to_integral_value(rounding=ROUND_HALF_UP)
    return int(scaled)
