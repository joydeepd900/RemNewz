# PRD — RemNewz: Personal AI Intelligence & Reminders Suite

**Product:** RemNewz  
**Status:** Planning & Specification Overhaul (Pre-Phase 0)  
**Distribution Model:** Open-Source GitHub Template Repository (Self-Hostable at $0 Cost)  
**Related Docs:** [Architecture.md](./Architecture.md) · [Rules.md](./Rules.md) · [Phases.md](./Phases.md)

---

## 1. Problem & Motivation

Staying ahead of rapid open-source innovations, AI developments, and personal deadlines currently requires juggling multiple feed readers, social platforms, and to-do apps. Raw scrapers flood users with overwhelming lists of links without context or synthesis, while traditional reminder bots require paid hosting or persistent servers.

**RemNewz** solves this by providing a serverless, zero-maintenance, $0-cost personal assistant suite that runs entirely on GitHub Actions and interfaces via Telegram. Instead of dumping raw links, RemNewz uses free-tier AI to read, filter, explain, and synthesize what's genuinely important, lets you convert news to actionable tasks with one tap, and manages your personal schedule with natural language understanding.

---

## 2. Core Personas

RemNewz operates as a single Telegram bot presenting three specialized personas to the user:

1. 📰 **Newzy (The Intel & Discovery Scout):**
   - Dispatches explanatory morning and evening digests (8:00 AM & 8:00 PM in user's local timezone).
   - Reads GitHub trending repositories, RSS feeds, and Hacker News.
   - Synthesizes findings using AI into personalized formats (*"What it is"*, *"Why it matters"*, *"Who should care"*).
   - Equips every digest item with an interactive `[ 📌 Remind Me ]` inline button and feedback controls (`[ 👍 ]`, `[ 👎 ]`).
   - Adapts to user interests dynamically over time.
   - Signs off as *Newzy Digest*.

2. ⏰ **Remzy (The NLP Task & Reminder Specialist):**
   - Understands natural language to-dos via NLP (e.g. `/todo read the vLLM paper by Friday 5pm with high priority`).
   - Handles task lifecycle: creation, listing, completion (`/done`), and archiving.
   - Delivers proactive, non-spammy due alerts and overdue nudges.
   - Converts news items tapped via Newzy's inline buttons into structured tasks.
   - Signs off as *Remzy*.

3. ⚙️ **Helpzy (The In-Chat Configuration Specialist):**
   - Allows users to customize settings directly within Telegram without editing code or committing files manually.
   - Commands: `/config`, `/config add_topic`, `/config remove_topic`, `/config add_feed`, `/config set_tz`, `/config set_style`, `/help`.
   - Persists dynamic overrides to git automatically.
   - Signs off as *Helpzy*.

---

## 3. Product Goals & Scope

### 3.1 Primary Goals

1. **Explanatory & Intelligent News Synthesis:** Curate, filter, and explain new open-source repos and tech/AI news, delivering actionable insights rather than uninformative link dumps.
2. **Pluggable Multi-Provider AI Architecture:** Users can configure their preferred free-tier AI provider (Google Gemini, OpenRouter, or Groq) with dynamic model selection (`AI_MODEL`), or run in deterministic zero-key fallback mode without hardcoded model constraints.
3. **Adaptive Feed Learning & Personalization:** Learn from user feedback (`[ 👍 ]` / `[ 👎 ]`) and customizable digest styles (`concise`, `deep_dive`, `technical`, `bullet_points`) to tailor future digests.
4. **Seamless News-to-Task Pipeline:** Bridge the gap between reading news and taking action via 1-tap inline buttons and context-aware task creation.
5. **Conversational Task Management:** Natural language task parsing, status tracking, and intelligent reminder cadences that respect user focus.
6. **Self-Hostable GitHub Template:** Any user can fork or instantiate the repository, configure secrets, and have their own private or public instance running in minutes.
7. **Privacy in Public Repositories:** Support optional symmetric encryption-at-rest (`AES-256 / Fernet`) so users who run in public repos (for unlimited free Actions minutes) never expose their personal to-dos or private notes.
8. **Zero Operational Cost ($0):** Run 100% on free tiers (GitHub Actions, Telegram Bot API, free AI provider tiers) with zero server maintenance.

### 3.2 Non-Goals (v1)

- No web dashboard, mobile app, or GUI — Telegram is the single, universal interface.
- No multi-tenant hosted SaaS — each user self-hosts their own instance via GitHub.
- No paid cloud infrastructure or paid LLM tokens required.
- No sub-second real-time responsiveness — operations run asynchronously on scheduled polling intervals.

---

## 4. Functional Requirements

### 4.1 Discovery & Intelligent Synthesis (Newzy)

- **FR1 — Multi-Source Ingestion:** Fetch trending/new GitHub repositories (via GitHub API) and tech/AI news from configured RSS feeds and Hacker News.
- **FR2 — Pluggable AI Synthesis:** Send candidate items to a configurable AI engine (Google Gemini, OpenRouter, or Groq) with user-selectable model strings (`AI_MODEL`) to extract key innovations, practical takeaways, and relevance.
- **FR3 — Deduplication & Pruning:** Compare candidates against `data/seen.json`. Auto-prune entries older than **14 days** or cap history to **1,000 items** to maintain high performance.
- **FR4 — Twice-Daily Scheduled Delivery:** Deliver digests twice daily at **8:00 AM and 8:00 PM** local time (customizable).
- **FR5 — Interactive Action Buttons & Feedback Loop:** Attach an inline Telegram button (`[ 📌 Remind Me ]`) to each digest item to bridge directly into Remzy, along with `[ 👍 ]` and `[ 👎 ]` buttons to train feed preferences.
- **FR6 — Zero-Key Graceful Fallback:** If no AI API key is configured, fall back to clean, deterministic markdown/HTML link summaries.

### 4.2 Conversational Reminders & Tasks (Remzy)

- **FR7 — Natural Language Task Parsing:** Parse commands like `/todo <text> [deadline] [priority]` using AI/NLP to extract task titles, dates, priorities, and tags.
- **FR8 — 1-Tap News-to-Task:** Process Telegram `callback_query` updates from Newzy's inline buttons, instantly filing the news item as a pending task.
- **FR9 — Task Listing & Filtering:** Display active tasks sorted by urgency via `/list`.
- **FR10 — Task Lifecycle & Archiving:** Mark tasks as done (`/done <id>`) or delete them (`/remove <id>`). Automatically move completed items to `data/archive_todos.json` capped at the **last 50 completed tasks**.
- **FR11 — Smart Nudge Cadence (Anti-Spam):**
  - Alert once when a task reaches its due window.
  - Send at most one overdue nudge every 12–24 hours (configurable snooze window) to prevent spamming.
- **FR12 — Completed History:** Allow users to view recently finished tasks via `/history`.

### 4.3 In-Chat Configuration & Operations (Helpzy)

- **FR13 — Setting Inspection:** `/config` outputs current timezone, active topics, RSS feeds, digest times, feed style, and storage encryption status.
- **FR14 — Dynamic Adjustments:** `/config add_topic <tag>`, `/config remove_topic <tag>`, `/config add_feed <url> <name>`, `/config set_tz <IANA_tz>`, `/config set_style <style>`.
- **FR15 — Dynamic Overrides:** Persist chat-configured settings in `data/settings.json` which override `config.example.yml` defaults without requiring manual YAML edits.

### 4.4 Security, Platform & Privacy

- **FR16 — Single-User Authorization:** Verify incoming message `chat.id == TELEGRAM_CHAT_ID`. Silently ignore any updates from unauthorized users.
- **FR17 — Secret Isolation:** Zero secrets, tokens, or credentials in source code or git history. All credentials injected via GitHub Actions Secrets.
- **FR18 — Storage & Repo Mode Toggle:**
  - Phases 0–3 use **plain JSON** (`todos.json`, `archive_todos.json`) for simplicity and debuggability.
  - Phase 4 introduces **optional AES-256 (Fernet) encryption-at-rest** (`todos.enc`, `archive_todos.enc`) via an `ENCRYPTION_KEY` secret, standardized across both public and private repos. Plaintext remains the fallback if the key is omitted.
  - *Public Repo Mode:* Runs `commands.yml` at high frequency (every **3–5 minutes**) with unlimited free Actions minutes.
  - *Private Repo Mode:* Runs `commands.yml` at **35-minute intervals** (`0,35 * * * *`) to stay within the 2,000 monthly free Actions minutes limit.
- **FR19 — Concurrency & Push Resilience:** Use GitHub Actions concurrency groups and a `git pull --rebase` retry loop to prevent push conflicts between workflows.

---

## 5. Success Criteria

1. **Information Quality:** The twice-daily digest delivers concise, genuinely insightful summaries that save 30+ minutes of manual scrolling every day.
2. **Adaptive Personalization:** The digest actively reflects user feedback (`[ 👍 ]` / `[ 👎 ]`), prioritizing topics the user cares about.
3. **Zero Friction Task Capture:** Turning an interesting open-source repo into a weekend research reminder takes exactly one tap on your phone.
4. **No False Reminders or Spam:** Due notifications fire accurately according to your local timezone, without repetitive nagging loops.
5. **Template Portability:** A new user can click **Use this template**, enter their Telegram credentials into GitHub Secrets, and have a fully functioning AI assistant in under 5 minutes.
6. **Zero Maintenance & Cost:** Runs completely unattended on GitHub Actions without runner failures, manual git fixes, or hosting bills.

---

## 6. Constraints & Operating Boundaries

- **Budget:** Exactly **$0.00**. Uses free tiers of GitHub Actions, Telegram Bot API, and free-tier AI providers (Google Gemini, OpenRouter, or Groq with user-specified models).
- **Runners:** Headless Linux GitHub Actions runners (`ubuntu-latest`).
- **Actions Minutes & Schedule Options:**
  - **Private Repositories:** GitHub allocates **2,000 free runner minutes per month**. `commands.yml` is scheduled at **35-minute intervals** (`0,35 * * * *`), running 48 times/day $\approx 1,440$ minutes/month. Combined with twice-daily digests ($\approx 60$ minutes/month), total usage is $\approx 1,500$ minutes/month, safely within quota.
  - **Public Repositories:** GitHub provides **unlimited free runner minutes**. When paired with our universal **AES-256 encryption-at-rest**, users can toggle high-frequency polling (**every 3–5 minutes**) with complete privacy.
  - **Instantaneous Webhook Alternative:** For private repo users desiring sub-second responses without making their repo public, an optional free Cloudflare Workers webhook proxy is documented as an advanced recommendation.
