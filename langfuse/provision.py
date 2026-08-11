"""Langfuse provisioning: create a project, get API keys, set up dashboard.

Phase 6. Run: `uv run python langfuse/provision.py`.

Creates a Langfuse project via the web UI signup flow (first user becomes admin),
then prints the public/secret keys. For self-hosted Langfuse v2, the first user
signs up via the web UI at http://localhost:3000 — we create that user and
project via the API.
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
        f"{LANGFUSE_HOST}/api/public/registration/setup",
        json={
            "email": "admin@arxiv-agent.local",
            "password": "adminadmin123!",
            "name": "Admin User",
            "organizationName": "arXiv Research",
            "organizationPlan": "PRO",
            "projectName": "arxiv-agent",
        },
        timeout=10,
    )
    if r.status_code == 200:
        return r.json()
    print(f"Setup response ({r.status_code}): {r.text[:300]}")
    return None


def get_project_keys(session: requests.Session):
    r = session.get(f"{LANGFUSE_HOST}/api/public/projects", timeout=10)
    if r.status_code != 200:
        print(f"Failed to get projects ({r.status_code}): {r.text[:300]}")
        return None
    projects = r.json()
    if not projects:
        print("No projects found")
        return None
    return projects[0]


def main() -> int:
    print(f"Waiting for Langfuse at {LANGFUSE_HOST}...")
    if not wait_for_langfuse():
        print("Langfuse not reachable")
        return 1
    print("Langfuse is healthy.")

    print("Setting up first user + project...")
    result = signup_first_user()
    if result:
        print(f"Setup OK: {result}")
    else:
        print("Setup may already be done (expected if re-running).")

    print()
    print("To get API keys:")
    print("1. Open http://localhost:3000 in your browser")
    print("2. Login: admin@arxiv-agent.local / adminadmin123!")
    print("3. Go to Settings → API Keys")
    print("4. Copy the public and secret keys")
    print("5. Add them to .env:")
    print("   LANGFUSE_PUBLIC_KEY=pk-lf-...")
    print("   LANGFUSE_SECRET_KEY=sk-lf-...")
    print()
    print("Then restart the app: docker-compose restart app")

    return 0


if __name__ == "__main__":
    sys.exit(main())