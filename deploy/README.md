# Deploying Pankh on Oracle Cloud (free)

Everything runs on one server with Docker Compose: the API, the simulators, the officials'
dashboard, Postgres, Temporal, S3-compatible storage (SeaweedFS), the voice agent, and Caddy for
HTTPS. Oracle Cloud's Always Free tier gives an ARM server large enough for all of it, at no cost.

## 1. Create the server (once)

1. Sign up at cloud.oracle.com. Choose **India West (Mumbai)** as the home region; it cannot be
   changed later. A card is asked for identity checks; Always Free resources are not charged.
2. **Compute → Instances → Create instance**
   - Image: **Canonical Ubuntu 24.04**
   - Shape: **Ampere → VM.Standard.A1.Flex**, 4 OCPUs and 24 GB memory (the Always Free maximum)
   - Networking: keep "Assign a public IPv4 address" on
   - SSH keys: upload your public key (`~/.ssh/id_ed25519.pub`, or generate one with
     `ssh-keygen -t ed25519`)
   - If Oracle says it is **out of capacity**, try again later or pick another availability
     domain; free ARM servers in Mumbai are in demand.
3. Open the web ports: on the instance page, **Subnet → Default security list → Add ingress
   rules**, source `0.0.0.0/0`, TCP, destination ports **80** and **443**.

## 2. Deploy

From the repository root on your computer:

```bash
bash deploy/push.sh ubuntu@<server-ip>
```

This copies the code, installs Docker, opens the server's own firewall, generates every secret into
`deploy/.env` on the server, and starts everything. It prints the addresses when done, as free
`sslip.io` names for the server's IP, with HTTPS certificates from Let's Encrypt:

- `https://api.<ip>.sslip.io`: the API the app talks to
- `https://dashboard.<ip>.sslip.io`: the officials' dashboard
- `https://sim.<ip>.sslip.io`: the simulators (DigiLocker sign-in, paper certificates, the browser
  phone at `/phone?api=https://api.<ip>.sslip.io&token=<PANKH_PHONE_WEBHOOK_TOKEN>`)

Run the same command again to deploy changes; secrets and data are kept.

If HTTPS certificates do not appear after a few minutes (`sudo docker compose logs caddy`), the
shared `sslip.io` names may be rate-limited by Let's Encrypt. Create three free names at
duckdns.org pointing at the server's IP, put them in `API_DOMAIN`, `SIM_DOMAIN` and
`DASHBOARD_DOMAIN` in `deploy/.env`, and run `setup.sh` again.

## 3. Keys (optional)

On the server, `nano ~/pankh/deploy/.env`, fill in any of these, and run `bash ~/pankh/deploy/setup.sh`:

- **Voice:** `PANKH_SARVAM_API_KEY` and the three `PANKH_LIVEKIT_…` values. The voice agent starts
  once all are set.
- **JAGO on Bedrock:** `PANKH_BEDROCK_MODEL_ID` (for example `apac.amazon.nova-lite-v1:0`) and an
  IAM access key allowed only to call Bedrock (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`).

## 4. Build the app for it

```bash
cd mobile
flutter build apk --release --dart-define=PANKH_API_URL=https://api.<ip>.sslip.io
```

The APK is at `mobile/build/app/outputs/flutter-apk/app-release.apk`; anyone can install it.

## Signing in

This is a demo deployment: no SMS is sent. Sign-in codes for the synthetic demo numbers (those
starting `90000`) are shown on screen in the app and the dashboard; real numbers never see one.
Demo officials: `90000 00001` (ministry), `…02` (Jharkhand), `…03` (Dumka), `…04` (Mayurbhanj).
Demo students: `90000 00001`…`90000 03000` are the synthetic people in the simulators.

## Looking after it

```bash
ssh ubuntu@<server-ip>
cd pankh/deploy
sudo docker compose ps               # what is running
sudo docker compose logs -f api      # follow the API's log
sudo docker compose restart api      # restart one service
```
