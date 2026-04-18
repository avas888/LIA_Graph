"""Reset every @lia.dev user in the target Supabase to a known password.

Usage:
    PYTHONPATH=src:. uv run python scripts/seed_local_passwords.py [--password Test123!]

Reads SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY from the environment.
Targets whichever Supabase those point at — local docker or cloud.
Idempotent: safe to run multiple times.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request

from lia_graph.password_auth import hash_password, verify_password


def _req(method: str, url: str, headers: dict, body: dict | None = None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req) as resp:
        text = resp.read().decode() or "null"
        return resp.status, json.loads(text)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--password", default="Test123!")
    parser.add_argument("--email-suffix", default="@lia.dev")
    args = parser.parse_args()

    supa = (os.environ.get("SUPABASE_URL") or "").rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or ""
    if not supa or not key:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required.", file=sys.stderr)
        return 2

    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

    _, users = _req(
        "GET",
        f"{supa}/rest/v1/users?select=user_id,email&email=like.*{args.email_suffix}",
        headers,
    )
    print(f"[seed_local_passwords] target={supa}  users={len(users)}")
    for u in users:
        h = hash_password(args.password)
        assert verify_password(args.password, h)
        status, _ = _req(
            "PATCH",
            f"{supa}/rest/v1/users?user_id=eq.{u['user_id']}",
            headers,
            {
                "password_hash": h,
                "password_reset_required": False,
                "password_updated_at": "now()",
            },
        )
        print(f"  {u['email']}: HTTP {status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
