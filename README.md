# RemNewz 📰🤖

An autonomous, serverless Telegram bot that acts as your personal AI News Anchor and Task Master, running entirely on free GitHub Actions.

RemNewz fetches top posts from HackerNews and trending GitHub repositories based on your interests, uses an AI (Gemini, OpenRouter, or Groq) to synthesize them into punchy summaries, and delivers them directly to your Telegram. 

It also functions as a full NLP Task Manager. Simply chat with it (`/todo Remind me to review the architecture doc tomorrow at 5pm`), and it will parse your deadline, store it securely using AES-256 encryption, and ping you when it's due.

## Features
- **Serverless News Digest:** Runs on a scheduled GitHub Actions cron.
- **Multi-Provider AI Synthesis:** Pluggable support for Gemini, Groq, or OpenRouter (with fallback).
- **NLP Task Management:** Remzy, your personal assistant, understands natural language deadlines.
- **Anti-Spam Due Checker:** Intelligently reminds you without spamming your inbox.
- **Privacy First (Encryption at Rest):** Automatically encrypts your tasks and settings into `.enc` files before pushing to GitHub, allowing you to use a free Public Repository without leaking personal data.

## 🚀 1-Click Setup Guide

### 1. Create Your Repository
1. Click the **"Use this template"** button at the top of this repository.
2. Name your repo. You can choose **Public** or **Private**:
   - **Public:** GitHub Actions minutes are *unlimited and free*. The Telegram chat poller can run every 5 minutes forever. (Your tasks will be safely encrypted).
   - **Private:** GitHub Actions minutes are capped (usually 2,000/month). A 5-minute poller will exhaust your quota. You will need to change the cron schedule in `.github/workflows/commands.yml` to `*/30 * * * *` or use a Webhook.

### 2. Setup Telegram Bot
1. Open Telegram and message [@BotFather](https://t.me/BotFather).
2. Send `/newbot`, choose a name, and copy the **HTTP API Token**.
3. Send a message to your new bot (e.g., "Hello").
4. Visit `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` in your browser. Look for `"chat": {"id": 123456789}`. Copy that chat ID.

### 3. Generate Encryption Key (Optional but highly recommended)
Run this short python snippet locally to generate a secure AES-256 key:
```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode('utf-8'))
```

### 4. Configure GitHub Secrets
Go to your repository **Settings > Secrets and variables > Actions** and add the following **Repository Secrets**:
- `TELEGRAM_BOT_TOKEN`: The token from BotFather.
- `TELEGRAM_CHAT_ID`: Your personal chat ID.
- `AI_PROVIDER`: Choose `gemini`, `openrouter`, or `groq`.
- `AI_MODEL`: The model string (e.g., `gemini-1.5-flash`, `llama3-8b-8192`).
- `ENCRYPTION_KEY`: The Fernet key generated in step 3.
- `GEMINI_API_KEY`, `GROQ_API_KEY`, or `OPENROUTER_API_KEY`: Depending on your chosen provider.

### 5. Start the Bot!
- Go to the **Actions** tab in your repository.
- You will see a prompt that says "I understand my workflows, go ahead and enable them." Click it.
- Click on **Commands Poller**, then **Run workflow**. 
- Go to Telegram and type `/help`. RemNewz is now alive!

## Commands
- `/todo <description>` - Create an NLP task.
- `/list` - View active tasks.
- `/done <id>` - Mark a task complete.
- `/config` - View and manage dynamic settings (topics, timezone, style).

## Advanced: Private Repos & Webhooks
If you are running a Private repo and want instantaneous chat replies without burning your Action minutes, disable `commands.yml` and deploy a Cloudflare Worker to act as a webhook proxy that triggers a lightweight GitHub repository_dispatch event only when you send a message.
