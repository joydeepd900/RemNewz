# Rules — Boundaries, Conventions & Operating Guardrails

**Related Docs:** [PRD.md](./PRD.md) · [Architecture.md](./Architecture.md) · [Phases.md](./Phases.md)

Read this before writing code or making architectural adjustments. These rules apply equally whether implementation is performed by a human engineer or an AI coding agent.

---

## 1. Security & Secrets (Open-Source Template Hygiene)
- **Zero Secrets in Git:** Never hardcode `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `AI_API_KEY`, or `ENCRYPTION_KEY`. All credentials must be read exclusively from environment variables injected via GitHub Actions Secrets.
- **Log Hygiene:** Never log API keys, bearer tokens, or raw Telegram payloads containing secrets in standard output or error logs.
- **Strict Allowlist:** Always verify `update.message.chat.id == TELEGRAM_CHAT_ID` or `update.callback_query.message.chat.id == TELEGRAM_CHAT_ID` before processing any command. Silently drop updates from any other user or chat.
- **Template Sanitization:** `config.example.yml` must only contain generic, non-identifying sample topics, feeds, and styles. Personal configurations must remain in `data/settings.json` or private `.gitignore` files.
- **Universal Encryption:** Standardize AES-256 Fernet encryption (`.enc`) across both public and private repositories when `ENCRYPTION_KEY` is provided. Plaintext personal tasks must never be committed to git unless the user explicitly leaves encryption disabled.

---

## 2. Workflow Safety & Batching Mechanics
- **Trigger Restrictions:** Both workflows must trigger only via `schedule:` crons and `workflow_dispatch:`. Never add a `push:` trigger to workflows, which would create an infinite commit $\to$ trigger loop.
- **Batched Commits:** In `commands.yml`, all commands and callback actions processed during the batch window (35-min private / 3–5 min public) must be consolidated into **at most one single git commit**. Never commit per-command.
- **Push Concurrency:** Every workflow committing back to the repository must belong to the `concurrency: git-state-storage` group with `cancel-in-progress: false`.
- **Rebase Before Push:** Always execute `git pull --rebase origin main` before `git push`. If there is nothing to commit (`git diff --quiet`), skip the commit entirely to avoid empty log pollution.
- **Idempotency:** Every workflow run must be idempotent. Re-running a workflow with identical input must never produce duplicate Telegram messages or duplicate tasks.

---

## 3. Timezone & Scheduling Integrity
- **No Naive Datetimes:** GitHub Actions runners always operate in `UTC`. Never execute unlocalized `datetime.now()` for user-facing calculations.
- **Timezone Normalization:** All user-entered dates (e.g. "tomorrow 5pm", "Friday at 3") and deadline comparisons must be localized to the user's configured IANA timezone (from `config.example.yml` or `data/settings.json`).
- **Cron Jitter Resilience:** Crons may be delayed by GitHub infrastructure. The due checker must check `due_at <= now` (not `due_at == now`) to ensure delayed runs still trigger pending notifications.

---

## 4. Anti-Spam & Notification Guardrails
- **Single Due Alert:** A task must trigger exactly **one** due notification upon becoming due (`reminded_due = true`).
- **Overdue Nudge Cadence:** If a task remains overdue, subsequent nudges must enforce a minimum **24-hour snooze gap** (`now - last_overdue_nudge >= 24h`). Never nudge on every cron cycle.
- **HTML Parse Mode:** Standardize exclusively on Telegram HTML parse mode (`<b>`, `<i>`, `<a>`, `<code>`). MarkdownV2 is strictly prohibited for external feeds due to fragile character escaping.
- **4KB Chunking:** Any Telegram payload exceeding 4,000 characters must be split at paragraph boundaries to comply with Telegram's 4,096-character API ceiling.

---

## 5. Multi-Provider AI Quota & Fallback Discipline
- **Pluggable Providers & Dynamic Models:** Support Google Gemini, OpenRouter, and Groq. Provider selection is governed by `AI_PROVIDER` (`gemini`, `openrouter`, `groq`), with dynamic model selection via `AI_MODEL`. Never hardcode static model IDs in application code.
- **Free-Tier Protection:** Restrict generation token limits ($< 800$ tokens per synthesis) to minimize latency and avoid hitting free-tier TPM/RPM limits.
- **Graceful Degradation:** If no `AI_API_KEY` is configured or an external provider experiences an outage, the system must immediately fall back to deterministic RSS/README title summaries and regex date parsing. An AI API failure must never crash a workflow run or prevent task creation.

---

## 6. Data Integrity & Retention
- **Atomic File Writes:** When writing JSON or encrypted state, write to a temporary file first and atomically replace the destination file.
- **Retention Ceilings:**
  - `data/seen.json`: Prune entries older than **14 days** or cap at **1,000 entries** on every digest run.
  - `data/archive_todos.json`: Cap completed tasks at the **last 50 items**.
  - `data/settings.json`: Track positive/negative tag weights bounded within $[-10, +10]$ to avoid preference skew.
- **Schema Validation:** Ensure data files are validated before saving. A corrupt payload must never overwrite a valid state file.

---

## 7. Scope & Development Discipline
- **No Heavy Frameworks:** Keep dependencies minimal (`requests`, `feedparser`, `pyyaml`, `python-dateutil`, `cryptography`). Avoid heavy Telegram SDKs or bulky ORMs.
- **Phase Verification:** Complete and verify each phase in [Phases.md](./Phases.md) end to end before advancing.
- **Documented Deviations:** Any architectural adjustment must be documented in [Architecture.md](./Architecture.md) and [PRD.md](./PRD.md) before writing corresponding code.
