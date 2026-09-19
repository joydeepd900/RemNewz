# RemNewz User Guide & Persona Command Reference

Welcome to RemNewz. This guide details how to interact with your personal AI assistant suite on Telegram, explaining each persona's role, supported commands, real-world examples, and Supergroup topic configuration.

---

## Table of Contents

1. [Introduction to the Personas](#1-introduction-to-the-personas)
2. [Remzy: Task Management & Reminders](#2-remzy-task-management--reminders)
   - [Natural Language Task Creation](#natural-language-task-creation-todo)
   - [View Active Tasks](#view-active-tasks-list)
   - [Complete & Archive Tasks](#complete--archive-tasks-done)
   - [Delete Tasks](#delete-tasks-remove)
   - [View Completed Tasks](#view-completed-tasks-history)
   - [Interactive Button: Remind Me](#interactive-button-remind-me)
   - [Deadline Alerts & Anti-Spam Nudges](#deadline-alerts--anti-spam-nudges)
3. [Helpzy: In-Chat Settings & Configuration](#3-helpzy-in-chat-settings--configuration)
   - [Command Overview](#command-overview-help)
   - [On-Demand Daily Digest](#on-demand-daily-digest-digest)
   - [Instant News & Keyword Search](#instant-news--keyword-search-news)
   - [Inspect Current Configuration](#inspect-current-configuration-config)
   - [Manage News Sources & RSS Feeds](#manage-news-sources--rss-feeds-source)
   - [Configure Digest Item Limit](#configure-digest-item-limit-config-set_limit)
   - [Configure Timezone](#configure-timezone-config-set_tz)
   - [Configure Digest Synthesis Style](#configure-digest-synthesis-style-config-set_style)
   - [Manage Interests](#manage-interests-config-add_topic--remove_topic)
   - [Repository Mode & Polling Schedule](#repository-mode--polling-schedule-config-repo_mode)
4. [Newzy: News Synthesis & Adaptive Feedback](#4-newzy-news-synthesis--adaptive-feedback)
   - [Delivery Schedule & Sources](#delivery-schedule--sources)
   - [Quality Thresholds & Curation](#quality-thresholds--curation)
   - [Interactive Feedback](#interactive-feedback)
5. [Telegram Supergroups & Forum Topic Routing (Optional)](#5-telegram-supergroups--forum-topic-routing-optional)
   - [Default Chat vs. Supergroups with Topics](#default-chat-vs-supergroups-with-topics)
   - [Step-by-Step Supergroup Setup Guide](#step-by-step-supergroup-setup-guide)
   - [What Happens in Regular Chats or Without Topics?](#what-happens-in-regular-chats-or-without-topics)
   - [Origin Thread Fallback Behavior](#origin-thread-fallback-behavior)
   - [Clearing Topic Bindings](#clearing-topic-bindings)
6. [Operational Cadence: Public vs. Private Repositories](#6-operational-cadence-public-vs-private-repositories)
7. [Security & Access Control](#7-security--access-control)
8. [Frequently Asked Questions (FAQ)](#8-frequently-asked-questions-faq)

---

## 1. Introduction to the Personas

RemNewz operates as a single Telegram bot presenting three specialized personas:

- **Newzy (The News & Intelligence Scout):** Dispatches daily morning digests (08:00 UTC) and on-demand news syntheses summarizing high-impact trending open-source projects, Hacker News technical discussions, and RSS articles using your configured AI provider.
- **Remzy (The NLP Task Master):** Converts natural language into structured to-dos, manages your task lifecycle, and delivers non-spam deadline alerts (with a 24-hour snooze gap).
- **Helpzy (The Configuration Specialist):** Allows you to manage settings, timezone, content preferences, instant news triggers, and Supergroup topic routing directly within Telegram.

---

## 2. Remzy: Task Management & Reminders

Remzy processes all task management commands and intelligently evaluates deadlines.

### Natural Language Task Creation (`/todo`)

Create a task using plain English. Remzy parses the task description, deadline, and priority using your configured AI model (with regex fallback).

**Syntax:**

```text
/todo <description> [due date/time] [priority]
```

**Examples:**

- **Relative Deadlines:**

  ```text
  /todo Review pull request tomorrow at 5pm
  ```

  *Result:* Creates a task titled "Review pull request" due tomorrow at 17:00 in your configured local timezone.

- **Specific Days & Times:**

  ```text
  /todo Send weekly report on Friday at 3:30pm
  ```

  *Result:* Schedules deadline for the upcoming Friday at 15:30.

- **Explicit Calendar Dates:**

  ```text
  /todo Renew server certificate by October 25 at 11am high priority
  ```

  *Result:* Parses deadline as October 25 at 11:00 with priority set to "high".

- **Tasks Without Deadlines:**

  ```text
  /todo Buy extra USB-C charging cables
  ```

  *Result:* Creates a task with no deadline, keeping it in your active list until completed.

**What Remzy Returns:**

```text
Task Created: Review pull request
Due: Tomorrow, 5:00 PM
ID: a1b2c3d4
```

---

### View Active Tasks (`/list`)

Displays all pending tasks sorted with their due dates and quick-action commands.

**Syntax:**

```text
/list
```

**Example Output:**

```text
Active Tasks

• Review pull request
  └ Tomorrow, 5:00 PM (/done a1b2c3d4)
• Send weekly report
  └ Friday, 3:30 PM (/done e5f6g7h8)
• Buy extra USB-C charging cables
  └ No deadline (/done k9l0m1n2)
```

---

### Complete & Archive Tasks (`/done`)

Marks a task as completed and archives it with a completion timestamp. The archive retains the last 50 completed tasks.

**Syntax:**

```text
/done <task_id>
```

**Example:**

```text
/done a1b2c3d4
```

**Output:**

```text
Task a1b2c3d4 marked as done and archived.
```

---

### Delete Tasks (`/remove`)

Permanently deletes a task from your active list without moving it to the archive.

**Syntax:**

```text
/remove <task_id>
```

**Example:**

```text
/remove k9l0m1n2
```

**Output:**

```text
Task k9l0m1n2 deleted permanently.
```

---

### View Completed Tasks (`/history`)

Displays the 10 most recently completed tasks from the archive.

**Syntax:**

```text
/history
```

**Example Output:**

```text
Recently Completed (Last 10)

• Review pull request (Sep 17, 4:45 PM)
• Clean up local branches (Sep 16, 8:12 PM)
• Configure Cloudflare Worker (Sep 15, 11:30 AM)
```

---

### Interactive Button: Remind Me

Every news item delivered by Newzy includes an inline `[ 📌 Remind Me ]` button.

- Tapping this button instantly creates a Remzy task titled `"Review News Item"` due in 24 hours.
- A toast notification confirms: `"Task Created!"`.
- The task is immediately tracked in your active `/list`.

---

### Deadline Alerts & Anti-Spam Nudges

Remzy scans deadlines on every execution cycle:

1. **Due Notification:** When `now >= due_at`, Remzy delivers a single alert:

   ```text
   Task Due!

   Review pull request
   Due at: 5:00 PM

   Reply with /done a1b2c3d4 to complete.
   ```

2. **Anti-Spam Overdue Nudges:** If a task remains incomplete, Remzy will not spam on every cycle. It enforces a strict **24-hour snooze gap** between subsequent overdue reminders.

---

## 3. Helpzy: In-Chat Settings & Configuration

Helpzy handles system configuration and news execution triggers. Changes made via Helpzy are saved in `data/settings.enc` (encrypted at rest) and committed automatically to GitHub.

### Command Overview (`/help`)

Displays a concise command reference for all available personas and features.

**Syntax:**

```text
/help
```

---

### On-Demand Daily Digest (`/digest`)

Triggers an immediate executive AI news digest without waiting for the scheduled 8:00 AM UTC cron. This processes your configured topics, RSS feeds, and GitHub trending repositories, synthesizes insights with your AI provider, and delivers them directly into your chat (or `#News` topic in Supergroups). Items delivered via `/digest` are marked as seen to avoid duplicate deliveries.

**Syntax:**

```text
/digest
```

**What Helpzy & Newzy Return:**

1. Initial confirmation: `📰 Preparing your executive digest...`
2. Formatted news syntheses with `[ 📌 Remind Me ]`, `[ 👍 ]`, and `[ 👎 ]` buttons.

---

### Instant News & Keyword Search (`/news`)

Fetches top news and GitHub repositories instantly. If called with a query (e.g., `/news python`, `/news local llm`), RemNewz performs a focused search across GitHub and RSS sources matching your keywords and summarizes the top 3 results. If called without arguments, it delivers a 3-item quick briefing. Items delivered via `/news` are not marked as seen, allowing them to still appear in your scheduled digest if relevant.

**Syntax:**

```text
/news [keyword or topic query]
```

**Examples:**

```text
/news
/news machine learning
/news rust web framework
```

**What Helpzy & Newzy Return:**

1. Initial confirmation: `⚡ Fetching your instant news...`
2. Formatted item summaries matching your search query.

---

### Inspect Current Configuration (`/config`)

Displays your active setting overrides in formatted JSON.

**Syntax:**

```text
/config
```

**Example Output:**

```json
{
  "timezone": "Asia/Kolkata",
  "digest_style": "concise",
  "topics": [
    "artificial-intelligence",
    "developer-tools"
  ],
  "topic_news": 104,
  "topic_tasks": 108
}
```

---

### Configure Timezone (`/config set_tz`)

Configures your local IANA timezone. This controls when twice-daily digests are sent (8:00 AM & 8:00 PM) and aligns natural language task deadlines.

**Syntax:**

```text
/config set_tz <IANA_Timezone>
```

**Examples:**

```text
/config set_tz Asia/Kolkata
/config set_tz America/New_York
/config set_tz Europe/London
/config set_tz UTC
```

---

### Configure Digest Synthesis Style (`/config set_style`)

Adjusts the synthesis prompt used by the AI engine when summarizing news items.

**Syntax:**

```text
/config set_style <style>
```

**Available Styles:**

- `concise` (Default): Brief 2-3 sentence overview covering what it is and why it matters.
- `deep_dive`: Detailed analysis including architecture notes and broader implications.
- `technical`: Emphasizes code details, benchmarks, dependencies, and implementation.
- `bullet_points`: Bullet-point breakdown of key features and takeaways.

**Example:**

```text
/config set_style technical
```

---

### Manage Interests (`/config add_topic` & `/remove_topic`)

Dynamically add or remove keyword tags that guide repository fetching and news filtering.

**Syntax:**

```text
/config add_topic <topic-name>
/config remove_topic <topic-name>
```

**Examples:**

```text
/config add_topic rust
/config add_topic local-llm
/config remove_topic web3
```

---

### Manage News Sources & RSS Feeds (`/source`)

RemNewz allows you to add or remove RSS and Atom feeds dynamically directly from your Telegram chat, without editing configuration files or touching git.

**Commands:**

- `/source` or `/source list` — Displays all active RSS feeds and GitHub topics.
- `/source add <url> [label]` — Adds an RSS or Atom feed. If no label is provided, RemNewz will automatically infer the name from the website domain.
- `/source remove <number or url>` — Removes an active feed by either its list number or matching URL/label.
- *Aliases:* `/config add_source`, `/config remove_source`, `/config sources`.

**Examples:**

```text
/source add https://news.ycombinator.com/rss Hacker News
/source add https://techcrunch.com/feed/
/source remove 1
/source remove https://techcrunch.com/feed/
```

---

### Configure Digest Item Limit (`/config set_limit`)

Control the maximum number of news articles synthesized and delivered in each morning and evening digest (range: 1 to 20 items).

**Syntax:**

```text
/config set_limit <number>
```

**Examples:**

```text
/config set_limit 5
/config set_limit 10
```

---

### Repository Mode & Polling Schedule (`/config repo_mode`)

Explains GitHub Actions free minute quotas for Public vs. Private repositories and provides a dynamic one-click link to open and edit `.github/workflows/commands.yml` directly on GitHub.

**Syntax:**

```text
/config repo_mode
```

For full details on operational trade-offs and switching steps, see the [Repository Modes Guide](repo_modes_guide.md).

---

## 4. Newzy: News Synthesis & Adaptive Feedback

Newzy operates autonomously to discover and synthesize technical news on schedule and on demand.

### Delivery Schedule & Sources

- **Schedule:** Dispatched daily at **8:00 AM UTC** (via `.github/workflows/digest.yml` cron `0 8 * * *`). You can also trigger a full digest anytime via the `/digest` command or perform ad-hoc keyword searches using `/news <topic>`.
- **Sources:**
  - Trending and top-starred GitHub repositories matching your configured topics.
  - Hacker News top technical submissions.
  - Custom RSS feeds defined in `config.example.yml` and dynamically managed via `/source`.
- **AI Processing:** Generates structured insights (*What it is*, *Why it matters*, *Relevance*) using your configured AI provider (Gemini, Groq, or OpenRouter) with deterministic markdown fallback if no AI key is provided.

### Quality Thresholds & Curation

To ensure your digest delivers genuinely impactful software and prevents noise:

- **Past 7 Days:** Repositories created in the last 7 days must have at least **250 stars**.
- **Past 30 Days:** Repositories created in the last 30 days must have at least **1,200 stars**.
- **Fallback Top Repositories:** Active projects in topic areas must have at least **50 stars**.
- **RSS Feeds:** Fetches and processes the top 10 articles per configured RSS source.
- **Deduplication:** Delivered items are recorded in `data/seen.enc` with a 21-day retention window (capped at 1,500 entries) to guarantee you never receive the same news twice.

### Interactive Feedback

Each digest item includes interactive feedback buttons:

- `[ 👍 ]`: Increases the preference weight for this item's topic tags.
- `[ 👎 ]`: Decreases the preference weight for this item's topic tags.

RemNewz records these preferences in `data/settings.enc` (encrypted at rest). Over time, the ranking engine automatically promotes topics you enjoy and suppresses topics you dislike.

---

## 5. Telegram Supergroups & Forum Topic Routing (Optional)

> **Important Note:** You do **not** need a Supergroup to use RemNewz! By default, RemNewz works out of the box in a standard **1-on-1 private chat** with your bot. All digests, tasks, commands, and reminders arrive in your direct message conversation without needing any topic setup.

Telegram Forum Supergroups are an **optional power-user feature** if you want to organize your bot into separate dedicated channels (like Discord or Slack channels)—for example, keeping noisy news digests in a `#News` topic while managing your personal to-dos in a `#Tasks` topic.

### Default Chat vs. Supergroups with Topics

| Feature | Standard 1-on-1 Private Chat (Default) | Telegram Supergroup with Topics (Optional) |
| --- | --- | --- |
| **Setup Required** | **None.** Just message the bot directly. | Create a group, toggle "Topics", add bot as admin. |
| **Digests & Tasks** | Everything arrives in your single DM chat. | News routes to `#News`, task alerts route to `#Tasks`. |
| **Binding Commands** | Not needed. Running `/config bind_news` will say: *"Cannot bind: this is not a topic thread"*. | Run `/config bind_news` or `/config bind_tasks` inside the desired topic. |

---

### Step-by-Step Supergroup Setup Guide

Because Telegram's security model prevents bots from creating groups or forum topics automatically, you set up the Supergroup manually in Telegram once:

1. **Create a New Group:**
   - In Telegram, tap the pencil/compose icon and select **New Group**.
   - Name it whatever you like (e.g., *RemNewz Hub* or *Personal HQ*). You can be the only person in the group.
2. **Enable Topics (Forums):**
   - Open the group's profile $\to$ tap **Edit** (pencil icon).
   - Scroll to **Topics** (or **Forum**) and toggle it **ON**. Telegram will convert the group into a Forum Supergroup.
3. **Add Your Bot as an Admin:**
   - In Group Settings $\to$ **Administrators** $\to$ **Add Admin**.
   - Select your RemNewz bot and grant it permission to *Manage Topics* and *Send Messages*.
4. **Create Your Forum Topics:**
   - Go back into your group and tap **New Topic** (or the `+` button).
   - Create a topic named **News** (or `#News`).
   - Create another topic named **Tasks** (or `#Tasks`).
5. **Bind the Topics to RemNewz:**
   - Open your newly created **News** topic thread and send:

     ```text
     /config bind_news
     ```

     *Response:* `✅ Bound News digests to this topic.`

   - Open your newly created **Tasks** topic thread and send:

     ```text
     /config bind_tasks
     ```

     *Response:* `✅ Bound Task alerts to this topic.`

That's it! Your twice-daily news digests will now post exclusively into `#News`, and your task due alerts will notify you in `#Tasks`.

---

### What Happens in Regular Chats or Without Topics?

If you send `/config bind_news` or `/config bind_tasks` in a standard private chat, a basic group chat without topics, or the General thread:

- The bot detects that there is no `message_thread_id` and replies:

  ```text
  ❌ Cannot bind: this is not a topic thread.
  ```

- All regular commands (`/todo`, `/list`, `/done`, `/config`, etc.) continue to work normally anywhere.

#### Alternative: Explicit Numeric Topic ID Binding

If you already know your topic's numeric `message_thread_id`:

```text
/config set_topic_news 104
/config set_topic_tasks 108
```

---

### Origin Thread Fallback Behavior

If you use a Supergroup with Topics but choose **not** to bind a dedicated `#Tasks` topic:

- When you run `/todo` inside any topic thread, Remzy automatically remembers that thread's ID (`origin_thread_id`).
- When that task becomes due, Remzy sends the due notification directly back into the exact thread where it was created.
- This preserves conversational context without any manual configuration.

---

### Clearing Topic Bindings

To unbind topics and return to standard single-chat behavior:

```text
/config clear_topics
```

---

## 6. Operational Cadence: Public vs. Private Repositories

RemNewz runs serverlessly on GitHub Actions. Depending on your repository visibility:

### Public Repositories (High Frequency Polling)

- **Actions Minutes:** Unlimited and free.
- **Polling Interval:** Runs every 3 to 5 minutes (`*/3 * * * *`).
- **Privacy:** Task data is fully encrypted at rest using Fernet (AES-128-CBC) (`ENCRYPTION_KEY`). Personal notes and to-dos remain private.

### Private Repositories (Quota-Efficient Batching or Webhook)

- **Actions Minutes:** Capped at 2,000 free minutes per month.
- **Option A - Batch Polling:** Runs every 35 minutes (`0,35 * * * *`), consuming approximately 1,440 minutes/month. Messages sent between intervals are queued safely by Telegram.
- **Option B - Instantaneous Webhooks:** Deploy a free Cloudflare Worker that triggers a GitHub `repository_dispatch` event on every incoming message. This provides sub-second replies while consuming runner minutes only when messages arrive.
  - See the [Cloudflare Worker Guide](cloudflare_worker_guide.md) for full setup instructions.

---

## 7. Security & Access Control

- **Allowlist Enforcement:** RemNewz validates incoming messages against `TELEGRAM_CHAT_ID`. Messages from unauthorized direct messages or unrecognized chats are rejected.
- **Supergroups vs. Personal Use:** When deployed in a Telegram Supergroup, all members in that authorized group can issue commands and receive updates (which acts as a shared team workspace for tasks and collective news updates). If you are using the Supergroup feature strictly for personal use, ensure no other members are added to the group (or restrict member permissions). User-level authorization for sensitive commands is planned for future releases.
- **Secret Isolation:** API tokens, chat IDs, and encryption keys are stored exclusively in GitHub Actions Secrets and are never committed to git.
- **Client-Side Encryption:** When `ENCRYPTION_KEY` is set, `todos.json` and `archive_todos.json` are encrypted into `todos.enc` and `archive_todos.enc` before git commits.

---

## 8. Frequently Asked Questions (FAQ)

### Why hasn't the bot replied to my command immediately?

If you are using a Private repository on the default 35-minute polling schedule, Telegram safely queues your message until the next runner cycle starts. If you require immediate responses, you can:

- Trigger **Commands Poller** manually from the **Actions** tab in GitHub, or
- Set up the [Cloudflare Worker Webhook Proxy](cloudflare_worker_guide.md).

### How do I check if my encryption key is active?

Send `/config` to Helpzy. If encrypted mode is active, active storage will show `.enc` formats in your GitHub repository `data/` directory rather than plain `.json`.

### Can other people in my Telegram group use the bot?

If `TELEGRAM_CHAT_ID` is set to a Supergroup ID, any member inside that group can interact with the bot. This allows shared team to-dos and team news feeds. If you intend to use the bot strictly for personal tasks, use a private 1-on-1 chat or do not add other members to your private Supergroup.

### How do I manually trigger a news digest?

There are two ways:

1. **Directly in Telegram (Easiest):** Simply send `/digest` to your bot in any authorized chat or `#News` topic. The bot will immediately reply and synthesize your daily digest.
2. **From GitHub Actions:**
   - Go to your repository's **Actions** tab on GitHub.
   - Select **Newzy Digest** on the left menu.
   - Click **Run workflow** $\to$ **Run workflow**.

### Why aren't command suggestions appearing when I type `/`?

Telegram clients only show the command suggestion popup and menu button after the bot's commands are registered with Telegram API. You have two options to register them:

#### Option 1: Run the Automated GitHub Action (Recommended)

1. Go to your repository's **Actions** tab on GitHub.
2. Select **Register Bot Commands** in the left sidebar.
3. Click **Run workflow** $\to$ **Run workflow**.
4. This runs `scripts/register_commands.py` which pushes the commands across all 4 Telegram scopes (`default`, `all_private_chats`, `all_group_chats`, and `all_chat_administrators`).

#### Option 2: Register via @BotFather

1. Message **@BotFather** on Telegram and send `/setcommands`.
2. Choose your bot.
3. Paste the complete command list:

   ```text
   digest - Get your daily AI news digest now
   news - Instant news & search (e.g. /news python)
   todo - Add a task (e.g. /todo Read docs by 5pm)
   list - View active tasks
   done - Mark task completed (e.g. /done abc1234)
   remove - Delete task permanently
   history - View recently completed tasks
   source - Manage news sources & RSS feeds
   config - Settings, timezones & topic binding
   help - Show command reference & help
   ```

> **Note on Client Caching:** Telegram apps (Desktop, Mobile, Web) cache bot commands locally. After registering commands, completely quit and restart your Telegram app (or open your 1-on-1 private chat with the bot and tap the `Menu` / `[ / ]` button) to force Telegram to refresh its local autocomplete cache.

---

