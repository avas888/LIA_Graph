"""Cloudflare Turnstile siteverify wrapper for the public visitor surface.

We hit `https://challenges.cloudflare.com/turnstile/v0/siteverify` server-side
with the user-supplied token + the visitor IP. Any error (missing secret,
network failure, malformed response, `success: false`) results in `False` —
we always fail closed so a Turnstile outage cannot bypass the captcha gate.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

_SITEVERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
_TIMEOUT_SECONDS = 5.0


def verify_turnstile(token: str, remote_ip: str) -> bool:
    """Return True only if Cloudflare confirms the token is valid."""
    token_value = str(token or "").strip()
    if not token_value:
        return False

    secret = str(os.getenv("LIA_PUBLIC_TURNSTILE_SECRET_KEY", "")).strip()
    if not secret:
        return False

    payload = {
        "secret": secret,
        "response": token_value,
    }
    if remote_ip:
        payload["remoteip"] = str(remote_ip).strip()

    body = urllib.parse.urlencode(payload).encode("utf-8")
    request = urllib.request.Request(
        _SITEVERIFY_URL,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
            raw = response.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError, OSError):
        return False

    try:
        data = json.loads(raw)
    except (ValueError, json.JSONDecodeError):
        return False

    return bool(isinstance(data, dict) and data.get("success") is True)
