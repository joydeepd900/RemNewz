"""
main_digest.py — Entrypoint for the Newzy digest workflow.

Phase 0:  Sends a formatted test message to verify the full pipeline.
Phase 1+: Fetches news, synthesizes with AI, and sends the digest.
"""

import os
import sys

# Fix Windows console encoding for emoji in print statements
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass  # Running in GitHub Actions, encoding is fine

from dotenv import load_dotenv

# Load .env for local development (GitHub Actions uses secrets instead)
load_dotenv()

from engine.time_utils import now_local, format_datetime
from notifier.telegram import send_message


def build_test_message():
    """Build a formatted HTML test message for Phase 0 verification."""
    now = now_local()
    timestamp = format_datetime(now, style="full")

    ai_provider = os.environ.get("AI_PROVIDER", "none")
    ai_model = os.environ.get("AI_MODEL", "not configured")
    timezone = os.environ.get("TIMEZONE", "UTC")

    message = (
        "\U0001f9ea <b>RemNewz \u2014 Phase 0 Infrastructure Test</b>\n"
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
        f"\u2705 <b>Telegram delivery:</b> Working\n"
        f"\U0001f550 <b>Local time:</b> {timestamp}\n"
        f"\U0001f30d <b>Timezone:</b> {timezone}\n"
        f"\U0001f916 <b>AI Provider:</b> {ai_provider}\n"
        f"\U0001f9e0 <b>AI Model:</b> {ai_model}\n\n"
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
        "\U0001f4e1 <i>Pipeline verified. Ready for Phase 1.</i>"
    )
    return message


def main():
    """Main entrypoint for the digest workflow."""
    print("[main_digest] Starting RemNewz digest pipeline...")
    print("[main_digest] Mode: Phase 0 -- Infrastructure Test")

    try:
        message = build_test_message()
        print("[main_digest] Sending test message to Telegram...")
        responses = send_message(message)

        if responses and responses[0].get("ok"):
            print("[main_digest] OK - Test message sent successfully!")
            return 0
        else:
            print(f"[main_digest] FAIL - Message send failed: {responses}")
            return 1

    except Exception as e:
        print(f"[main_digest] FAIL - Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
