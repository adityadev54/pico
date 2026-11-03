"""Disk grants are authoritative when changed externally; never union old access.
UI changes remain in memory until save. External revocations/downgrades win
when both happen together, rather than silently restoring stronger access.
"""
import copy
import json
from pathlib import Path

class GrantFile:
    def __init__(self, path):
        self.path = Path(path)
        self.snapshot = self.read()

    def read(self):
        try:
            value = json.loads(self.path.read_text()).get('grants', [])
            return value if isinstance(value, list) else []
        except (OSError, ValueError, AttributeError):
            return []

    def reconcile(self, memory):
        disk = self.read()
        if disk != self.snapshot:
            self.snapshot = copy.deepcopy(disk)
            return copy.deepcopy(disk)
        return memory

    def saved(self, grants):
        self.snapshot = copy.deepcopy(grants)
