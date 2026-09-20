# RemNewz — System Structures & Architecture Diagrams

This document centralizes the visual architectural models and Mermaid sequence diagrams for **RemNewz**. It illustrates the system topology, end-to-end news ingestion flow, task management lifecycle, Cloudflare webhook sequence, persona decision routing, and storage encryption subsystem.

---

## 1. System Topology & Infrastructure Overview

RemNewz operates as an autonomous, serverless suite running on GitHub Actions with zero dedicated servers. It interacts with the Telegram Bot API for user communication and interfaces with pluggable AI providers for natural language synthesis.

```mermaid
graph TB
    subgraph Telegram["Telegram Ecosystem"]
        USER["User (Mobile / Desktop)"]
        TG_API["Telegram Bot API"]
        USER <-->|"Interactions & Commands"| TG_API
    end

    subgraph Ingress["Ingress Layer (Zero Polling Webhook)"]
        CF_WORKER["Cloudflare Worker Proxy<br/><i>remnewz-telegram-proxy</i>"]
        TG_API -->|"Webhook POST (Secret Token Header)"| CF_WORKER
        CF_WORKER -->|"POST repository_dispatch<br/>('telegram-webhook')"| GH_DISPATCH["GitHub Repository Dispatch"]
    end

    subgraph GitHubActions["GitHub Actions Serverless Runners"]
        subgraph Workflows["Workflows (.github/workflows/)"]
            WF_CMD["commands.yml<br/>• Webhook Dispatch<br/>• 5-min Poller (Public)<br/>• 30-min Poller (Private)"]
            WF_DIGEST["digest.yml<br/>• Scheduled Cron (08:00 UTC)<br/>• Manual workflow_dispatch"]
            WF_REG["register_commands.yml<br/>• Manual workflow_dispatch"]
            WF_MAINT["maintenance.yml<br/>• Monthly Squash Cron (0 0 1 * *)<br/>• Consolidates 'data' to 1 Commit"]
        end

        subgraph CoreApp["Application Runtime (Python 3.11/3.12)"]
            MAIN_CMD["main_commands.py<br/>(Dispatcher & Poller)"]
            MAIN_DIGEST["main_digest.py<br/>(Digest Orchestrator)"]
            REG_SCRIPT["scripts/register_commands.py<br/>(4 Telegram Scopes)"]
            
            WF_CMD --> MAIN_CMD
            WF_DIGEST --> MAIN_DIGEST
            WF_REG --> REG_SCRIPT
        end

        subgraph Personas["Persona Layer"]
            NEWZY["Newzy<br/>(News Scout & Synthesizer)"]
            REMZY["Remzy<br/>(NLP Tasks & Anti-Spam Alerts)"]
            HELPZY["Helpzy<br/>(Settings & Topic Routing)"]
            
            MAIN_CMD --> HELPZY
            MAIN_CMD --> REMZY
            MAIN_CMD --> NEWZY
            MAIN_DIGEST --> NEWZY
        end
    end

    subgraph ExternalServices["External APIs & AI Engine"]
        GH_API["GitHub REST API<br/>(Trending / Top Repos)"]
        RSS_SOURCES["RSS / Atom Feeds & HackerNews"]
        
        AI_ENGINE["Multi-Provider AI Engine<br/>(engine/ai_client.py)"]
        GEMINI["Google Gemini API"]
        GROQ["Groq Cloud API"]
        OPENROUTER["OpenRouter API"]
        
        AI_ENGINE --> GEMINI
        AI_ENGINE --> GROQ
        AI_ENGINE --> OPENROUTER
        
        NEWZY --> GH_API
        NEWZY --> RSS_SOURCES
        NEWZY --> AI_ENGINE
        REMZY --> AI_ENGINE
    end

    subgraph Persistence["Dual-Branch Storage Architecture"]
        CRYPTO["CryptoManager (engine/crypto.py)<br/>AES-128-CBC Fernet Encryption"]
        STORE["Store (engine/store.py)<br/>Atomic Writes (.tmp -> replace)"]
        
        BRANCH_MAIN["Git Branch: 'main'<br/>100% Clean Code • Zero .enc Files<br/>Permanent .gitignore for data/"]
        BRANCH_DATA["Git Branch: 'data' (Worktree Mounted to /data)<br/>• todos.enc<br/>• archive_todos.enc<br/>• settings.enc<br/>• seen.enc<br/>• last_update_id.enc<br/>Auto-Provisioned on First Run • Monthly Squashed"]
        
        WF_MAINT -->|"Squashes to 1 commit"| BRANCH_DATA
        REMZY <--> STORE
        HELPZY <--> STORE
        NEWZY <--> STORE
        STORE <--> CRYPTO
        CRYPTO <--> BRANCH_DATA
    end

    GH_DISPATCH --> WF_CMD
    REG_SCRIPT -->|"setMyCommands"| TG_API
    MAIN_CMD -->|"sendMessage / answerCallbackQuery"| TG_API
    MAIN_DIGEST -->|"sendMessage (HTML Chunks)"| TG_API
```

---

## 2. End-to-End News Ingestion & Synthesis Flow (Newzy)

This diagram illustrates how Newzy discovers, filters, deduplicates, synthesizes, and delivers technical news both on a schedule and on-demand (`/digest`, `/news [query]`).

```mermaid
sequenceDiagram
    autonumber
    participant Triggers as Trigger (Cron 08:00 UTC / /digest / /news)
    participant Orchestrator as main_digest.py
    participant Settings as engine/store.py (settings.enc)
    participant FetcherGH as fetchers/github_repos.py
    participant FetcherRSS as fetchers/rss_hn.py
    participant Dedup as engine/dedup.py (seen.enc)
    participant AI as engine/ai_client.py
    participant Persona as personas/newzy.py
    participant Telegram as notifier/telegram.py

    Triggers->>Orchestrator: Execute run_digest(chat_id, thread_id, max_items, mark_seen, query)
    Orchestrator->>Settings: Load active topics, RSS feeds, limit, and digest_style
    Settings-->>Orchestrator: Return configuration dict

    alt Query Mode (/news <keyword>)
        Orchestrator->>FetcherGH: Search GitHub repos matching query
        Orchestrator->>FetcherRSS: Filter RSS / HN entries matching query
    else Standard Digest Mode (Cron or /digest)
        Orchestrator->>FetcherGH: Fetch repos (>500 stars/7d, >2000 stars/30d, min 500 stars/recency)
        Orchestrator->>FetcherRSS: Fetch top 10 items per feed + HackerNews top stories
    end

    FetcherGH-->>Orchestrator: Return repo items
    FetcherRSS-->>Orchestrator: Return feed items

    Orchestrator->>Dedup: Filter unseen items (against seen.enc)
    Dedup-->>Orchestrator: Unseen candidate pool

    Orchestrator->>Orchestrator: Rank items using feedback weights & cap to limit (default: 5)

    loop For each selected item
        Orchestrator->>Persona: synthesize_item(item, style, provider, model)
        Persona->>AI: generate_text(prompt)
        AI-->>Persona: AI Synthesis ("What it is", "Why it matters", "Key takeaways")
        Persona->>Persona: Format HTML + attach inline buttons ([📌 Remind Me], [👍], [👎])
        Persona-->>Orchestrator: Formatted HTML message & callback data
        Orchestrator->>Telegram: send_message(html_text, reply_markup, thread_id)
        Telegram-->>Orchestrator: Delivery success
    end

    opt mark_seen is True (Automated Digest or /digest)
        Orchestrator->>Dedup: mark_seen(item_urls) & prune_seen(retention=30 days, max=2000)
        Dedup->>Settings: Save updated seen.enc
    end
```

---

## 3. NLP Task Management & Anti-Spam Due Engine (Remzy)

This diagram details Remzy's task parsing pipeline, Fernet encryption at rest, proactive due notification engine, and 24-hour anti-spam snooze protection.

```mermaid
stateDiagram-v2
    [*] --> CommandReceived: User sends /todo or taps [📌 Remind Me]

    state CommandReceived {
        [*] --> ParseInput
        ParseInput --> AI_NLP_Parser: Send natural text to AI Client
        AI_NLP_Parser --> ExtractMetadata: Parse title, due_at (UTC), priority, tags
        AI_NLP_Parser --> RegexFallback: On API Failure / Missing Key
        RegexFallback --> ExtractMetadata: Deterministic date parsing
        ExtractMetadata --> AtomicSave: Store task in data/todos.enc
    }

    CommandReceived --> ActiveTasks: Task Active

    state ActiveTasks {
        [*] --> IdleWaiting
        IdleWaiting --> DeadlineEvaluation: commands.yml poller runs
        
        state DeadlineEvaluation {
            check_due: Is now_utc >= due_at?
            check_reminded: Has reminded_due been sent?
            check_snooze: Is now_utc - last_nudge >= 24 hours?

            [*] --> check_due
            check_due --> check_reminded: Yes
            check_due --> [*]: No (Task not due)

            check_reminded --> SendDueAlert: False (First time due)
            check_reminded --> check_snooze: True (Already alerted)

            SendDueAlert --> MarkReminded: Set reminded_due = True
            check_snooze --> SendOverdueNudge: Yes (>= 24 hours elapsed)
            check_snooze --> [*]: No (< 24 hours elapsed, suppress spam)

            SendOverdueNudge --> UpdateLastNudge: Set last_overdue_nudge = now
        }
    }

    ActiveTasks --> Completed: User sends /done <id>
    
    state Completed {
        [*] --> MoveToArchive: Remove from todos.enc
        MoveToArchive --> CapArchive: Append to archive_todos.enc (Cap at 50)
        CapArchive --> NotifyCompletion: Send "Task Completed & Archived"
    }

    Completed --> [*]
```

---

## 4. Cloudflare Worker Webhook Proxy Flow (Zero-Polling)

This sequence diagram illustrates the zero-polling webhook architecture for instant (<1s) Telegram responses without consuming GitHub Actions cron minutes.

```mermaid
sequenceDiagram
    autonumber
    actor User as User on Telegram
    participant Telegram as Telegram Bot API
    participant CFWorker as Cloudflare Worker (remnewz-telegram-proxy)
    participant GitHubAPI as GitHub REST API (repository_dispatch)
    participant Runner as GitHub Actions Runner (commands.yml)
    participant Bot as main_commands.py

    User->>Telegram: Send command (e.g., /digest, /todo buy milk)
    Telegram->>CFWorker: HTTPS POST update payload (X-Telegram-Bot-Api-Secret-Token)
    
    CFWorker->>CFWorker: Verify secret token matches SECRET_HEADER
    alt Invalid Secret Token
        CFWorker-->>Telegram: 403 Forbidden
    else Valid Token
        CFWorker->>GitHubAPI: POST /repos/{owner}/{repo}/dispatches<br/>{"event_type": "telegram-webhook", "client_payload": {"update": {...}}}
        GitHubAPI-->>CFWorker: 204 No Content
        CFWorker-->>Telegram: 200 OK
    end

    GitHubAPI->>Runner: Trigger commands.yml job (repository_dispatch)
    Runner->>Runner: Mask payload: ::add-mask:: ${{ toJson(event.client_payload.update) }}
    Runner->>Bot: Execute python main_commands.py (with TELEGRAM_UPDATE_PAYLOAD)
    
    Bot->>Bot: Route command to Persona (Helpzy / Remzy / Newzy)
    Bot->>Telegram: Send response message to chat_id / message_thread_id
    Telegram-->>User: Display bot response in Telegram chat
    
    Bot->>Runner: Save updated state files
    Runner->>Runner: Commit & Push: chore(sync): update tasks and settings [skip ci]
```

---

## 5. Persona Decision Matrix & Scope Routing

This diagram models how incoming messages, forum supergroup threads, and Telegram API command scopes are evaluated and routed.

```mermaid
flowchart TD
    START([Incoming Telegram Update]) --> AUTH{Chat ID or From ID<br/>== TELEGRAM_CHAT_ID?}
    AUTH -- No --> DROP([Silently Drop Update])
    AUTH -- Yes --> MSG_TYPE{Update Type?}

    MSG_TYPE -- Callback Query --> CB_ROUTER{Button Action?}
    CB_ROUTER -- remind_me --> CB_REMIND[Remzy: Create 24h Review Task]
    CB_ROUTER -- like_ / dislike_ --> CB_FEEDBACK[Helpzy: Adjust Tag Preferences & Weights]
    CB_REMIND --> ANS_CB[Telegram: answerCallbackQuery]
    CB_FEEDBACK --> ANS_CB

    MSG_TYPE -- Text Message --> CMD_CHECK{Starts with '/'?}
    CMD_CHECK -- No --> IGNORE([Ignore Non-Command Message])
    CMD_CHECK -- Yes --> NORMALIZE[Extract Command Name & Strip @BotMention]

    NORMALIZE --> SCOPE_HELPZY{Helpzy Commands?}
    SCOPE_HELPZY -- "/help" --> H_HELP[Send Command Reference]
    SCOPE_HELPZY -- "/config" --> H_CONFIG[View / Mutate Dynamic Settings]
    SCOPE_HELPZY -- "/source" --> H_SOURCE[List / Add / Remove RSS Feeds]
    SCOPE_HELPZY -- "/digest" --> H_DIGEST[Trigger Immediate Daily Digest]
    SCOPE_HELPZY -- "/news" --> H_NEWS[Fetch Instant News or Keyword Search]

    SCOPE_HELPZY -- Unmatched --> SCOPE_REMZY{Remzy Commands?}
    SCOPE_REMZY -- "/todo" --> R_TODO[Parse NLP Task & Schedule Deadline]
    SCOPE_REMZY -- "/list" --> R_LIST[Display Active Tasks]
    SCOPE_REMZY -- "/done" --> R_DONE[Archive Task to archive_todos.enc]
    SCOPE_REMZY -- "/remove" --> R_REMOVE[Delete Task Permanently]
    SCOPE_REMZY -- "/history" --> R_HIST[Display Last 10 Archived Tasks]

    SCOPE_REMZY -- Unmatched --> UNKNOWN([Ignore Unknown Command])

    H_CONFIG --> TOPIC_ROUTING{Subcommand?}
    TOPIC_ROUTING -- "bind_news" --> BIND_N[Set topic_news = current_thread_id]
    TOPIC_ROUTING -- "bind_tasks" --> BIND_T[Set topic_tasks = current_thread_id]
    TOPIC_ROUTING -- "clear_topics" --> CLEAR_T[Unbind all topic routing]
    TOPIC_ROUTING -- "set_limit" --> LIMIT[Set news_limit = 1-15]
    TOPIC_ROUTING -- "repo_mode" --> REPO_M[Display Public/Private guide & edit link]
    TOPIC_ROUTING -- "add_topic" --> ADD_T[AI Normalizes Canonical Slug & Adds]
```

---

## 6. Storage & Cryptographic Architecture (Fail-Secure)

This diagram details the atomic file-write pattern and Fernet symmetric encryption mechanism safeguarding personal data in public and private repositories.

```mermaid
flowchart TD
    subgraph DatabaseLayer["SQLite Runtime Layer (engine/store.py)"]
        SQLITE_DB[("Local SQLite Database<br/>data/remnewz.db")]
        TASKS_TBL["Table: tasks<br/>(id, status, data, completed_at)"]
        KV_TBL["Table: kv_store<br/>(key, value JSON: settings, seen, cursor)"]
        
        TASKS_TBL --- SQLITE_DB
        KV_TBL --- SQLITE_DB
        
        CLOSE["Pipeline Exit (close_db)<br/>1. Commit & Close Connection<br/>2. Read DB Binary Bytes"]
        SQLITE_DB --> CLOSE
    end

    subgraph CryptoLayer["engine/crypto.py (CryptoManager)"]
        CHK_KEY{ENCRYPTION_KEY<br/>Set & Valid?}
        CHK_KEY -- Invalid Format --> FAIL_SECURE[Raise RuntimeError<br/>Fail Securely & Halt]
        CHK_KEY -- Missing / Empty --> PLAIN_MODE[Plaintext Mode<br/>Retain remnewz.db]
        CHK_KEY -- Valid Fernet Key --> ENC_MODE[encrypt_bytes<br/>AES-128-CBC + HMAC-SHA256]
        
        CLOSE --> CHK_KEY
        ENC_MODE --> CIPHER_BYTES[Encrypted Database Binary]
    end

    subgraph AtomicIO["engine/store.py (_atomic_write_file)"]
        TMP_FILE["Write to Temporary File<br/>(remnewz.db.enc.tmp)"]
        FSYNC["Flush Buffer & os.fsync(fd)<br/>Ensure bytes written to physical disk"]
        OS_REPLACE["Atomic Replace<br/>os.replace(tmp, remnewz.db.enc)"]
        VERIFIED_PURGE["Verified Plaintext Purge<br/>Remove local data/remnewz.db<br/>Zero Leaks"]
        
        CIPHER_BYTES --> TMP_FILE
        TMP_FILE --> FSYNC
        FSYNC --> OS_REPLACE
        OS_REPLACE --> VERIFIED_PURGE
    end

    subgraph DiskStorage["Repository Storage (Dedicated 'data' Branch via Worktree)"]
        OS_REPLACE --> DATA_ENC["Target File: data/remnewz.db.enc<br/>(Single Unified Encrypted Database)"]
        GITIGNORE[".gitignore Shielding<br/>• Blocks *.db, *.sqlite3, *.tmp, /data<br/>• Guarantees zero plaintext database leaks"]
    end
```

---

## 7. Dual-Branch Worktree & Monthly Squash Lifecycle

This diagram demonstrates how GitHub Actions mounts the dedicated `data` branch at runtime via Git Worktrees, commits state exclusively to `origin data`, auto-provisions for new template adopters, and runs monthly squash maintenance.

```mermaid
sequenceDiagram
    autonumber
    participant Runner as GitHub Actions Runner
    participant Main as Git Branch 'main' (Code)
    participant Data as Git Branch 'data' (Encrypted State)
    participant Maint as Maintenance Cron (1st of Month)

    Note over Runner, Main: Routine Bot Run (commands.yml / digest.yml)
    Runner->>Main: Checkout code (fetch-depth: 0)
    alt 'data' branch exists on origin
        Runner->>Data: git fetch origin data:data
        Runner->>Runner: git worktree add data data (mounts branch to /data)
    else First Run (New Template Adopter)
        Runner->>Runner: git worktree add --orphan -b data data
        Runner->>Data: Push initial clean state (auto-provision)
    end

    Note over Runner: Python Pipeline Executes<br/>Reads/writes encrypted files at /data

    opt State Changed
        Runner->>Data: cd data && git add . && git commit -m "chore(sync): update..."
        Runner->>Data: git pull --rebase origin data && git push origin data
    end
    Note over Main: Branch 'main' remains 100% CLEAN<br/>Zero chore commits • Zero user activity clutter

    Note over Maint, Data: Monthly Squash Maintenance (maintenance.yml)
    Maint->>Data: Check commit count
    opt Commit count > 1
        Maint->>Maint: git checkout --orphan temp-data
        Maint->>Maint: git commit -m "chore(maintenance): monthly state consolidation"
        Maint->>Data: git push --force origin data
        Note over Data: Consolidated hundreds of sync commits<br/>into 1 single clean snapshot commit!
    end
```
