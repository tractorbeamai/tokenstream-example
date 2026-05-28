"""Authentication patterns, one function per scheme the sources use.

Everything is stdlib (``hmac``, ``hashlib``, ``base64``) so the example needs
no crypto dependency, and every signature is computed for real against the
mounted secret — only the network send (see ``_transport.send``) is mocked.
Secrets that carry more than one part (an HMAC key plus a passphrase, a
client id plus client secret, an API key plus a PEM) are mounted as a single
colon-joined value and split here.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

from tokenstream.connectors._transport import Request, send


def _split(credential: str, parts: int) -> list[str]:
    """Split a colon-joined credential into exactly ``parts`` fields."""
    return (credential.split(":", parts - 1) + [""] * parts)[:parts]


def bearer(token: str) -> dict[str, str]:
    """OAuth2 / API-key bearer token (Increase, Circle, OANDA, Stripe)."""
    return {"Authorization": f"Bearer {token}"}


def api_key_header(name: str, value: str) -> dict[str, str]:
    """Raw API key in a custom header (Adyen ``X-API-Key``)."""
    return {name: value}


def http_basic(username: str, password: str = "") -> dict[str, str]:
    """HTTP Basic (Column: API key as the username, empty password)."""
    raw = f"{username}:{password}".encode()
    return {"Authorization": "Basic " + base64.b64encode(raw).decode()}


def coinbase_prime_headers(
    credential: str, *, method: str, path: str, body: str = ""
) -> dict[str, str]:
    """Coinbase Prime: HMAC-SHA256 over timestamp+method+path+body, plus passphrase."""
    access_key, signing_key, passphrase = _split(credential, 3)
    timestamp = str(int(time.time()))
    message = f"{timestamp}{method.upper()}{path}{body}".encode()
    signature = base64.b64encode(hmac.new(signing_key.encode(), message, hashlib.sha256).digest())
    return {
        "X-CB-ACCESS-KEY": access_key,
        "X-CB-ACCESS-PASSPHRASE": passphrase,
        "X-CB-ACCESS-SIGNATURE": signature.decode(),
        "X-CB-ACCESS-TIMESTAMP": timestamp,
    }


def kraken_headers(credential: str, *, path: str, data: dict[str, str]) -> dict[str, str]:
    """Kraken: HMAC-SHA512 over path + SHA256(nonce + postdata), key is base64."""
    api_key, api_secret_b64 = _split(credential, 2)
    postdata = "&".join(f"{k}={v}" for k, v in data.items())
    message = path.encode() + hashlib.sha256((data["nonce"] + postdata).encode()).digest()
    try:
        key = base64.b64decode(api_secret_b64 or "AA==")
    except ValueError:
        key = b""
    signature = base64.b64encode(hmac.new(key, message, hashlib.sha512).digest())
    return {"API-Key": api_key, "API-Sign": signature.decode()}


def gemini_headers(credential: str, *, payload: dict[str, Any]) -> dict[str, str]:
    """Gemini: base64 JSON payload signed with HMAC-SHA384."""
    api_key, api_secret = _split(credential, 2)
    encoded = base64.b64encode(json.dumps(payload).encode())
    signature = hmac.new(api_secret.encode(), encoded, hashlib.sha384).hexdigest()
    return {
        "X-GEMINI-APIKEY": api_key,
        "X-GEMINI-PAYLOAD": encoded.decode(),
        "X-GEMINI-SIGNATURE": signature,
    }


def oauth2_client_credentials(
    token_url: str, credential: str, *, scope: str = "", mock_token: str = "mock-access-token"
) -> str:
    """OAuth2 client-credentials grant (Cross River, Paxos, JPMorgan).

    Exchanges a client id/secret for a bearer token. The token endpoint is hit
    through the mocked transport, so ``mock_token`` stands in for the response.
    """
    client_id, client_secret = _split(credential, 2)
    request = Request(
        method="POST",
        url=token_url,
        headers=http_basic(client_id, client_secret),
        json={"grant_type": "client_credentials", "scope": scope},
    )
    body = send(
        request, mock={"access_token": mock_token, "token_type": "Bearer", "expires_in": 3600}
    )
    return str(body.json()["access_token"])


def fireblocks_jwt(credential: str, *, path: str, body: str = "") -> dict[str, str]:
    """Fireblocks: per-request RS256 JWT (api key + RSA private key)."""
    api_key, private_key_pem = _split(credential, 2)
    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT"}
    claims = {
        "uri": path,
        "nonce": str(now),
        "iat": now,
        "exp": now + 55,
        "sub": api_key,
        "bodyHash": hashlib.sha256(body.encode()).hexdigest(),
    }
    signing_input = f"{_b64url(json.dumps(header))}.{_b64url(json.dumps(claims))}"
    token = f"{signing_input}.{_rs256_sign(signing_input, private_key_pem)}"
    return {"X-API-Key": api_key, "Authorization": f"Bearer {token}"}


def _b64url(data: str) -> str:
    return base64.urlsafe_b64encode(data.encode()).rstrip(b"=").decode()


def _rs256_sign(signing_input: str, private_key_pem: str) -> str:
    """RS256-sign ``signing_input`` with the RSA private key.

    Production uses PyJWT / ``cryptography``; mocked with a deterministic
    digest so the example stays dependency-free.
    """
    digest = hashlib.sha256(f"{private_key_pem}.{signing_input}".encode()).digest()
    return _b64url(base64.b64encode(digest).decode())
