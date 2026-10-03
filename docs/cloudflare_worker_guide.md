# Cloudflare Worker Webhook Proxy Guide

An optional, 100% free guide for configuring instantaneous, sub-second responses and eliminating GitHub Actions minute limits for private repositories.

---

## Table of Contents

- [Why Use a Webhook Proxy?](#why-use-a-webhook-proxy)
- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Step 1: Create a GitHub Personal Access Token (PAT)](#step-1-create-a-github-personal-access-token-pat)
- [Step 2: Create a Cloudflare Worker](#step-2-create-a-cloudflare-worker)
- [Step 3: Configure Worker Environment Variables](#step-3-configure-worker-environment-variables)
- [Step 4: Deploy the Worker Code](#step-4-deploy-the-worker-code)
- [Step 5: Register the Webhook with Telegram](#step-5-register-the-webhook-with-telegram)
- [Step 6: (Optional) Optimize for Private Repositories](#step-6-optional-optimize-for-private-repositories)
- [Troubleshooting & Rollback](#troubleshooting--rollback)

---

## Why Use a Webhook Proxy?

By default, RemNewz uses GitHub Actions scheduled crons (`*/5 * * * *`) to poll Telegram for messages. While this works effortlessly on public repositories (where GitHub Actions minutes are free and unlimited), it presents two drawbacks:

1. **Latency:** Responses can take between a few seconds up to 5 minutes depending on when the cron triggers.
2. **Action Minute Limits on Private Repositories:** Free private GitHub repositories receive 2,000 Action minutes per month. A 5-minute poller uses ~8,600 minutes/month, exceeding the quota.

**The Solution:**
Cloudflare Workers provides a generous free tier of **100,000 requests per day** with zero cold starts and no credit card required. With this proxy:

- GitHub Actions only runs when you actually send a message to your bot.
- Messages are processed almost instantaneously (sub-second trigger).

---

## Architecture Overview

```text
[Telegram Message]
       │
       ▼ (Instant HTTPS POST)
[Cloudflare Worker]
       │
       ▼ (Validates Secret & POSTs repository_dispatch)
[GitHub Actions (commands.yml)]
       │
       ▼ (Executes main_commands.py & pushes state)
[Telegram Reply Sent to You]
```

---

## Prerequisites

- Your forked or cloned **RemNewz** repository.
- A free account on [Cloudflare](https://dash.cloudflare.com/) (no credit card required).
- Your Telegram Bot Token from [@BotFather](https://t.me/BotFather).

---

## Step 1: Create a GitHub Personal Access Token (PAT)

The Cloudflare Worker needs authorization to trigger a `repository_dispatch` event on your repository.

1. In GitHub, click your profile icon (top right) → **Settings**.
2. Scroll to the bottom of the left sidebar and select **Developer settings** → **Personal access tokens** → **Fine-grained tokens**.
3. Click **Generate new token**.
4. Configure the token details:
   - **Token name:** `RemNewz Cloudflare Dispatcher`
   - **Expiration:** Choose your preferred expiration period (e.g. 90 days, 1 year).
   - **Repository access:** Choose **Only select repositories** → Select your `RemNewz` repository.
5. In **Permissions** → **Repository permissions**:
   - Find **Contents** → Change access to **Read and write**. *(Required by GitHub to trigger `repository_dispatch`).*
   - *(Optional)* Find **Actions** → Change access to **Read and write**.
6. Click **Generate token** at the bottom and copy the `github_pat_...` string.

---

## Step 2: Create a Cloudflare Worker

1. Log into your [Cloudflare Dashboard](https://dash.cloudflare.com/).
2. In the left navigation menu, go to **Compute (Workers) > Workers & Pages**.
3. Click **Create application**.
4. Select **Start with Hello World!**.
5. Set your worker name (e.g., `remnewz-telegram-proxy`).
6. If this is your first worker, choose your free `*.workers.dev` subdomain when prompted.
7. Click **Deploy**.

---

## Step 3: Configure Worker Environment Variables

1. On your worker dashboard page, navigate to **Settings** → **Variables and Secrets**.
2. Click **Add** for each of the following variables:

| Variable Name | Type | Value | Description |
| :--- | :--- | :--- | :--- |
| `GITHUB_OWNER` | Plain text / Secret | `your-github-username` | Your GitHub account or organization name |
| `GITHUB_REPO` | Plain text / Secret | `RemNewz` | Your repository name |
| `GITHUB_PAT` | **Secret (Encrypted)** | `github_pat_xxxxxxxx` | The GitHub token created in Step 1 |
| `TELEGRAM_SECRET_TOKEN` | **Secret (Encrypted)** | *(see below)* | A **cryptographically random** secret string to authenticate incoming Telegram requests |

1. Click **Deploy** / **Save**.

> **⚠️ Security: Generate a strong `TELEGRAM_SECRET_TOKEN`**
>
> Do **not** use a simple or guessable value. Generate a cryptographically random token using one of these commands:
>
> **Python:**
> ```bash
> python -c "import secrets; print(secrets.token_urlsafe(32))"
> ```
>
> **PowerShell:**
> ```powershell
> -join ((1..44) | ForEach-Object { [char](Get-Random -Minimum 33 -Maximum 127) })
> ```
>
> Copy the output and use it as your `TELEGRAM_SECRET_TOKEN` value in both Cloudflare Worker secrets and the Telegram webhook registration (Step 5).

> **Note:** Keep your `TELEGRAM_SECRET_TOKEN` handy, as you will use this exact string when registering the webhook with Telegram.

---

## Step 4: Deploy the Worker Code

1. Return to the worker page and click **Edit code** (or **Quick Edit**).
2. Replace all existing code in `worker.js` with the following:

```javascript
export default {
  async fetch(request, env) {
    // Only accept POST requests from Telegram
    if (request.method !== "POST") {
      return new Response("Method Not Allowed", { status: 405 });
    }

    // Security check: Validate Telegram Secret Token header
    const secretHeader = request.headers.get("X-Telegram-Bot-Api-Secret-Token");
    if (env.TELEGRAM_SECRET_TOKEN && secretHeader !== env.TELEGRAM_SECRET_TOKEN) {
      return new Response("Unauthorized", { status: 401 });
    }

    try {
      const updateData = await request.json();

      // Trigger GitHub repository_dispatch event
      const githubUrl = `https://api.github.com/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/dispatches`;

      const response = await fetch(githubUrl, {
        method: "POST",
        headers: {
          "Accept": "application/vnd.github.v3+json",
          "Authorization": `Bearer ${env.GITHUB_PAT}`,
          "User-Agent": "Cloudflare-Worker-RemNewz-Proxy",
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          event_type: "telegram-webhook",
          client_payload: {
            update: updateData
          }
        })
      });

      if (!response.ok) {
        const errorText = await response.text();
        return new Response(`GitHub dispatch failed: ${errorText}`, { status: 500 });
      }

      // Return 200 OK to Telegram to confirm delivery
      return new Response(JSON.stringify({ ok: true }), {
        headers: { "Content-Type": "application/json" },
        status: 200
      });
    } catch (err) {
      return new Response(`Error: ${err.message}`, { status: 500 });
    }
  }
};
```

1. Click **Deploy** in the top right.
2. Note your Worker URL: `https://<worker-name>.<your-subdomain>.workers.dev`.

> **Tip:** If you see `Method Not Allowed` in Cloudflare's preview panel, don't worry! The preview panel sends `GET` requests, which your worker correctly rejects.

---

## Step 5: Register the Webhook with Telegram

Inform Telegram to route all incoming bot messages to your Cloudflare Worker URL.

### Option A: PowerShell (Windows)

```powershell
$BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
$WORKER_URL = "https://<worker-name>.<your-subdomain>.workers.dev"
$SECRET_TOKEN = "AnyRandomSecretKey123" # Must match TELEGRAM_SECRET_TOKEN in Step 3

Invoke-RestMethod -Uri "https://api.telegram.org/bot$BOT_TOKEN/setWebhook" `
  -Method Post `
  -Body (@{ url = $WORKER_URL; secret_token = $SECRET_TOKEN } | ConvertTo-Json) `
  -ContentType "application/json"
```

### Option B: cURL (macOS / Linux / Bash)

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_TELEGRAM_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://<worker-name>.<your-subdomain>.workers.dev",
    "secret_token": "AnyRandomSecretKey123"
  }'
```

**Expected Response:**

```json
{"ok": true, "result": true, "description": "Webhook was set"}
```

---

## Step 6: (Optional) Optimize for Private Repositories

If you are running RemNewz in a **Private repository** and want to conserve 100% of your scheduled minutes:

1. Open `.github/workflows/commands.yml`.
2. Comment out or delete the `schedule` block:

```yaml
on:
  workflow_dispatch:
  repository_dispatch:
    types: [telegram-webhook]
  # schedule:
  #   - cron: '*/5 * * * *'
```

1. Commit and push the changes.

Now, `commands.yml` will only run when you send a message to your bot.

> **Note on Task Deadlines:** If you disable the cron poller completely, reminder evaluations (`remzy.check_deadlines()`) will occur whenever you interact with the bot or when the daily news digest runs (`digest.yml`). If you want background deadline checks without burning private minutes, keep the cron at a relaxed cadence such as `0 * * * *` (once per hour).

---

## Troubleshooting & Rollback

### Check Live Worker Logs

In your Cloudflare Worker dashboard, navigate to the **Logs** tab and click **Begin log stream**. Send a message in Telegram to observe the incoming request and GitHub dispatch status in real time.

### Check GitHub Actions

In your repository, navigate to the **Actions** tab. You should see a workflow run titled **Commands Poller** triggered by `repository_dispatch`.

### Reverting Back to Standard Polling

If you ever want to remove the webhook and switch back to default GitHub Actions polling:

**PowerShell:**

```powershell
Invoke-RestMethod -Uri "https://api.telegram.org/bot<YOUR_TELEGRAM_BOT_TOKEN>/deleteWebhook"
```

**cURL:**

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_TELEGRAM_BOT_TOKEN>/deleteWebhook"
```

Telegram will resume standard update queuing, and `main_commands.py` will automatically resume polling via `get_updates()`.
