<div align="center">
  <img src="./assets/remnewz_banner.jpg" alt="RemNewz Logo" width="100%">
</div>

<br/>

An autonomous, serverless Telegram bot that acts as your personal AI News Anchor and Task Master, running entirely on free GitHub Actions.

RemNewz fetches top posts from HackerNews and trending GitHub repositories based on your interests, uses an AI (Gemini, OpenRouter, or Groq) to synthesize them into concise, informative summaries, and delivers them directly to your Telegram. 

It also functions as a full Natural Language Processing (NLP) Task Manager. Simply interact with it via chat (e.g., `/todo Remind me to review the architecture doc tomorrow at 5pm`), and it will parse your deadline, store it securely using Fernet encryption (AES-128-CBC), and notify you when it is due.

## Features

- **Serverless News Digest:** Runs autonomously on a scheduled GitHub Actions cron.
- **Multi-Provider AI Synthesis:** Pluggable support for Gemini, Groq, or OpenRouter (with built-in fallback mechanisms).
- **NLP Task Management:** Includes a personal assistant interface that understands natural language deadlines.
- **Intelligent Due Checker:** Reminds you of pending tasks without overwhelming your inbox.
- **Supergroup Topic Routing:** Natively supports Telegram Forum Supergroups to route news digests and task alerts into dedicated topics.
- **Privacy First (Encryption at Rest):** Automatically encrypts your tasks and settings into `.enc` files before pushing to GitHub. This allows you to securely use a free Public Repository without exposing personal data.

## 1-Click Setup Guide

### 1. Create Your Repository

1. Click the **Use this template** button at the top of this repository.
2. Name your repository. You can choose **Public** or **Private**:
   - **Public:** GitHub Actions minutes are unlimited and free. The Telegram chat poller can run every 5 minutes continuously. Your personal data is safely encrypted.
   - **Private:** GitHub Actions minutes are capped (typically 2,000/month). A 5-minute poller will exhaust your quota. You will need to change the cron schedule in `.github/workflows/commands.yml` to `*/30 * * * *` or utilize a Webhook.

### 2. Configure the Telegram Bot

1. Open Telegram and message [@BotFather](https://t.me/BotFather).
2. Send `/newbot`, choose a name, and copy the **HTTP API Token**.
3. Send a message to your new bot to initialize the chat.
4. Visit `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` in your web browser. Locate the `"chat": {"id": 123456789}` field and copy your chat ID.

### 3. Generate an Encryption Key (Recommended)

Run this Python snippet locally to generate a secure Fernet key:

```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode('utf-8'))
```

### 4. Configure GitHub Secrets

Navigate to your repository **Settings > Secrets and variables > Actions** and add the following **Repository Secrets**:

- `TELEGRAM_BOT_TOKEN`: The token provided by BotFather.
- `TELEGRAM_CHAT_ID`: Your personal chat ID.
- `AI_PROVIDER`: Choose `gemini`, `openrouter`, or `groq`.
- `AI_MODEL`: The specific model string (e.g., `gemini-1.5-flash`, `llama3-8b-8192`).
- `ENCRYPTION_KEY`: The Fernet key generated in the previous step.
- `GEMINI_API_KEY`, `GROQ_API_KEY`, or `OPENROUTER_API_KEY`: Depending on your chosen AI provider.

### 5. Start the Bot

1. Navigate to the **Actions** tab in your repository.
2. Accept the prompt to enable workflows.
3. Click on **Register Bot Commands**, then select **Run workflow**. This automatically pushes the bot's `/` command autocomplete menu to Telegram.
4. Click on **Commands Poller**, then select **Run workflow**.
5. Go to Telegram and type `/help`. RemNewz is now active and ready to assist.

## Commands and User Guide

RemNewz features three built-in personas: **Remzy** (Tasks), **Helpzy** (Configuration), and **Newzy** (News).

- `/todo <description>` - Create an NLP task with parsed deadlines and priorities.
- `/list` - View active tasks.
- `/done <id>` - Mark a task complete and archive it.
- `/remove <id>` - Permanently delete a task.
- `/history` - View recently completed tasks.
- `/config` - View and manage dynamic settings (timezone, style, topics, forum routing).
- `/help` - Display command summary.

For a full reference of commands, natural language examples, and Supergroup topic routing instructions, see the [RemNewz User Guide](docs/user_guide.md).

## Advanced Configuration: Private Repositories & Webhooks

If you are running a Private repository and require instantaneous chat replies without depleting your Action minutes, it is recommended to deploy a Cloudflare Worker. This worker acts as a webhook proxy, triggering a lightweight GitHub `repository_dispatch` event only when a message is received.

For complete, step-by-step setup instructions, see the [Cloudflare Worker Webhook Proxy Guide](docs/cloudflare_worker_guide.md).
