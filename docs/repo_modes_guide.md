# Repository Modes Guide: Public vs. Private Repositories

RemNewz runs entirely on free GitHub Actions. Depending on whether your repository is **Public** or **Private**, GitHub applies different quotas and visibility rules.

This guide explains the trade-offs and provides clear instructions for switching between modes safely.

---

## 1. Public vs. Private Mode Comparison

| Feature | Public Repository | Private Repository (Scheduled Cron) | Private Repository (Cloudflare Webhook) |
| :--- | :--- | :--- | :--- |
| **GitHub Actions Minutes** | **100% Free & Unlimited** | Free tier capped at **2,000 min/mo** | Uses ~10–20 min/mo |
| **Response Latency** | Fast (~3–5 minutes) | Slow (~35 minutes) | **Instantaneous (< 2 seconds)** |
| **Workflow Schedule** | `*/5 * * * *` (every 5 min) | `0,35 * * * *` (every 35 min) | No cron needed (Webhook event) |
| **Privacy / Encryption** | **Mandatory** (`ENCRYPTION_KEY`) | Recommended, but private by default | Recommended |
| **Setup Effort** | 1-Click Fork & Add Secrets | 1-Click Fork + Edit Cron | 1-Click Fork + Cloudflare Worker |

---

## 2. Switching from Public to Private

When converting a repository from Public to Private:

### Step 1: Change Repository Visibility

1. In your GitHub repository, go to **Settings > General**.
2. Scroll to the bottom **Danger Zone**.
3. Click **Change repository visibility > Change to private**.

### Step 2: Adjust Polling Interval (Prevent Quota Exhaustion)

Because private repositories are capped at 2,000 Action minutes per month, a 5-minute poller will exhaust your quota in approximately 7 days.

#### Option A: 35-Minute Poller

1. Open `.github/workflows/commands.yml`.
2. Locate the `cron:` trigger:

   ```yaml
   on:
     schedule:
       - cron: '0,35 * * * *'  # Runs twice an hour (~1,440 min/month)
   ```

3. Commit changes to `main`.

#### Option B: Instantaneous Webhook (Recommended for Private Repos)

If you want instantaneous responses without running a periodic cron:

1. Follow the [Cloudflare Worker Webhook Proxy Guide](cloudflare_worker_guide.md).
2. Remove or comment out the `schedule:` section in `.github/workflows/commands.yml`.

---

## 3. Switching from Private to Public

> [!CAUTION]
> **CRITICAL SECURITY REQUIREMENT:** Before making a private repository public, verify that all task data is encrypted.

### Step 1: Ensure Encryption is Active

1. Go to **Settings > Secrets and variables > Actions**.
2. Verify that `ENCRYPTION_KEY` is present.
3. Check your `data/` folder:
   - Your state database is encrypted as `remnewz.db.enc`.
   - If you have unencrypted database files (`data/remnewz.db`, `*.db`, `*.sqlite3`) or legacy `.json` files in `data/`, do NOT make the repository public until you purge them.

### Step 2: Clean Historical Commits (If Plaintext Was Ever Committed)

If you previously ran in plaintext mode and committed tasks before setting `ENCRYPTION_KEY`:

1. Historical commits may still contain plaintext tasks or an unencrypted database binary (`data/remnewz.db`, `data/*.json`).
2. Untrack plaintext database and state files from git:

   ```bash
   git rm --cached data/*.json data/*.db data/*.sqlite3 data/remnewz.db
   ```

   Ensure `.gitignore` contains rules shielding `*.db`, `*.sqlite3`, `data/*.json`, and `data/*.tmp`.
3. **Mandatory History Purge:** Untracking files only prevents future commits. To guarantee sensitive plaintext data is not exposed when switching visibility to public, you **must** purge history by recreating the orphan `data` branch with only the encrypted database:

   ```bash
   git checkout --orphan data-clean
   git rm -rf .
   git add data/remnewz.db.enc
   git commit -m "chore(init): initial encrypted state"
   git branch -M data-clean data
   git push -f origin data
   ```

   Alternatively, rewrite repository history using tools such as `git filter-repo` to permanently erase plaintext commits. Do not rely solely on `git rm --cached` before changing repository visibility.

### Step 3: Upgrade Polling Interval to 5 Minutes

Once public, GitHub Actions minutes are free and unlimited!

1. Open `.github/workflows/commands.yml`.
2. Change the schedule to run every 5 minutes:

   ```yaml
   on:
     schedule:
       - cron: '*/5 * * * *'
   ```

3. Commit changes to `main`.
4. Go to **Settings > General > Change repository visibility > Change to public**.

---

## 4. Helpful Telegram Commands

You can check your configuration and get direct links at any time in Telegram:

- `/config repo_mode` — Displays your repository options and a direct, one-click link to edit `.github/workflows/commands.yml` on GitHub.
- `/source` — View and manage news and RSS feed sources.
- `/config` — View all active overrides (timezone, topics, news limits).
