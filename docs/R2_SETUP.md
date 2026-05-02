# Cloudflare R2 Setup — One-Time

This is the click-by-click setup for the BacktestStation cloud warehouse. You only do this once. Total time: ~15 minutes.

## What you're creating

- **One R2 bucket** named `bsdata-prod` — holds the parquet warehouse mirror.
- **Two API tokens** scoped to that bucket:
  1. **`bsdata-uploader`** — read-write. Lives only on `ben-247` (the machine that runs the uploader).
  2. **`bsdata-reader`** — read-only. Distributed to vetted collaborators (Husky/Elijah for now).

## Step 1 — Create the Cloudflare account (skip if you have one)

1. Go to <https://dash.cloudflare.com/sign-up>.
2. Sign up with `benbrainard11@gmail.com`. Use a long password from your password manager.
3. Verify the email link.

## Step 2 — Enable R2

1. In the Cloudflare dashboard left sidebar, click **R2 Object Storage**.
2. The first time you click this, Cloudflare asks you to **subscribe** (note: R2 has a generous free tier — 10 GB storage, 1M Class A operations/month, **zero egress fees forever**). Click **Purchase R2** but don't worry — you won't get charged at our scale.
3. Cloudflare will ask for a payment method. Add one. **You will not actually be billed** at current warehouse size (~few GB). Verify after a month.

## Step 3 — Create the bucket

1. Still in **R2 Object Storage**, click **Create bucket**.
2. Name: **`bsdata-prod`** (exact spelling — the code expects this name).
3. Location: leave as **Automatic** (Cloudflare picks the closest region; doesn't matter for our use case).
4. Storage class: **Standard**.
5. Click **Create bucket**.

## Step 4 — Note your account ID and endpoint URL

1. From the **R2 Object Storage** page, find **Account ID** in the right sidebar (or under Settings).
2. Your **R2 endpoint** is: `https://<ACCOUNT_ID>.r2.cloudflarestorage.com`
3. Copy this into a note you can refer back to. You'll paste it into env vars later.

## Step 5 — Create the uploader token (read-write)

1. R2 Object Storage → click **Manage R2 API Tokens** (top-right corner, or under your bucket).
2. Click **Create API Token**.
3. **Token name:** `bsdata-uploader`
4. **Permissions:** select **Object Read & Write**.
5. **Specify bucket(s):** choose **Apply to specific buckets only** → tick **`bsdata-prod`**.
6. **TTL:** leave as **Forever** (or set a long expiry — your call; just remember to rotate).
7. **Client IP Address Filtering:** leave blank.
8. Click **Create API Token**.
9. **CRITICAL:** the next screen shows the **Access Key ID** and **Secret Access Key** **exactly once**. Copy both into your password manager now — they cannot be recovered.
10. Save them under labels:
    - `BS_R2_ACCESS_KEY` (the Access Key ID)
    - `BS_R2_SECRET` (the Secret Access Key)

## Step 6 — Create the reader token (read-only)

Same flow as Step 5, with three differences:

1. **Token name:** `bsdata-reader`
2. **Permissions:** select **Object Read only** (not Read & Write).
3. Everything else identical (bucket scope = `bsdata-prod`, TTL = Forever).

After clicking Create, save under labels:
- `BS_R2_ACCESS_KEY` (reader token value for collaborator machines)
- `BS_R2_SECRET` (reader token value for collaborator machines)

These are what you'll send Husky over Signal when the pipeline is ready.

## Step 7 — Set env vars on ben-247 (the uploader machine)

When you're back at ben-247, open PowerShell **as Administrator** and run (substitute the actual values you saved):

```powershell
[Environment]::SetEnvironmentVariable("BS_R2_BUCKET", "bsdata-prod", "Machine")
[Environment]::SetEnvironmentVariable("BS_R2_ENDPOINT", "https://<YOUR_ACCOUNT_ID>.r2.cloudflarestorage.com", "Machine")
[Environment]::SetEnvironmentVariable("BS_R2_ACCESS_KEY", "<paste uploader access key>", "Machine")
[Environment]::SetEnvironmentVariable("BS_R2_SECRET", "<paste uploader secret>", "Machine")
```

These are **machine-scope** env vars so the scheduled task picks them up. Restart any open PowerShell windows to see them.

**Do NOT set `BS_DATA_BACKEND=r2` on ben-247** — it stays on `local` because ben-247 reads from local disk. The `r2` backend is for **client** machines only.

## Step 8 — Verify

In a fresh PowerShell on ben-247:

```powershell
$env:BS_R2_BUCKET     # should print: bsdata-prod
$env:BS_R2_ENDPOINT   # should print: https://<account>.r2.cloudflarestorage.com
$env:BS_R2_ACCESS_KEY # should print the access key
```

If all three print, you're done with manual setup. Tell me, and I'll run the uploader smoke test.

## What to send Husky later (after Phase 4 lands)

Send via **Signal** (not chat history, not email):

```
BS_R2_BUCKET=bsdata-prod
BS_R2_ENDPOINT=https://<your-account-id>.r2.cloudflarestorage.com
BS_R2_ACCESS_KEY=<reader access key>
BS_R2_SECRET=<reader secret>
BS_DATA_BACKEND=r2
```

Plus the install command (will be in `client/bsdata/README.md`).

## If you hit problems

- **"Subscribe to R2 first" loop:** add a payment method even if billing won't kick in.
- **Bucket name taken:** R2 bucket names are scoped to your account only, not global. `bsdata-prod` should be available unless you reused it.
- **Forgot to copy secret:** delete the token and create a new one. Secrets are unrecoverable by design.
- **Endpoint format:** the URL must include `https://` for the env var, but inside the code we strip it for `pyarrow.fs.S3FileSystem`. Don't include a trailing slash.
