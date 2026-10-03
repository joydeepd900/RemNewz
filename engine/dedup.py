import os
import json
from datetime import datetime, timedelta, timezone
from engine.store import load_data, save_data

MAX_ITEMS = 2000
RETENTION_DAYS = 30

class DedupManager:
    """
    Manages deduplication of seen news items to prevent repetitive deliveries.
    
    Uses an encrypted key-value store to persist the history of sent items.
    Enforces retention limits (e.g., max 2000 items, max 30 days) during pruning.
    """
    def __init__(self, *args, **kwargs):
        self.seen_items = {}
        self._load()

    def _load(self):
        """Load seen items from the JSON file."""
        self.seen_items = load_data("seen", {})

    def _save(self):
        """Save seen items to the JSON file."""
        try:
            save_data("seen", self.seen_items)
        except Exception as e:
            print(f"[dedup] Failed to save seen items: {e}")

    def is_seen(self, item_id: str) -> bool:
        """
        Check if an item identifier has already been processed.
        
        Args:
            item_id (str): The unique identifier for the item.
            
        Returns:
            bool: True if the item is present in the seen history, False otherwise.
        """
        return item_id in self.seen_items

    def mark_seen(self, item_id: str):
        """
        Record an item as seen using the current UTC timestamp.
        
        Args:
            item_id (str): The unique identifier for the item.
        """
        # Store timestamp in ISO 8601 format
        self.seen_items[item_id] = datetime.now(timezone.utc).isoformat()
        self._save()

    def prune(self):
        """
        Remove stale entries based on configured retention limits.
        
        Discards any seen records older than the maximum retention period (30 days)
        and enforces an absolute limit on the total number of items stored (2000)
        to prevent database bloat.
        """
        if not self.seen_items:
            return

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
        
        pruned = {}
        for item_id, ts_str in self.seen_items.items():
            try:
                ts = datetime.fromisoformat(ts_str)
                if ts >= cutoff_date:
                    pruned[item_id] = ts
            except ValueError:
                pass # Drop invalid timestamps

        # Sort by timestamp descending (newest first)
        sorted_items = sorted(
            pruned.items(), 
            key=lambda x: x[1], 
            reverse=True
        )

        # Enforce max limit
        if len(sorted_items) > MAX_ITEMS:
            sorted_items = sorted_items[:MAX_ITEMS]

        # Re-build dictionary
        self.seen_items = {k: v.isoformat() for k, v in sorted_items}
        self._save()
