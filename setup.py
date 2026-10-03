import os
import sys
import json
import time
import shutil
import subprocess
import secrets
from cryptography.fernet import Fernet

try:
    import requests
    from dotenv import load_dotenv, set_key
except ImportError:
    print("❌ Missing required standard packages. Please run: pip install -r requirements.txt")
    sys.exit(1)

load_dotenv()
GITHUB_API_ACCEPT = "application/vnd.github+json"

def print_header(text):
    print(f"\n{'='*50}\n{text}\n{'='*50}")

def mask_secret(secret):
    if not secret:
        return "(not set)"
    s = str(secret).strip()
    if len(s) <= 8:
        return "********"
    return f"{s[:4]}...{s[-4:]}"

def get_env_or_prompt(key, prompt_text, default=None, is_secret=False):
    val = os.getenv(key)
    if val:
        display_val = mask_secret(val) if is_secret else val
        print(f"✅ Found {key} in .env cache: {display_val}")
        return val
    
    val = input(f"{prompt_text}: ").strip()
    if not val and default:
        val = default
    if not val:
        print("❌ Value cannot be empty.")
        sys.exit(1)
    
    set_key(".env", key, val)
    return val

def run_cmd(cmd, env=None, check=True, interactive=False):
    if interactive:
        result = subprocess.run(cmd, shell=True, env=env)
    else:
        result = subprocess.run(cmd, shell=True, env=env, capture_output=True, text=True)
        
    if check and result.returncode != 0:
        print(f"❌ Command failed: {cmd}")
        if not interactive:
            print(result.stderr)
        sys.exit(1)
    return result

def check_gh_cli():
    return shutil.which("gh") is not None

def check_npx():
    return shutil.which("npx") is not None

def validate_telegram_token(token):
    if not token or not token.strip():
        return False, "Token cannot be empty", None
    try:
        resp = requests.get(f"https://api.telegram.org/bot{token.strip()}/getMe", timeout=10)
        data = resp.json()
        if resp.ok and data.get("ok"):
            username = data["result"].get("username", "UnknownBot")
            return True, f"@{username}", username
        err = data.get("description", f"HTTP {resp.status_code}")
        return False, f"Telegram rejected token: {err}", None
    except Exception as e:
        return False, f"Connection error: {e}", None

def validate_gemini_key(key):
    if not key or not key.strip():
        return False, "Key cannot be empty"
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key.strip()}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return True, "Valid Gemini API Key"
        try:
            data = resp.json()
            err = data.get("error", {}).get("message", f"HTTP {resp.status_code}")
        except Exception:
            err = f"HTTP {resp.status_code}"
        return False, f"Gemini API error: {err}"
    except Exception as e:
        return False, f"Connection error: {e}"

def validate_github_pat(pat):
    if not pat or not pat.strip():
        return False, "PAT cannot be empty", None
    try:
        headers = {
            "Authorization": f"Bearer {pat.strip()}",
            "Accept": GITHUB_API_ACCEPT,
            "User-Agent": "RemNewz-Setup"
        }
        resp = requests.get("https://api.github.com/user", headers=headers, timeout=10)
        if resp.status_code == 200:
            user_data = resp.json()
            username = user_data.get("login", "")
            return True, f"@{username}", username
        elif resp.status_code == 401:
            return False, "Bad credentials or expired PAT", None
        else:
            return False, f"GitHub returned HTTP {resp.status_code}", None
    except Exception as e:
        return False, f"Connection error: {e}", None

def validate_github_repo(pat, owner, repo):
    if not pat or not owner or not repo:
        return False, "Missing credentials or repository name", None
    try:
        headers = {
            "Authorization": f"Bearer {pat.strip()}",
            "Accept": GITHUB_API_ACCEPT,
            "User-Agent": "RemNewz-Setup"
        }
        resp = requests.get(f"https://api.github.com/repos/{owner}/{repo}", headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            is_private = data.get("private", False)
            return True, f"Accessible (Private: {is_private})", is_private
        elif resp.status_code == 404:
            return False, f"Repo '{owner}/{repo}' not found or PAT lacks access", None
        elif resp.status_code == 401:
            return False, "Bad credentials", None
        else:
            return False, f"GitHub HTTP {resp.status_code}", None
    except Exception as e:
        return False, f"Connection error: {e}", None

def prompt_and_validate(key, prompt_text, validator_fn=None, is_secret=False, default=None, force_prompt=False):
    if not force_prompt:
        cached_val = os.getenv(key)
        if cached_val:
            if validator_fn:
                valid, info = validator_fn(cached_val)[:2]
                if valid:
                    display_val = mask_secret(cached_val) if is_secret else cached_val
                    print(f"✅ Found cached {key} ({display_val}): {info}")
                    return cached_val
                else:
                    print(f"⚠️ Cached {key} failed validation: {info}")
            else:
                display_val = mask_secret(cached_val) if is_secret else cached_val
                print(f"✅ Found cached {key}: {display_val}")
                return cached_val

    while True:
        val = input(f"{prompt_text}: ").strip()
        if not val and default:
            val = default
        if not val:
            print("❌ Input cannot be empty. Please try again.")
            continue
            
        if validator_fn:
            print(f"⏳ Verifying {key}...")
            res = validator_fn(val)
            valid, info = res[0], res[1]
            if valid:
                print(f"✅ Verified successfully! ({info})")
                set_key(".env", key, val)
                return val
            else:
                print(f"❌ Verification failed: {info}")
                retry = input("Options: [R]etry, [U]se anyway, [Q]uit [R/u/q]: ").strip().lower()
                if retry in ('u', 'use'):
                    set_key(".env", key, val)
                    return val
                elif retry in ('q', 'quit'):
                    print("Setup aborted.")
                    sys.exit(0)
        else:
            set_key(".env", key, val)
            return val

def get_telegram_chat_id(token, force_prompt=False):
    if not force_prompt:
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if chat_id:
            print(f"✅ Found TELEGRAM_CHAT_ID in .env cache: {chat_id}")
            return chat_id

    print("\nHow would you like to provide your Telegram Chat ID?")
    print("1. Auto-detect (Send '/start' to your bot on Telegram)")
    print("2. Enter Chat ID manually")
    choice = input("Select [1/2] (Default: 1): ").strip()
    
    if choice == '2':
        while True:
            chat_id = input("Enter your Telegram Chat ID: ").strip()
            if chat_id:
                set_key(".env", "TELEGRAM_CHAT_ID", chat_id)
                return chat_id
            print("❌ Chat ID cannot be empty.")

    print("\n⏳ Listening for messages from your Telegram Bot...")
    print("👉 IMPORTANT: Open Telegram, search for your bot, and send '/start' to it right now!")
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    
    for attempt in range(1, 13):
        try:
            resp = requests.get(url, timeout=10)
            if resp.ok:
                data = resp.json()
                if data.get("result"):
                    chat_id = str(data["result"][-1]["message"]["chat"]["id"])
                    set_key(".env", "TELEGRAM_CHAT_ID", chat_id)
                    print(f"✅ Extracted Chat ID: {chat_id}")
                    return chat_id
        except Exception:
            pass
        time.sleep(5)
        print(f"Waiting for message... ({attempt * 5}/60s)")
    
    print("⚠️ Could not detect a message within 60 seconds.")
    while True:
        chat_id = input("Please manually enter your Telegram Chat ID: ").strip()
        if chat_id:
            set_key(".env", "TELEGRAM_CHAT_ID", chat_id)
            return chat_id
        print("❌ Chat ID cannot be empty.")

def provision_github_secrets(secrets_dict):
    print_header("Provisioning GitHub Secrets")
    
    if check_gh_cli():
        print("✅ GitHub CLI (gh) detected. Provisioning secrets...")
        for key, value in secrets_dict.items():
            run_cmd(f"gh secret set {key} --body \"{value}\"")
            print(f"✅ Set GitHub Secret: {key}")
    else:
        print("⚠️ GitHub CLI (gh) not found. Falling back to manual REST API.")
        github_pat = get_env_or_prompt("GITHUB_PAT", "Enter your GitHub PAT (repo scope)")
        github_repo = get_env_or_prompt("GITHUB_REPO", "Enter your GitHub Repo (e.g. username/RemNewz)")
        
        try:
            from base64 import b64encode
            from nacl import encoding, public
        except ImportError:
            print("❌ PyNaCl is required for GitHub REST API encryption. Run: pip install pynacl")
            print("   (Or install GitHub CLI: https://cli.github.com)")
            sys.exit(1)
            
        # Get public key
        headers = {
            "Authorization": f"Bearer {github_pat}",
            "Accept": GITHUB_API_ACCEPT,
            "X-GitHub-Api-Version": "2022-11-28"
        }
        resp = requests.get(f"https://api.github.com/repos/{github_repo}/actions/secrets/public-key", headers=headers)
        if not resp.ok:
            print("❌ Failed to fetch GitHub public key. Check your PAT and repo name.")
            sys.exit(1)
        
        key_data = resp.json()
        public_key = public.PublicKey(key_data["key"].encode("utf-8"), encoding.Base64Encoder())
        
        for key, value in secrets_dict.items():
            sealed_box = public.SealedBox(public_key)
            encrypted = sealed_box.encrypt(value.encode("utf-8"))
            encrypted_b64 = b64encode(encrypted).decode("utf-8")
            
            payload = {
                "encrypted_value": encrypted_b64,
                "key_id": key_data["key_id"]
            }
            put_resp = requests.put(f"https://api.github.com/repos/{github_repo}/actions/secrets/{key}", headers=headers, json=payload)
            if put_resp.status_code in [201, 204]:
                print(f"✅ Set GitHub Secret: {key}")
            else:
                print(f"❌ Failed to set secret {key}: {put_resp.text}")

def deploy_cloudflare_worker(env_vars):
    print_header("Deploying Cloudflare Worker")
    
    if check_npx():
        print("✅ Node/npx detected. Deploying via Wrangler...")
        # Check login status
        print("Checking Wrangler authentication...")
        run_cmd("npx wrangler whoami", check=False, interactive=True) # May trigger login if not authenticated
        
        print("Deploying Worker proxy...")
        run_cmd("npx wrangler deploy scripts/cf_worker_proxy.js --name remnewz-proxy", interactive=True)
        
        for key, value in env_vars.items():
            # Wrangler 3.x secret put command
            # Using standard input pipe for the secret value
            subprocess.run(f"npx wrangler secret put {key} --name remnewz-proxy", shell=True, input=value, text=True)
            print(f"✅ Set Worker Secret: {key}")
            
        print("✅ Worker deployed successfully. (Check your Cloudflare Dashboard for the URL)")
        
        worker_url = get_env_or_prompt("CF_WORKER_URL", "Enter the deployed Worker URL (e.g. https://remnewz-proxy.your-subdomain.workers.dev)")
        return worker_url
    else:
        print("⚠️ Node/npx not found. Falling back to Cloudflare REST API.")
        cf_account = get_env_or_prompt("CF_ACCOUNT_ID", "Enter Cloudflare Account ID")
        cf_token = get_env_or_prompt("CF_API_TOKEN", "Enter Cloudflare API Token (Edit Workers permission)")
        
        headers = {"Authorization": f"Bearer {cf_token}"}
        
        # Prepare multipart payload for module worker
        with open("scripts/cf_worker_proxy.js", "r") as f:
            script_content = f.read()
            
        metadata = {
            "main_module": "cf_worker_proxy.js",
            "bindings": [{"name": k, "type": "secret_text", "text": v} for k, v in env_vars.items()]
        }
        
        files = {
            "metadata": (None, json.dumps(metadata), "application/json"),
            "cf_worker_proxy.js": (None, script_content, "application/javascript+module")
        }
        
        print("Deploying worker to Cloudflare API...")
        resp = requests.put(f"https://api.cloudflare.com/client/v4/accounts/{cf_account}/workers/scripts/remnewz-proxy", headers=headers, files=files)
        
        if not resp.ok:
            print(f"❌ Cloudflare deployment failed: {resp.text}")
            sys.exit(1)
            
        print("✅ Worker deployed via API.")
        
        # To get the route, we need to check subdomains. For simplicity:
        worker_url = get_env_or_prompt("CF_WORKER_URL", "Enter the deployed Worker URL (e.g. https://remnewz-proxy.your-subdomain.workers.dev)")
        return worker_url

def setup_webhook(bot_token, worker_url, webhook_secret):
    print_header("Linking Telegram Webhook")
    url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
    resp = requests.post(url, json={
        "url": worker_url,
        "secret_token": webhook_secret,
        "drop_pending_updates": True
    })
    
    if resp.ok and resp.json().get("ok"):
        print(f"✅ Webhook successfully set to {worker_url}")
    else:
        print(f"❌ Failed to set webhook: {resp.text}")

def send_success_message(bot_token, chat_id):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    text = "✅ **RemNewz Setup Complete!**\n\nThe webhook is successfully linked and the backend is configured. You can now use the `/help` command."
    requests.post(url, json={
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    })
    print("✅ Sent success confirmation message to Telegram!")

def main():
    print_header("Welcome to RemNewz Automated Setup")
    print("This wizard will configure your Telegram Bot, GitHub Secrets, and Cloudflare Worker.")
    print("Progress is saved locally. You can safely close and restart this script at any time.\n")
    
    bot_token = prompt_and_validate(
        "TELEGRAM_BOT_TOKEN",
        "Enter your Telegram Bot Token (from @BotFather)",
        validator_fn=validate_telegram_token,
        is_secret=True
    )
    _, _, bot_username = validate_telegram_token(bot_token)
    
    chat_id = get_telegram_chat_id(bot_token)
    
    gemini_key = prompt_and_validate(
        "GEMINI_API_KEY",
        "Enter your Gemini API Key (from Google AI Studio)",
        validator_fn=validate_gemini_key,
        is_secret=True
    )
    
    # Needs GH PAT for the CF worker to trigger repo dispatch and for provisioning secrets
    gh_pat = prompt_and_validate(
        "GITHUB_PAT",
        "Enter your GitHub Personal Access Token (PAT with 'repo' scope)",
        validator_fn=validate_github_pat,
        is_secret=True
    )
    _, _, gh_user = validate_github_pat(gh_pat)
    
    default_owner = gh_user if gh_user else ""
    owner_prompt = f"Enter your GitHub Username [{default_owner}]" if default_owner else "Enter your GitHub Username"
    gh_owner = get_env_or_prompt("GITHUB_OWNER", owner_prompt, default=default_owner)
    gh_repo = get_env_or_prompt("GITHUB_REPO", "Enter the Repository Name [RemNewz]", default="RemNewz")
    
    # Validate repository access with PAT
    val_ok, val_res, is_priv = validate_github_repo(gh_pat, gh_owner, gh_repo)
    default_vis = '1'
    if val_ok:
        print(f"✅ Verified GitHub repository access: {gh_owner}/{gh_repo}")
        if is_priv is True:
            default_vis = '2'
            print("ℹ️ Detected Private repository.")
        elif is_priv is False:
            default_vis = '1'
            print("ℹ️ Detected Public repository.")
    else:
        print(f"⚠️ Repo access warning: {val_res}")
        
    cached_vis = os.getenv("REPO_VISIBILITY")
    if cached_vis in ('1', '2'):
        repo_visibility = cached_vis
        print(f"✅ Found REPO_VISIBILITY in .env cache: {'Public' if repo_visibility == '1' else 'Private'}")
    else:
        vis_prompt = f"Is your repo Public (1) or Private (2)? [Default: {default_vis}]"
        repo_visibility = input(f"{vis_prompt}: ").strip() or default_vis
        if repo_visibility not in ('1', '2'):
            repo_visibility = default_vis
        set_key(".env", "REPO_VISIBILITY", repo_visibility)
    
    while True:
        bot_mask = mask_secret(bot_token)
        bot_info = f" (@{bot_username})" if bot_username else ""
        gemini_mask = mask_secret(gemini_key)
        gh_pat_mask = mask_secret(gh_pat)
        gh_info = f" (@{gh_user})" if gh_user else ""
        vis_str = "Public (cron: every 5m)" if repo_visibility == '1' else "Private (cron: every 30m)"

        print_header("Review & Verify Your Configuration")
        print(f"1. Telegram Bot Token : {bot_mask}{bot_info}")
        print(f"2. Telegram Chat ID   : {chat_id}")
        print(f"3. Gemini API Key     : {gemini_mask} (Verified)")
        print(f"4. GitHub PAT         : {gh_pat_mask}{gh_info}")
        print(f"5. GitHub Repository  : {gh_owner}/{gh_repo}")
        print(f"6. Repo Visibility    : {vis_str}")
        print("-" * 50)
        print("Note: Secret tokens are masked for your security.")
        
        choice = input("\nProceed with deployment? [Y to proceed, 1-6 to edit/change, Q to quit]: ").strip().lower()
        if choice in ('y', 'yes', ''):
            break
        elif choice in ('q', 'quit'):
            print("Setup cancelled by user.")
            sys.exit(0)
        elif choice == '1':
            bot_token = prompt_and_validate(
                "TELEGRAM_BOT_TOKEN",
                "Enter new Telegram Bot Token",
                validator_fn=validate_telegram_token,
                is_secret=True,
                force_prompt=True
            )
            _, _, bot_username = validate_telegram_token(bot_token)
            recheck_chat = input("Do you also want to update your Telegram Chat ID for this new bot? [y/N]: ").strip().lower()
            if recheck_chat in ('y', 'yes'):
                chat_id = get_telegram_chat_id(bot_token, force_prompt=True)
        elif choice == '2':
            chat_id = get_telegram_chat_id(bot_token, force_prompt=True)
        elif choice == '3':
            gemini_key = prompt_and_validate(
                "GEMINI_API_KEY",
                "Enter new Gemini API Key",
                validator_fn=validate_gemini_key,
                is_secret=True,
                force_prompt=True
            )
        elif choice == '4':
            gh_pat = prompt_and_validate(
                "GITHUB_PAT",
                "Enter new GitHub PAT (repo scope)",
                validator_fn=validate_github_pat,
                is_secret=True,
                force_prompt=True
            )
            _, _, gh_user = validate_github_pat(gh_pat)
            if gh_user and gh_user != gh_owner:
                update_owner = input(f"Update GitHub Username from '{gh_owner}' to PAT owner '{gh_user}'? [Y/n]: ").strip().lower()
                if update_owner in ('', 'y', 'yes'):
                    gh_owner = gh_user
                    set_key(".env", "GITHUB_OWNER", gh_owner)
        elif choice == '5':
            gh_owner = input(f"Enter GitHub Username [current: {gh_owner}]: ").strip() or gh_owner
            gh_repo = input(f"Enter Repository Name [current: {gh_repo}]: ").strip() or gh_repo
            set_key(".env", "GITHUB_OWNER", gh_owner)
            set_key(".env", "GITHUB_REPO", gh_repo)
            val_ok, val_res, is_priv = validate_github_repo(gh_pat, gh_owner, gh_repo)
            if val_ok:
                print(f"✅ Verified access to {gh_owner}/{gh_repo}!")
                if is_priv is not None:
                    detected_vis = '2' if is_priv else '1'
                    if detected_vis != repo_visibility:
                        vis_name = "Private" if is_priv else "Public"
                        update_vis = input(f"Detected repo visibility as {vis_name}. Update Repo Visibility setting to {vis_name}? [Y/n]: ").strip().lower()
                        if update_vis in ('', 'y', 'yes'):
                            repo_visibility = detected_vis
                            set_key(".env", "REPO_VISIBILITY", repo_visibility)
            else:
                print(f"⚠️ Warning: {val_res}")
        elif choice == '6':
            print("\nRepository Visibility determines the GitHub Actions cron schedule:")
            print("1. Public  -> Checks every 5 minutes (unlimited free GHA minutes)")
            print("2. Private -> Checks every 30 minutes (conserves your 2,000 monthly minutes)")
            repo_visibility = input("Select [1 for Public, 2 for Private]: ").strip()
            while repo_visibility not in ('1', '2'):
                repo_visibility = input("Please enter 1 or 2: ").strip()
            set_key(".env", "REPO_VISIBILITY", repo_visibility)
        else:
            print("Invalid choice. Please enter Y to proceed, 1-6 to edit, or Q to quit.")

    # Adjust cron schedule
    workflow_path = ".github/workflows/commands.yml"
    if os.path.exists(workflow_path):
        with open(workflow_path, "r", encoding="utf-8") as f:
            content = f.read()
        if repo_visibility == '2':
            content = content.replace("cron: '*/5 * * * *'", "cron: '*/30 * * * *'")
            print("✅ Adjusted GitHub Actions cron to every 30 minutes for Private repo.")
        else:
            content = content.replace("cron: '*/30 * * * *'", "cron: '*/5 * * * *'")
            print("✅ Maintained GitHub Actions cron at every 5 minutes for Public repo.")
        with open(workflow_path, "w", encoding="utf-8") as f:
            f.write(content)
            
    webhook_secret = os.getenv("TELEGRAM_SECRET_TOKEN")
    if not webhook_secret:
        webhook_secret = secrets.token_urlsafe(16)
        set_key(".env", "TELEGRAM_SECRET_TOKEN", webhook_secret)
        print(f"✅ Generated secure Webhook Secret.")
        
    encryption_key = os.getenv("ENCRYPTION_KEY")
    if not encryption_key:
        encryption_key = Fernet.generate_key().decode('utf-8')
        set_key(".env", "ENCRYPTION_KEY", encryption_key)
        print(f"✅ Generated secure Database Encryption Key.")
    
    github_secrets = {
        "TELEGRAM_BOT_TOKEN": bot_token,
        "TELEGRAM_CHAT_ID": chat_id,
        "GEMINI_API_KEY": gemini_key,
        "GITHUB_PAT": gh_pat,
        "ENCRYPTION_KEY": encryption_key,
        "AI_PROVIDER": "gemini",
        "AI_MODEL": "gemini-2.0-flash"
    }
    provision_github_secrets(github_secrets)
    
    cf_env_vars = {
        "GITHUB_OWNER": gh_owner,
        "GITHUB_REPO": gh_repo,
        "GITHUB_PAT": gh_pat,
        "TELEGRAM_SECRET_TOKEN": webhook_secret
    }
    
    worker_url = deploy_cloudflare_worker(cf_env_vars)
    
    setup_webhook(bot_token, worker_url, webhook_secret)
    send_success_message(bot_token, chat_id)
    
    print_header("🎉 All Done! RemNewz is fully configured and ready.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Setup paused. Progress saved in `.env` cache. Run `python setup.py` to resume.")
        sys.exit(0)
