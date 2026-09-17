"""
main_commands.py — Entrypoint for the Remzy & Helpzy command workflow.

Phase 2: Runs the deadline evaluator for tasks and sends due/overdue nudges.
Phase 3+: Will act as the batched Telegram long-poller and NLP router.
"""

import sys

# Fix Windows console encoding for emoji in print statements
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from dotenv import load_dotenv

# Load .env for local development
load_dotenv()

from personas.remzy import Remzy

def main():
    print("[main_commands] Starting RemNewz commands pipeline (Phase 2)...")
    
    # Run the deadline checker
    remzy = Remzy()
    print("[main_commands] Evaluating task deadlines...")
    remzy.check_deadlines()
    
    print("[main_commands] Commands pipeline complete.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
