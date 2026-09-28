"""Fill a running Pankh with demo Students who link DigiLocker the way the app does.

Usage (from backend/, with the API on :8000, simulators on :8100 and the console SMS sender):
    uv run python tools/demo_data.py --log ../path/to/api.log [--count 12]

Each Student signs in with an OTP (read from the API log, since no SMS is sent in
development), answers nothing, and links DigiLocker as a synthetic person. People whose
certificates disagree with their Aadhaar are chosen first, so the review queues have work.
"""

import argparse
import re
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
from pankh_simulators.population import population

from app.verification.names import match_names

API = "http://localhost:8000/v1"
SIMULATOR = "http://localhost:8100"


def otp_from_log(log: Path, phone: str) -> str:
    for _ in range(50):
        codes = re.findall(rf"OTP for {re.escape(phone)} is (\d{{6}})", log.read_text())
        if codes:
            return codes[-1]
        time.sleep(0.1)
    raise RuntimeError(f"No OTP for {phone} in {log}")


def sign_in(client: httpx.Client, log: Path, phone: str) -> dict[str, str]:
    client.post(f"{API}/auth/otp/request", json={"phone": phone}).raise_for_status()
    tokens = client.post(
        f"{API}/auth/otp/verify", json={"phone": phone, "code": otp_from_log(log, phone)}
    )
    tokens.raise_for_status()
    return {"Authorization": f"Bearer {tokens.json()['access_token']}"}


def link_digilocker(client: httpx.Client, auth: dict[str, str], person_id: str) -> dict:
    start = client.post(f"{API}/me/digilocker/start", headers=auth)
    start.raise_for_status()
    query = parse_qs(urlparse(start.json()["authorization_url"]).query)
    consent = client.post(
        f"{SIMULATOR}/digilocker/public/oauth2/1/authorize",
        data={
            key: query[key][0] for key in ("client_id", "redirect_uri", "state", "code_challenge")
        }
        | {"person_id": person_id},
    )
    callback = parse_qs(urlparse(consent.headers["location"]).query)
    done = client.post(
        f"{API}/me/digilocker/complete",
        headers=auth,
        json={"code": callback["code"][0], "state": callback["state"][0]},
    )
    done.raise_for_status()
    return done.json()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path, required=True, help="the API's log file")
    parser.add_argument("--count", type=int, default=12)
    parser.add_argument("--district", help="only people from this district")
    parser.add_argument("--first-phone", type=int, default=0, help="number the phones from here")
    args = parser.parse_args()

    people = sorted(
        (
            p
            for p in population().people
            if p.has_caste_certificate and (args.district is None or p.district == args.district)
        ),
        key=lambda p: (
            match_names(p.caste_certificate_spelling, p.name).is_match,
            not p.stale_income_certificate,
        ),
    )
    with httpx.Client(timeout=30, follow_redirects=False) as client:
        for index, person in enumerate(people[: args.count]):
            phone = f"+9196{args.first_phone + index:08d}"
            auth = sign_in(client, args.log, phone)
            result = link_digilocker(client, auth, person.id)
            print(
                f"{phone}  {person.name:<24} {person.district}, {person.state.name}: "
                f"{len(result['proofs'])} proofs, {len(result['exceptions'])} for review"
            )


if __name__ == "__main__":
    main()
