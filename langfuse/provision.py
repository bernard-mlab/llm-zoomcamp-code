"""Langfuse provisioning: create the first user, then guide key setup.

Phase 6. Run: `uv run python langfuse/provision.py`.

Self-hosted Langfuse v2 exposes no public API to create an org/project/API-key
(only the onboarding wizard in the browser does that). This script automates
just the first step — creating the admin user via `POST /api/auth/signup` —
and then prints the remaining manual steps. See `langfuse/README.md` for the
full headless (no-browser) provisioning path, including the documented direct
SQL alternative for org/project/API-key creation.
"""
from __future__ import annotations

import os
import sys
import time

import requests

LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "http://localhost:3000")


def wait_for_langfuse(timeout: int = 60) -> bool:
    for _ in range(timeout // 5):
        try:
            r = requests.get(f"{LANGFUSE_HOST}/api/public/health", timeout=2)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(5)
    return False


def signup_first_user():
    r = requests.post(
        f"{LANGFUSE_HOST}/api/auth/signup",
        json={
            "name": "Admin User",
            "email": "admin@arxiv-agent.local",
            "password": "adminadmin123!",
        },
        timeout=10,
    )
    if r.status_code == 200:
        return r.json()
    print(f"Signup response ({r.status_code}): {r.text[:300]}")
    return None


def main() -> int:
    print(f"Waiting for Langfuse at {LANGFUSE_HOST}...")
    if not wait_for_langfuse():
        print("Langfuse not reachable")
        return 1
    print("Langfuse is healthy.")

    print("Creating first user...")
    result = signup_first_user()
    if result:
        print(f"Signup OK: {result}")
    else:
        print("Signup may already be done (expected if re-running), or the "
              "org/project must be created first via the browser wizard.")

    print()
    print("Self-hosted Langfuse v2 has no public API to create an org/project/")
    print("API-key — only the browser wizard does that (or the SQL path in")
    print("langfuse/README.md for headless setups). To finish provisioning:")
    print("1. Open http://localhost:3000/auth/sign-up in your browser")
    print("2. Login: admin@arxiv-agent.local / adminadmin123!")
    print("3. Follow the onboarding wizard to create an org + project")
    print("4. Go to Settings → API Keys, generate a key pair")
    print("5. Add them to .env:")
    print("   LANGFUSE_PUBLIC_KEY=pk-lf-...")
    print("   LANGFUSE_SECRET_KEY=sk-lf-...")
    print()
    print("Then restart the app: docker compose restart app")

    return 0


if __name__ == "__main__":
    sys.exit(main())