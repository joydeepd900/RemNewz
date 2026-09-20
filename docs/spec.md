# Product Specification (PRD) — RemNewz: Personal AI Intelligence & Reminders Suite

**Product:** RemNewz  
**Status:** Phase 6 Complete (Unified Encrypted SQLite Migration & Advanced Task Intelligence)  
**Distribution Model:** Open-Source GitHub Template Repository (Self-Hostable at $0 Cost)  
**Related Docs:** [Architecture](./architecture.md) · [Contributing Guidelines](../CONTRIBUTING.md) · [Roadmap (Phases)](./roadmap.md)

---

## 1. Problem & Motivation

Staying ahead of rapid open-source innovations, AI developments, and personal deadlines currently requires juggling multiple feed readers, social platforms, and to-do apps. Raw scrapers flood users with overwhelming lists of links without context or synthesis, while traditional reminder bots require paid hosting or persistent servers.

**RemNewz** solves this by providing a serverless, zero-maintenance, $0-cost personal assistant suite that runs entirely on GitHub Actions and interfaces via Telegram. Instead of dumping raw links, RemNewz uses free-tier AI to read, filter, explain, and synthesize what's genuinely important, lets you convert news to actionable tasks with one tap, and manages your personal schedule with natural language understanding.

---

## 2. Core Personas

RemNewz operates as a single Telegram bot presenting three specialized personas to the user:

1. 📰 **Newzy (The Intel & Discovery Scout):**
   - Dispatches daily morning digests at 8:00 AM UTC (`0 8 * * *`).
   - Supports on-demand daily digest execution via `/digest` and instant keyword searches via `/news <topic>`.
   - Reads GitHub trending repositories (with curated star thresholds: >500 past 7d viral new releases, >2000 past 30d active momentum, min 500 stars ranked by recency), RSS feeds (top 10 items), and Hacker News.
   - Synthesizes findings using AI into personalized formats (*"What it is"*, *"Why it matters"*, *"Who should care"*).
   - Equips every digest item with an interactive `[ 📌 Remind Me ]` inline button and feedback controls (`[ 👍 ]`, `[ 👎 ]`).
   - Adapts to user interests dynamically over time.
   - Routes digests into a dedicated `#News` topic in Supergroups when configured.
   - Signs off as *Newzy Digest*.

2. ⏰ **Remzy (The NLP Task & Reminder Specialist):**
   - Understands natural language to-dos via NLP (e.g. `/todo read the vLLM paper by Friday 5pm with high priority`).
   - Handles task lifecycle: creation, listing, completion (`/done`), and archiving.
   - Delivers proactive, non-spammy due alerts and overdue nudges (24-hour snooze gap).
   - Converts news items tapped via Newzy's inline buttons into structured tasks.
   - Remembers the `origin_thread_id` of tasks created inside Supergroup topics, ensuring reminders reply in context if a dedicated `#Tasks` topic is not bound.
   - Signs off as *Remzy*.

3. ⚙️ **Helpzy (The In-Chat Configuration Specialist):**
   - Allows users to customize settings directly within Telegram without editing code or committing files manually.
   - Commands: `/digest`, `/news`, `/todo`, `/list`, `/done`, `/remove`, `/history`, `/search`, `/stats`, `/source`, `/config`, `/help`.
   - In-chat settings: `/config set_tz`, `/config set_style`, `/config set_limit`, `/config repo_mode`, `/config bind_news`, `/config bind_tasks`, `/config clear_topics`, `/source add`, `/source remove`, `/source list`.
   - Persists dynamic overrides to git automatically in the `kv_store` table of `data/remnewz.db.enc`.
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
7. **Privacy in Public Repositories:** Support symmetric encryption-at-rest (`Fernet / AES-128-CBC`) so users who run in public repos (for unlimited free Actions minutes) never expose their personal to-dos or private notes.
8. **Zero Operational Cost ($0):** Run 100% on free tiers (GitHub Actions, Telegram Bot API, free AI provider tiers) with zero server maintenance.

### 3.2 Non-Goals (v1)

- No web dashboard, mobile app, or GUI — Telegram is the single, universal interface.
- No multi-tenant hosted SaaS — each user self-hosts their own instance via GitHub.
- No paid cloud infrastructure or paid LLM tokens required.
- No sub-second real-time responsiveness without webhook proxy.

---

## 4. Functional Requirements

### 4.1 Discovery & Intelligent Synthesis (Newzy)

- **FR1 — Multi-Source Ingestion:** Fetch trending/new GitHub repositories (via GitHub API) with quality star thresholds (>500 past 7d viral new releases, >2000 past 30d active momentum, min 500 threshold with recency ranking) and tech/AI news from configured RSS feeds (top 10 per feed) and Hacker News.
- **FR2 — Pluggable AI Synthesis:** Send candidate items to a configurable AI engine (Google Gemini, OpenRouter, or Groq) with user-selectable model strings (`AI_MODEL`) to extract key innovations, practical takeaways, and relevance.
- **FR3 — Deduplication & Pruning:** Compare candidates against `kv_store` in `data/remnewz.db.enc`. Auto-prune entries older than **30 days** or cap history to **2,000 items** to maintain high performance.
- **FR4 — Daily Scheduled Delivery:** Deliver digests once daily at **8:00 AM UTC** (`0 8 * * *`).
- **FR5 — Interactive Action Buttons & Feedback Loop:** Attach an inline Telegram button (`[ 📌 Remind Me ]`) to each digest item to bridge directly into Remzy, along with `[ 👍 ]` and `[ 👎 ]` buttons to train feed preferences.
- **FR6 — Zero-Key Graceful Fallback:** If no AI API key is configured, fall back to clean, deterministic markdown/HTML link summaries.
- **FR22 — On-Demand Execution & Instant News Search:** Allow users to request an immediate executive digest anytime via `/digest` (marking items seen) or run keyword searches across feeds via `/news <topic>` (without marking items seen).

### 4.2 Conversational Reminders & Tasks (Remzy)

- **FR7 — Natural Language Task Parsing:** Parse commands like `/todo <text> [deadline] [priority]` using AI/NLP to extract task titles, dates, priorities, and tags.
- **FR8 — 1-Tap News-to-Task:** Process Telegram `callback_query` updates from Newzy's inline buttons, instantly filing the news item as a pending task.
- **FR9 — Task Listing & Filtering:** Display active tasks sorted by urgency via `/list`.
- **FR10 — Task Lifecycle & Archiving:** Mark tasks as done (`/done <id>`) or delete them (`/remove <id>`). Automatically move completed items to status `archived` in the `tasks` SQLite table within `data/remnewz.db.enc`.
- **FR11 — Smart Nudge Cadence (Anti-Spam):**
  - Alert once when a task reaches its due window.
  - Send at most one overdue nudge every 24 hours to prevent spamming.
- **FR12 — Completed History:** Allow users to view recently finished tasks via `/history`.
- **FR24 — Advanced Task Search & Analytics:** Support instant keyword search via `/search <query>` across all active and archived tasks. Provide productivity analytics, completion rates, and deadline compliance metrics via `/stats`.

### 4.3 In-Chat Configuration & Operations (Helpzy)

- **FR13 — Setting Inspection:** `/config` outputs current timezone, active topics, RSS feeds, digest times, feed style, and storage encryption status.
- **FR14 — Dynamic Adjustments:** `/config add_topic <tag>`, `/config remove_topic <tag>`, `/config set_tz <IANA_tz>`, `/config set_style <style>`, `/config set_limit <1-15>`, `/config repo_mode`.
- **FR15 — Dynamic Overrides:** Persist chat-configured settings in the `kv_store` table within `data/remnewz.db.enc` which override `config.example.yml` defaults without requiring manual YAML edits.
- **FR23 — Dynamic Source Management:** Manage RSS feeds in chat via `/source add <url> [label]`, `/source remove <id/url>`, and `/source list`.

### 4.4 Security, Platform & Privacy

- **FR16 — Single-User Authorization:** Verify incoming message `chat.id == TELEGRAM_CHAT_ID` or sender in group. Silently ignore any updates from unauthorized users.
- **FR17 — Secret Isolation:** Zero secrets, tokens, or credentials in source code or git history. All credentials injected via GitHub Actions Secrets.
- **FR18 — Dual-Branch Storage & Unified SQLite Engine:**
  - Standardizes the **Unified Encrypted SQLite Engine (`data/remnewz.db.enc`)** backed by Fernet encryption-at-rest (`ENCRYPTION_KEY`). Unifies tasks, settings (stored in the `kv_store` table of the unified `remnewz.db.enc` database), deduplication (30 days / 2,000 items), and update offsets into a single transactional database.
  - **Zero-Leak Guarantee:** Plaintext `.db`, `.sqlite3`, and `.tmp` files are permanently ignored by `.gitignore`. The database is decrypted in-memory/ephemerally during workflow execution and atomically re-encrypted before termination.
  - **Dedicated Data Branch (`data`):** Code and state are strictly separated. The `main` branch contains application code only with zero `.enc` files and permanent `.gitignore` protection, ensuring personal user profiles and contribution graphs stay clean of automated bot commits. State files are mounted at `/data` at runtime via Git Worktrees and pushed exclusively to `origin data`.
  - **Zero-Setup Auto-Provisioning:** When a user creates a new repo from the template, workflows detect the missing `data` branch and auto-provision an orphan `data` storage branch on first run.
  - **Monthly History Squashing:** A scheduled maintenance workflow (`maintenance.yml`, `0 0 1 * *`) periodically squashes accumulated state sync commits on the `data` branch into a single clean snapshot commit.
  - *Public Repo Mode:* Runs `commands.yml` at high frequency (**every 5 minutes**) with unlimited free Actions minutes.
  - *Private Repo Mode:* Runs `commands.yml` at **35-minute intervals** (`0,35 * * * *`) or utilizes Cloudflare Worker webhook proxy.
- **FR19 — Concurrency & Push Resilience:** Use GitHub Actions concurrency groups (`git-state-storage`) and a resilient `git pull --rebase` retry loop targeting `origin data` to eliminate push conflicts.
- **FR20 — Supergroup Topic Routing & Thread Retention:** Support Telegram Forum Supergroups by routing Newzy digests to `topic_news` and Remzy task alerts to `topic_tasks`. For tasks created in unbound topics, preserve `origin_thread_id` to direct deadline alerts back into the context thread.
- **FR21 — Event-Driven Webhook Dispatch Option:** Support optional zero-polling instant execution via Cloudflare Worker webhook proxy, passing payloads via `repository_dispatch` (`TELEGRAM_UPDATE_PAYLOAD`).

---

## 5. Success Criteria

1. **Information Quality:** The daily digest and on-demand news search deliver concise, genuinely insightful summaries that save 30+ minutes of manual scrolling every day.
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
  - **Private Repositories:** The GitHub Free plan allocates **2,000 free runner minutes per month**. `commands.yml` is scheduled at **35-minute intervals** (`0,35 * * * *`), running 48 times/day $\approx 1,440$ minutes/month. Combined with twice-daily digests ($\approx 60$ minutes/month), total usage is $\approx 1,500$ minutes/month, safely within quota. Exhausting this quota pauses workflows until the next billing cycle unless a spending limit is configured.
  - **Public Repositories:** GitHub provides **unlimited free runner minutes**. When paired with our universal **Fernet encryption-at-rest**, users can toggle high-frequency polling (**every 5 minutes**) with complete privacy.
  - **Instantaneous Webhook Alternative:** For private repo users desiring sub-second responses without making their repo public, an optional free Cloudflare Workers webhook proxy is documented as an advanced recommendation.
