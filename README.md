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

There are two ways to set up RemNewz: the **Automated Setup (Recommended)**, which handles everything for you in minutes, or the **Manual Setup**.

### Option A: Automated Setup (Recommended)
The easiest way to set up RemNewz is to use our automated wizard inside a free GitHub Codespace. This method requires zero local installations and automatically configures your Telegram Bot, GitHub Secrets, and a free Cloudflare Webhook proxy for instant replies.

1. **Create Repository:** Click **Use this template** at the top of this repository and name your new repo.
2. **Open Codespace:** In your new repository, click the **`<> Code`** button, select the **Codespaces** tab, and click **Create codespace on main**.
3. **Run Wizard:** Once the browser terminal loads, simply run:
   ```bash
   python setup.py
   ```
4. Follow the interactive prompts to paste your API keys. The wizard will securely provision your GitHub Secrets, deploy the Cloudflare Worker, and link your Telegram webhook automatically.

---

### Option B: Manual Setup (If automated setup fails)

If you prefer to configure everything manually or if the setup script encounters issues, follow these steps:

#### 1. Create Your Repository
1. Click the **Use this template** button at the top of this repository.
2. Name your repository. You can choose **Public** or **Private**:
   - **Public:** GitHub Actions minutes are unlimited and free. The Telegram chat poller can run every 5 minutes continuously. Your personal data is safely encrypted.
   - **Private:** GitHub Actions minutes are capped (typically 2,000/month). A 5-minute poller will exhaust your quota. You will need to change the cron schedule in `.github/workflows/commands.yml` to `*/30 * * * *` or utilize a Webhook.

#### 2. Configure the Telegram Bot
1. Open Telegram and message [@BotFather](https://t.me/BotFather).
2. Send `/newbot`, choose a name, and copy the **HTTP API Token**.
3. Send a message to your new bot to initialize the chat.
4. Visit `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` in your web browser. Locate the `"chat": {"id": 123456789}` field and copy your chat ID.

#### 3. Generate an Encryption Key (Recommended)
Run this Python snippet locally to generate a secure Fernet key:

```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode('utf-8'))
```

#### 4. Configure GitHub Secrets
Navigate to your repository **Settings > Secrets and variables > Actions** and add the following **Repository Secrets**:

- `TELEGRAM_BOT_TOKEN`: The token provided by BotFather.
- `TELEGRAM_CHAT_ID`: Your personal chat ID.
- `AI_PROVIDER`: Choose `gemini`, `openrouter`, or `groq`.
- `AI_MODEL`: The specific model string (e.g., `gemini-2.0-flash`, `llama-3.3-70b-versatile`).
- `ENCRYPTION_KEY`: The Fernet key generated in the previous step.
- `GEMINI_API_KEY`, `GROQ_API_KEY`, or `OPENROUTER_API_KEY`: Depending on your chosen AI provider.

#### 5. Start the Bot
1. Navigate to the **Actions** tab in your repository.
2. Accept the prompt to enable workflows.
3. Click on **Register Bot Commands**, then select **Run workflow**. This automatically pushes the bot's `/` command autocomplete menu across all Telegram scopes.
4. Click on **Commands Poller**, then select **Run workflow**.
5. Go to Telegram and type `/help`. RemNewz is now active and ready to assist.

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

For visual system architecture, sequence diagrams, and flowcharts, see [System Structures & Diagrams](docs/structures.md).

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
