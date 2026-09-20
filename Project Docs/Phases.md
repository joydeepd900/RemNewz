# Phases — Build & Verification Roadmap

**Related Docs:** [PRD.md](./PRD.md) · [Architecture.md](./Architecture.md) · [Rules.md](./Rules.md)

This roadmap divides the build into modular, verifiable phases. Each phase concludes with explicit manual and automated checkpoints before advancing to the next.

---

## Phase 0 — Foundation & Infrastructure Pipe
**Goal:** Verify communications, secrets, and template scaffolding end to end.

- **Tasks:**
  - Create repository structure, `.gitignore`, `requirements.txt`, and `config.example.yml`.
  - Create `notifier/telegram.py` supporting Telegram HTML parse mode and 4KB message chunking.
  - Create `engine/time_utils.py` for timezone-aware formatting.
  - Set up GitHub Actions Secrets (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, optional `AI_PROVIDER`, `AI_MODEL`, `AI_API_KEY`).
  - Create `digest.yml` with a `workflow_dispatch` manual trigger sending a test message.
- **Verification Milestone:**
  - Manually trigger workflow; receive a clean HTML formatted test message on your phone.

---

## Phase 1 — Newzy: Explanatory News & Multi-Provider Digest
**Goal:** Deliver the twice-daily AI-synthesized intelligence digest with adaptive feedback.

- **Tasks:**
  - Implement `fetchers/github_repos.py` with `GITHUB_TOKEN` authentication.
  - Implement `fetchers/rss_hn.py` for RSS feeds and Hacker News.
  - Implement `data/seen.json` dedup with retention pruning (**14 days** or max **1,000 items**).
  - Implement `engine/ai_client.py` with dynamic multi-provider support: Google Gemini, OpenRouter, and Groq (with configurable `AI_MODEL`).
  - Add deterministic fallback if no AI API key is configured.
  - Format digest with interactive Telegram inline buttons: `[ 📌 Remind Me ]`, `[ 👍 ]`, `[ 👎 ]`.
  - Configure `digest.yml` cron for **8:00 AM & 8:00 PM** local time.
  - Add unit tests (`tests/test_fetchers.py`) to verify dedup, provider routing, and fallback formatting locally.
- **Verification Milestone:**
  - Receive an explanatory morning/evening digest on Telegram with working inline buttons. Verify re-running does not produce duplicate items.

---

## Phase 2 — Remzy: Data Model & Anti-Spam Due Checker
**Goal:** Build the task storage engine and proactive notification logic before attaching live chat inputs.

- **Tasks:**
  - Define schema for `data/todos.json` (active tasks) and `data/archive_todos.json` (completed tasks, capped at **50 items**).
  - Implement timezone-aware deadline evaluator in `personas/remzy.py`.
  - Implement anti-spam guardrails:
    - Exactly **one** due notification upon becoming due (`reminded_due = true`).
    - At most **one** overdue nudge every 24 hours (`now - last_overdue_nudge >= 24h`).
  - Implement archive logic: moving completed tasks to `archive_todos.json` with `completed_at` timestamps.
  - Add unit tests (`tests/test_reminders.py`) validating timezone transitions, anti-spam suppression, and archive rotation.
- **Verification Milestone:**
  - Populate sample tasks in `todos.json`; execute checker; verify due notification arrives accurately without repeating on successive executions.

---

## Phase 3 — Remzy & Helpzy: Interactive Chatbot & Batched Loop
**Goal:** Control tasks and settings entirely from Telegram via natural language, feedback buttons, and batched execution.

- **Tasks:**
  - Implement Telegram update poller in `main_commands.py` with chat-ID allowlist security.
  - Build `personas/remzy.py` command router:
    - **NLP `/todo` Parser:** Uses AI client structured output to extract title, deadline, and priority from natural text (with regex fallback).
    - **Inline Button Handler:** Captures `callback_query` from Newzy's `[ 📌 Remind Me ]` button and auto-creates a task.
    - **Feedback Handler:** Captures `[ 👍 ]` and `[ 👎 ]` button callbacks and adjusts tag weights in `data/settings.json`.
    - **Commands:** `/list`, `/done <id>`, `/remove <id>`, `/history`.
  - Build `personas/helpzy.py` settings dispatcher:
    - Commands: `/config`, `/config add_topic`, `/config remove_topic`, `/config set_tz`, `/config set_style`, `/help`.
    - Persist overrides to `data/settings.json`.
  - Create `commands.yml` workflow running on a **2-3 minute schedule** (`*/2 * * * *`) as the repo is public.
  - Add GitHub Actions `concurrency: git-state-storage` and `git pull --rebase` retry loop ensuring all actions during the window produce **at most one consolidated commit**.
- **Verification Milestone:**
  - Tap `[ 📌 Remind Me ]` on a news item $\to$ confirm it appears in `/list`.
  - Send `/todo read paper tomorrow 5pm` $\to$ confirm Remzy parses deadline correctly.
  - Mark `/done` $\to$ confirm item moves to `/history`.
  - Adjust a setting with Helpzy $\to$ confirm `data/settings.json` is committed cleanly in a single batched commit.

---

## Phase 4 — Privacy, Encryption & Open-Source Template Polish
**Goal:** Protect public and private repositories with universal encryption and prepare the project for public distribution.

- **Tasks:**
  - Implement `engine/crypto.py` with AES-256 (Fernet) encryption at rest.
  - Set up `ENCRYPTION_KEY` in GitHub Secrets to enable symmetric Fernet encryption (AES-128-CBC) for all task storage.enc` and `archive_todos.enc` before git commit; decrypt in runner memory. Standardize across both public and private repos.
  - Validate that zero plaintext tasks appear in git history.
  - Polish `config.example.yml` with helpful commentary and cadence mode toggle (`public` vs `private`).
  - Write comprehensive, beginner-friendly `README.md` covering:
    - "Use this template" 1-click setup.
    - BotFather Telegram setup.
    - GitHub Actions secrets setup (including choosing between Gemini, OpenRouter, or Groq with dynamic `AI_MODEL`).
    - Public vs. Private repository choices and Actions minutes optimization.
    - Optional recommendation: Free Cloudflare Workers webhook proxy for private repo users who want instantaneous sub-second response times.
- **Verification Milestone:**
  - Deploy to a test repository with `ENCRYPTION_KEY`; verify git commit history contains only encrypted ciphertext.

---

## Phase 5 — Telegram Supergroups & Webhook Architecture (Completed)

**Goal:** Enable seamless Telegram Forum Supergroup topic routing and zero-polling webhook execution.

- **Tasks:**
  - Add `message_thread_id` and `resolve_topic_id` routing to `notifier/telegram.py`.
  - Update `main_digest.py` to dispatch digests to `topic_news` when bound.
  - Update `personas/remzy.py` to store `origin_thread_id` on tasks and route due alerts to `topic_tasks` (or origin thread fallback).
  - Update `personas/helpzy.py` with topic commands (`/config bind_news`, `/config bind_tasks`, `/config set_topic_news <id>`, `/config set_topic_tasks <id>`, `/config clear_topics`).
  - Implement Cloudflare Worker webhook proxy ingestion in `main_commands.py` and `.github/workflows/commands.yml` (`TELEGRAM_UPDATE_PAYLOAD`).
  - Add unit test suite `tests/test_supergroups.py` validating topic routing, settings persistence, and origin thread fallback.
- **Verification Milestone:**
  - Verified topic routing and origin fallback in automated tests (`pytest tests/test_supergroups.py`).
  - Verified command loop processes single update payloads from webhook dispatches.

---

## Phase 6 — Intelligence, Security & Operational Overhauls (Completed)

**Goal:** Advanced source management, fail-secure crypto hardening, curated digest filtering, and on-demand news delivery.

- **Phase 6.1 — Dynamic Sources & Settings Management:**
  - Added in-chat `/source` (`add`, `remove`, `list`) to dynamically manage RSS and Atom feeds without file edits.
  - Added `/config set_limit [1-15]` to dynamically customize news items per digest.
  - Added `/config repo_mode` with dynamic GitHub edit links for workflow files.
  - Extended deduplication window to 30 days / 2,000 items in `data/remnewz.db.enc`.
- **Phase 6.2 — Encryption Securities Deep-Check:**
  - Hardened cryptographic subsystem with fail-secure `CryptoManager` (`AES-128-CBC` with `SHA256 HMAC`).
  - Added universal encryption across all metadata files (`settings.enc`, `seen.enc`, `last_update_id.enc`).
  - Implemented `_atomic_write_file` using temporary files, buffer flushing, and `os.replace` to prevent database corruption.
  - Masked webhook payloads in GitHub Actions runner logs (`::add-mask::`).
  - Added `.gitignore` shielding for `data/*.json` and `data/*.tmp`.
- **Phase 6.3 — Newzy Digest Overhaul & On-Demand Briefings:**
  - Standardized daily automated digest delivery to **8:00 AM UTC** (`0 8 * * *`).
  - Implemented on-demand daily digest via `/digest` (marking items seen).
  - Implemented instant news and topic search via `/news [query]` (without marking items seen).
  - Upgraded GitHub trending filters with high-impact star thresholds (>500 past 7 days viral new releases, >2000 past 30 days active momentum, min 500 threshold with recency ranking).
  - Expanded RSS ingestion to top 10 articles per feed.
  - Added AI canonical topic slug normalization for clean GitHub topic queries.
  - Added dynamic command registration (`scripts/register_commands.py`) synchronizing commands across all 4 Telegram scopes.

---

## Phase 7 — Future Stretch Expansions

**Goal:** Advanced ecosystem and intelligence enhancements.

- **Ideas:**
  - Additional ingestion sources: ArXiv AI papers, Reddit (`r/LocalLLaMA`, `r/MachineLearning`), Product Hunt.
  - Weekly executive review digest delivered on Sunday mornings summarizing major trends.
  - SQLite backend migration if active task count exceeds hundreds of items.
  - User-level authorization for shared Supergroup moderation.
