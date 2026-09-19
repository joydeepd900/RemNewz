import os
import sys
import json
import urllib.request
import urllib.error

# Add parent directory to path so we can import from dotenv if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    print("Error: TELEGRAM_BOT_TOKEN is not set in the environment or .env file.")
    sys.exit(1)

API_URL = f"https://api.telegram.org/bot{TOKEN}/setMyCommands"

COMMANDS = [
    {"command": "digest", "description": "Get your daily AI news digest now"},
    {"command": "news", "description": "Instant news & search (e.g. /news python)"},
    {"command": "todo", "description": "Add a task (e.g. /todo Read docs by 5pm)"},
    {"command": "list", "description": "View active tasks"},
    {"command": "done", "description": "Mark task completed (e.g. /done abc1234)"},
    {"command": "remove", "description": "Delete task permanently"},
    {"command": "history", "description": "View recently completed tasks"},
    {"command": "source", "description": "Manage news sources & RSS feeds"},
    {"command": "config", "description": "Settings, timezones & topic binding"},
    {"command": "help", "description": "Show command reference & help"}
]

SCOPES = [
    {"type": "default"},
    {"type": "all_private_chats"},
    {"type": "all_group_chats"},
    {"type": "all_chat_administrators"}
]

def register_commands():
    print("Registering commands for bot...")
    
    success = True
    for scope in SCOPES:
        payload = {
            "commands": COMMANDS,
            "scope": scope
        }
        
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(API_URL, data=data, headers={"Content-Type": "application/json"})
        
        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode())
                if result.get("ok"):
                    print(f"Successfully registered commands for scope: {scope['type']}")
                else:
                    print(f"Failed to register for scope {scope['type']}: {result}")
                    success = False
        except urllib.error.URLError as e:
            print(f"HTTP Error for scope {scope['type']}: {e}")
            success = False

    if success:
        print("\nAll command scopes registered successfully!")
        print("Note: Telegram clients cache commands. If you don't see them immediately in a chat, restart the Telegram app or switch chats to refresh.")
    else:
        print("\nSome scopes failed to register.")

if __name__ == "__main__":
    register_commands()
