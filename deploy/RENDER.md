# Deploying Pankh on Render

`render.yaml` at the repository root describes everything, so Render builds and runs it from
GitHub:

| Service | Plan | Cost |
|---|---|---|
| `pankh-sih-api` (the API) | Free | $0; sleeps after 15 minutes idle |
| `pankh-sih-sim` (simulators) | Free | $0; sleeps after 15 minutes idle |
| `pankh-sih-dashboard` (officials) | Free | $0; sleeps after 15 minutes idle |
| `pankh-sih-voice` (JAGO's voice agent) | Starter worker | about $7 a month |
| Database | Neon, free | $0, and it does not expire |

## 1. Create the database on Neon (free, once)

Render's own free database is deleted after 30 days; Neon's free tier has no time limit.

1. Sign up at neon.tech. Create a project named `pankh`, region **AWS Asia Pacific (Singapore)**,
   next to Render's Singapore region.
2. On the project dashboard, **Connect** shows the connection string, which looks like
   `postgresql://neondb_owner:…@ep-….ap-southeast-1.aws.neon.tech/neondb?sslmode=require`.
   Copy it. It is a password: paste it only into Render, never into chat or the repository.

## 2. Create the Blueprint on Render

1. Sign up at render.com with GitHub and allow access to this repository.
2. **New → Blueprint**, pick the repository, branch `main`, and give it a name.
3. Render asks for the values that are not in the repository:
   - `PANKH_DATABASE_URL`: the Neon connection string from step 1 (required)
   - `PANKH_SARVAM_API_KEY`, and `PANKH_LIVEKIT_URL`, `PANKH_LIVEKIT_API_KEY`,
     `PANKH_LIVEKIT_API_SECRET`: the same values as in your local `backend/.env`. The voice
     worker copies the LiveKit values from the API, so they are entered once.
   - Everything else (photo storage, Bedrock, Firebase) can stay empty for now.
4. **Apply**. Render asks for a card because the voice worker is paid; Render credits are used
   first. The first build takes 10 to 20 minutes; each service's **Logs** tab shows progress.
5. Open `https://pankh-sih-api.onrender.com/health`: it should answer `{"status":"ok"}`. The
   API creates the tables and the demo officials by itself on first start.

If Render says a name is taken, it adds a suffix (like `pankh-sih-api-x7k2`). Then update the
addresses that mention the other services: in the API's Environment tab `PANKH_CORS_ORIGINS` and
the four `…pankh-sih-sim.onrender.com…` values, in the dashboard's `PANKH_API_URL`, and in the
voice worker's `PANKH_API_URL`.

## 3. Build the app for it

```bash
cd mobile
flutter build apk --release --dart-define=PANKH_API_URL=https://pankh-sih-api.onrender.com
```

## Signing in

Codes for the synthetic demo numbers (starting `90000`) are shown on screen. Demo officials:
`90000 00001` (ministry), `…02` (Jharkhand), `…03` (Dumka), `…04` (Mayurbhanj). Real numbers
sign in by SMS once `PANKH_FIREBASE_PROJECT_ID` is set and the app is built with Firebase.

## Keeping uploaded photos (optional, free)

Free services have no lasting disk, so photos are lost whenever the API restarts. To keep them,
use Cloudflare R2 (10 GB free): create a bucket `pankh-documents` and an API token with Object
Read & Write on it, then set `PANKH_OBJECT_STORE=s3`, `PANKH_S3_ENDPOINT_URL`
(`https://<account-id>.r2.cloudflarestorage.com`), `PANKH_S3_ACCESS_KEY_ID` and
`PANKH_S3_SECRET_ACCESS_KEY` in the API's Environment tab. Photos are encrypted before they are
stored, so R2 never holds a readable document.

## Good to know

- **Sleeping:** free services stop after 15 minutes without requests; the next one waits about 50
  seconds. Open the API's health address a minute before a demo.
- **Memory:** free services have 512 MB. Everyday use fits; the ministry's coverage run (record
  linkage over the whole roster) is the heaviest job and may need a larger instance.
- **Daily jobs:** Temporal is not run, so reminders are not sent daily and old photos are not
  purged automatically. Officials can still start a reminder check from the dashboard.
- **Region:** Singapore. For production, data should stay in India (see `deploy/README.md`).
