"""Generate an organization-scoped credential for local setup; never run in a build."""
import argparse
import json
from pathlib import Path
import secrets


def main():
    orgs = json.loads((Path(__file__).resolve().parents[1] / "backend/app/data/orgs.json").read_text())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subject", default="Local administrator")
    parser.add_argument("--role", choices=("operator", "reviewer", "admin"), default="admin")
    parser.add_argument("--org", action="append", choices=[org["id"] for org in orgs])
    parser.add_argument("--env-assignment", action="store_true")
    args = parser.parse_args()
    credential = [{"token": secrets.token_urlsafe(32), "subject": args.subject,
                   "role": args.role, "org_ids": args.org or [org["id"] for org in orgs]}]
    print(("API_TOKENS_JSON=" if args.env_assignment else "") + json.dumps(credential, separators=(",", ":")))


if __name__ == "__main__":
    main()
