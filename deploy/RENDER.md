# Deploying Pankh on Render (free tier)

`render.yaml` at the repository root describes everything, so Render builds and runs it from
GitHub. The free tier is fine for a demo, with limits (see the end).

## Steps

1. Sign up at render.com with GitHub, and allow access to this repository.
2. **New → Blueprint**, pick the repository. Render reads `render.yaml` and shows a Postgres
   database and three web services: the API, the simulators and the officials' dashboard.
3. It asks for the values marked secret. Leave them all empty for a first demo, or fill in:
   - Photo storage in Cloudflare R2 (free 10 GB): see below.
   - Voice and Bedrock keys: only if you add the paid voice worker.
4. **Apply**. The first build takes 10 to 15 minutes. Then open
   `https://pankh-sih-api.onrender.com/health`, which should answer `{"status":"ok"}`.

If Render says a name is taken, it adds a suffix (like `pankh-sih-api-x7k2`). Then, in the
Environment tab of each service, update the addresses that mention the other services, and save.

## Build the app for it

```bash
cd mobile
flutter build apk --release --dart-define=PANKH_API_URL=https://pankh-sih-api.onrender.com
```

## Keeping uploaded photos (optional, free)

Free Render services have no lasting disk, so with the default settings photos are lost whenever
a service restarts. To keep them, use Cloudflare R2:

1. In Cloudflare, **R2 → Create bucket** named `pankh-documents`.
2. **R2 → Manage API tokens → Create token** with Object Read & Write on that bucket. Note the
   access key, the secret and the S3 endpoint (`https://<account-id>.r2.cloudflarestorage.com`).
3. In the API service's Environment tab set `PANKH_OBJECT_STORE=s3`,
   `PANKH_S3_ENDPOINT_URL`, `PANKH_S3_ACCESS_KEY_ID` and `PANKH_S3_SECRET_ACCESS_KEY`.

Photos are encrypted before they are stored, so R2 never holds a readable document.

## Signing in

No SMS is sent. Codes for the synthetic demo numbers (starting `90000`) are shown on screen.
Demo officials: `90000 00001` (ministry), `…02` (Jharkhand), `…03` (Dumka), `…04` (Mayurbhanj).

## What the free tier leaves out

- **Sleeping:** free services stop after 15 minutes without requests; the next request waits about
  50 seconds. Open the API's health address before a demo to wake it.
- **Database:** Render's free Postgres expires after 30 days. Upgrade it (about $7 a month) or
  point `PANKH_DATABASE_URL` at a free Neon database instead.
- **Voice agent:** it must stay on, which needs a paid worker (about $7 a month). Uncomment the
  voice worker in `render.yaml` to add it.
- **Daily jobs:** Temporal is not run, so reminders are not sent daily and old photos are not
  purged automatically. Officials can still start a reminder check from the dashboard.
- **Region:** Singapore, the closest Render region. For production, data should stay in India
  (see `deploy/README.md` for Oracle Cloud in Mumbai).
