<div align="center">
  <img src="./assets/remnewz_banner.jpg" alt="RemNewz Logo" width="100%">
</div>

<br/>

An autonomous, serverless Telegram bot that acts as your personal AI News Anchor and Task Master, running entirely on free GitHub Actions.

RemNewz fetches top posts from HackerNews and trending GitHub repositories based on your interests, uses an AI (Gemini, OpenRouter, or Groq) to synthesize them into concise, informative summaries, and delivers them directly to your Telegram.

It also functions as a full Natural Language Processing (NLP) Task Manager. Simply interact with it via chat (e.g., `/todo Remind me to review the architecture doc tomorrow at 5pm`), and it will parse your deadline, store it securely using Fernet encryption (AES-128-CBC), and notify you when it is due.

## Features

- **Serverless News Digest:** Runs autonomously on a daily GitHub Actions cron (08:00 UTC) with on-demand `/digest` execution.
- **Instant News & Keyword Search:** Search live technical topics on demand using `/news <topic>`.
- **Multi-Provider AI Synthesis:** Pluggable support for Gemini, Groq, or OpenRouter (with built-in fallback mechanisms).
- **NLP Task Management:** Includes a personal assistant interface that understands natural language deadlines.
- **Intelligent Due Checker:** Reminds you of pending tasks without overwhelming your inbox (24-hour snooze gap for overdue tasks).
- **Privacy First (Unified Encrypted SQLite Engine):** Automatically encrypts your entire database (`remnewz.db.enc`) with Fernet (AES-128-CBC) before pushing to GitHub. This enables transactional SQL task management and settings while allowing you to securely run in a free Public Repository without exposing personal data.
- **Dedicated Data Branch & Zero Git Clutter:** Code (`main`) and state (`data`) are strictly separated. Automated state syncs never touch `main`, keeping your personal GitHub activity graph and repository history 100% clean.
- **Automated Monthly Maintenance:** A monthly scheduled workflow (`maintenance.yml`) consolidates historical sync commits on the `data` branch down to a single clean snapshot commit.

## Setup Guide

Setting up RemNewz takes less than 5 minutes and runs on **100% free services** (GitHub Actions, Telegram Bot API, Google AI Studio, and Cloudflare Workers).

---

### Step 1: Obtain Required Tokens & Credentials (Prerequisites)

Before launching the setup wizard or manual configuration, have the following keys ready. For a detailed, screenshot-backed walkthrough, see the **[Token & API Key Generation Guide](docs/token_generation_guide.md)**.

1. **Telegram Bot Token:** Message [@BotFather](https://t.me/BotFather) on Telegram, send `/newbot`, follow the prompts, and copy the **HTTP API Token**. Then open your new bot's chat and tap **Start** (or send `/start`).
2. **Telegram Chat ID:** Auto-detected by `setup.py` when you send `/start`, or find it manually via `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`.
3. **AI API Key (Google Gemini):** Get a free API key at [Google AI Studio](https://aistudio.google.com/app/apikey) (*Pluggable support for Groq or OpenRouter also available*).
4. **GitHub Personal Access Token (PAT):** Go to [GitHub Settings > Developer Settings > Personal access tokens](https://github.com/settings/tokens). Generate a token with `repo` scope (or fine-grained token with `Contents: Read and write`). This allows Cloudflare to trigger instant webhook responses and provisions secrets.
5. **Cloudflare Account (Optional/Recommended):** Create a free account at [dash.cloudflare.com](https://dash.cloudflare.com/sign-up) for instant sub-second bot replies.

---

### Step 2: Choose Your Deployment Method

Select either the **Automated Setup Wizard** (handles secrets, Cloudflare worker, and webhook linkage for you) or **Manual Setup**.

#### Option A: Automated Setup Wizard (Recommended)

The easiest way to set up RemNewz is to use our interactive wizard inside a free GitHub Codespace. This method requires zero local installations and automatically configures your Telegram Bot, GitHub Secrets, database encryption, and a free Cloudflare Webhook proxy for instant replies.

1. **Create Repository:** Click **Use this template** at the top of this repository and name your new repo.
2. **Open Codespace:** In your new repository, click the **`<> Code`** button, select the **Codespaces** tab, and click **Create codespace on main**.
3. **Install Dependencies & Run Wizard:** Once the browser terminal loads, run:
   ```bash
   pip install -r requirements.txt
   python setup.py
   ```
4. **Follow Interactive Prompts:** Paste your prepared API keys. The wizard will validate tokens in real time, auto-detect your Telegram Chat ID, provision your GitHub Secrets, deploy the Cloudflare Worker, and link your Telegram webhook automatically.
5. **Delete Codespace (Recommended):** Once setup completes and you receive the Telegram confirmation message, you can safely close and delete your Codespace at [github.com/codespaces](https://github.com/codespaces) to free up your monthly storage quota and wipe the temporary `.env` cache.

---

#### Option B: Manual Setup (Without Wizard)

If you prefer to configure everything manually or without using GitHub Codespaces, follow these steps:

1. **Create Your Repository:**
   - Click **Use this template** at the top of this repository.
   - Choose **Public** (unlimited free GitHub Actions minutes; personal data is AES-128 encrypted) or **Private** (capped at 2,000 min/month; set cron in `.github/workflows/commands.yml` to `*/30 * * * *` or use a Webhook).

2. **Generate Database Encryption Key:**
   - Run this Python snippet to generate a secure Fernet key:
     ```python
     from cryptography.fernet import Fernet
     print(Fernet.generate_key().decode('utf-8'))
     ```

3. **Configure GitHub Secrets:**
   - In your repository, go to **Settings > Secrets and variables > Actions** and add the following **Repository Secrets**:
     - `TELEGRAM_BOT_TOKEN`: The token provided by @BotFather.
     - `TELEGRAM_CHAT_ID`: Your personal numeric chat ID.
     - `AI_PROVIDER`: `gemini` (or `groq` / `openrouter`).
     - `AI_MODEL`: `gemini-2.0-flash` (or your preferred model string).
     - `GEMINI_API_KEY`: Your key from Google AI Studio (or `GROQ_API_KEY` / `OPENROUTER_API_KEY`).
     - `GITHUB_PAT`: Your GitHub Personal Access Token (with `repo` / `Contents:write` access).
     - `ENCRYPTION_KEY`: The Fernet key generated in step 2.

4. **Start the Bot:**
   - Navigate to the **Actions** tab in your repository and accept the prompt to enable workflows.
   - Select **Register Bot Commands**, then click **Run workflow** (registers `/` autocomplete menu with Telegram).
   - Select **Commands Poller**, then click **Run workflow**.
   - Open Telegram and send `/help`. RemNewz is now active and ready!

5. **(Recommended) Deploy Webhook Proxy:**
   - For sub-second responses and zero idle runner minute consumption, follow the [Cloudflare Worker Webhook Proxy Guide](docs/cloudflare_worker_guide.md).

## Commands and User Guide

RemNewz features three built-in personas: **Newzy** (News), **Remzy** (Tasks), and **Helpzy** (Configuration).

- `/digest` - Get your daily AI news digest immediately on-demand.
- `/news [query]` - Instant news and search (e.g., `/news python`, `/news local llm`).
- `/todo <description>` - Create an NLP task with parsed deadlines and priorities.
- `/list` - View active tasks.
- `/done <id>` - Mark a task complete and archive it.
- `/remove <id>` - Permanently delete a task.
- `/history` - View recently completed tasks.
- `/search <query>` - Search active and archived tasks.
- `/stats` - View productivity analytics and completion rates.
- `/source` - View, add (`/source add <url> [label]`), or remove news/RSS feed sources.
- `/config` - View and manage dynamic settings (timezone, style, topics, news limits, forum routing).
- `/help` - Display command summary and operational help.

For a full reference of commands, natural language examples, and Supergroup topic routing instructions, see the [RemNewz User Guide](docs/user_guide.md).

### Documentation & Guides

- 📖 **[User Guide & Persona Reference](docs/user_guide.md)** — Comprehensive command reference, natural language examples, and Telegram Supergroup setup.
- 🔑 **[Token & API Key Generation Guide](docs/token_generation_guide.md)** — Step-by-step instructions for BotFather, Gemini, GitHub PAT, and encryption keys.
- ⚡ **[Cloudflare Worker Webhook Guide](docs/cloudflare_worker_guide.md)** — Zero-cost, sub-second responses and quota elimination for private repos.
- 🛡️ **[Repository Modes Guide](docs/repo_modes_guide.md)** — Public vs. Private repository trade-offs, cron schedules, and migration steps.
- 🏗️ **[System Architecture](docs/architecture.md)** — In-depth architectural design, subsystems, and code layout.
- 📊 **[System Structures & Diagrams](docs/structures.md)** — Centralized visual Mermaid models, sequence diagrams, and state machines.

## Recommended: Instant Replies via Webhooks

By default, RemNewz uses GitHub Actions polling (`commands.yml`) to fetch Telegram updates.
- If your repository is **Public**, polling every 5 minutes is free and reliable.
- If your repository is **Private**, GitHub limits your Actions minutes (2,000/month).

**For instantaneous replies and zero wasted Action minutes**, we highly recommend deploying a Cloudflare Worker as a webhook proxy. It costs $0 and only triggers GitHub when you actually send a message.

For 5-minute step-by-step instructions, see the [Cloudflare Worker Webhook Proxy Guide](docs/cloudflare_worker_guide.md).

## Secret & Key Management

When generating and managing your API keys (Gemini, Groq, OpenRouter, GitHub PAT, Telegram Token) and your generated `ENCRYPTION_KEY`, **never store them in plaintext files** on your computer.
- **Use a Password Manager:** Save your keys as Secure Notes in Bitwarden, 1Password, or Proton Pass.
- **`.env.example`**: We provide an `.env.example` file. If you create a local `.env` file for testing, ensure it is never committed (it is safely in `.gitignore`). **Always delete your local `.env` file before making your code public.**
- **GitHub Secrets:** Your production secrets should live exclusively in **Settings > Secrets and variables > Actions**.

For detailed comparisons on repo modes, see the [Repository Modes Guide](docs/repo_modes_guide.md).
