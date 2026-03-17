#!/usr/bin/env python3
# on-add_time-defaults — apply configured default times to date-only fields
#
# When a task is added with due/scheduled/wait/until set to a date only
# (no time specified), Taskwarrior stores midnight local time. This hook
# replaces that midnight with a configured default time.
#
# Config (in time-defaults.rc, included from ~/.taskrc):
#   time-defaults.due       = 21:00
#   time-defaults.scheduled = 09:00
#   time-defaults.wait      = 06:00
#   time-defaults.until     = 23:59

# ── Phase 1: fast path ────────────────────────────────────────────────────────
import sys, json

DATE_FIELDS = ('due', 'scheduled', 'wait', 'until')

new = json.loads(sys.stdin.readline())

if not any(f in new for f in DATE_FIELDS):
    print(json.dumps(new))
    sys.exit(0)

# ── Phase 2: heavy imports — only reached if task has at least one date field ─
import os
from datetime import datetime, timezone


def _read_config():
    """Parse TASKRC (following includes) for time-defaults.* keys."""
    cfg = {}
    taskrc = os.environ.get('TASKRC', os.path.expanduser('~/.taskrc'))

    def _parse(path, depth=0):
        if depth > 5:
            return
        try:
            with open(os.path.expanduser(path)) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('include '):
                        _parse(line[8:].strip(), depth + 1)
                    elif line.startswith('time-defaults.'):
                        key, _, val = line.partition('=')
                        cfg[key.strip()] = val.strip()
        except OSError:
            pass

    _parse(taskrc)
    return cfg


def _is_local_midnight(ts):
    """True if the UTC timestamp represents midnight in the local timezone."""
    dt = datetime.strptime(ts, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    local = dt.astimezone()
    return local.hour == 0 and local.minute == 0 and local.second == 0


def _apply_time(ts, t_str):
    """Replace the time component of a UTC timestamp with t_str (HH:MM or HH:MM:SS)."""
    dt = datetime.strptime(ts, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    local = dt.astimezone()
    parts = t_str.split(':')
    h, m = int(parts[0]), int(parts[1])
    s = int(parts[2]) if len(parts) > 2 else 0
    new_local = local.replace(hour=h, minute=m, second=s, microsecond=0)
    return new_local.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


cfg = _read_config()

for field in DATE_FIELDS:
    key = f'time-defaults.{field}'
    if field in new and key in cfg and _is_local_midnight(new[field]):
        new[field] = _apply_time(new[field], cfg[key])

print(json.dumps(new))
