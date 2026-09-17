import os
import json
from datetime import datetime, timedelta, timezone

DATA_DIR = "data"
SEEN_FILE = os.path.join(DATA_DIR, "seen.json")
MAX_ITEMS = 1000
RETENTION_DAYS = 14

class DedupManager:
    def __init__(self, file_path=SEEN_FILE):
        self.file_path = file_path
        self.seen_items = {}
        self._load()

    def _load(self):
        """Load seen items from the JSON file."""
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR, exist_ok=True)
            
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self.seen_items = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.seen_items = {}

    def _save(self):
        """Save seen items to the JSON file."""
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.seen_items, f, indent=2)
        except IOError as e:
            print(f"[dedup] Failed to save seen items: {e}")

    def is_seen(self, item_id: str) -> bool:
        """Check if an item has been seen."""
        return item_id in self.seen_items

    def mark_seen(self, item_id: str):
        """Mark an item as seen with the current timestamp."""
        # Store timestamp in ISO 8601 format
        self.seen_items[item_id] = datetime.now(timezone.utc).isoformat()
        self._save()

    def prune(self):
        """Prune old items based on retention policy (14 days or 1000 max items)."""
        if not self.seen_items:
            return

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
        
        # Filter by age
        pruned = {}
        for item_id, ts_str in self.seen_items.items():
            try:
                ts = datetime.fromisoformat(ts_str)
                if ts >= cutoff_date:
                    pruned[item_id] = ts_str
            except ValueError:
                pass # Drop invalid timestamps

        # Sort by timestamp descending (newest first)
        sorted_items = sorted(
            pruned.items(), 
            key=lambda x: datetime.fromisoformat(x[1]), 
            reverse=True
        )

        # Enforce max limit
        if len(sorted_items) > MAX_ITEMS:
            sorted_items = sorted_items[:MAX_ITEMS]

        self.seen_items = dict(sorted_items)
        self._save()
