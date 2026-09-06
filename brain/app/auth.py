from __future__ import annotations

import ipaddress
import os
import secrets
from urllib.parse import urlsplit

from fastapi import HTTPException, Request
from starlette.requests import HTTPConnection


def has_bearer(headers, setting: str) -> bool:
    expected = (os.environ.get(setting) or "").strip()
    scheme, _, supplied = (headers.get("authorization") or "").partition(" ")
    return bool(expected) and scheme.lower() == "bearer" and secrets.compare_digest(
        expected.encode("utf-8"), supplied.strip().encode("utf-8")
    )


def _loopback(host: str) -> bool:
    try:
        address = ipaddress.ip_address(host)
        mapped = getattr(address, "ipv4_mapped", None)
        return (mapped or address).is_loopback
    except ValueError:
        return False


def local_ui_allowed(connection: HTTPConnection) -> bool:
    # Use the transport peer, never a forwarded header or the claimed Host alone.
    peer = connection.client
    if peer is None or not _loopback(peer.host):
        return False
    host = connection.url.hostname or ""
    if host != "localhost" and not _loopback(host):
        return False
    origin = connection.headers.get("origin")
    if origin is None:
        return True  # Local CLI clients do not send Origin.
    try:
        parsed = urlsplit(origin)
        return (
            parsed.scheme in {"http", "https"}
            and parsed.scheme == connection.url.scheme
            and parsed.hostname == host
            and (parsed.port or (443 if parsed.scheme == "https" else 80))
                == (connection.url.port or (443 if connection.url.scheme == "https" else 80))
            and not (parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment)
        )
    except ValueError:
        return False


def require_im_token(request: Request) -> None:
    if not has_bearer(request.headers, "NIULAI_IM_TOKEN"):
        raise HTTPException(401, "authentication_required", headers={"WWW-Authenticate": "Bearer"})
