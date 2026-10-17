#!/usr/bin/env python3
# on-modify_time-defaults — apply configured default times to date-only fields
#
# When a task is modified with due/scheduled/wait/until set to a date only
# (no time specified), Taskwarrior stores midnight local time. This hook
# replaces that midnight with a configured default time. A time given in the
# command (due:2026-10-17T00:00) is left alone: midnight on purpose (all-day).
#
# Config (in time-defaults.rc, included from ~/.taskrc):
#   time-defaults.due       = 21:00
#   time-defaults.scheduled = 09:00
#   time-defaults.wait      = 06:00
#   time-defaults.until     = 23:59

# ── Phase 1: fast path ────────────────────────────────────────────────────────
import sys, json

DATE_FIELDS = ('due', 'scheduled', 'wait', 'until')

lines = sys.stdin.read().splitlines()
old = json.loads(lines[0])
new = json.loads(lines[1])

# Only date fields this modify set or changed: a date already on the task stays as it is
# (an edit to the description must not move an old midnight date).
changed = [f for f in DATE_FIELDS if f in new and new[f] != old.get(f)]
if not changed:
    print(json.dumps(new))
    sys.exit(0)

# ── Phase 2: heavy imports — only reached if a date field changed ─────────────
import os
import re
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


def _explicit_times():
    """Fields the command gave a time for (due:2026-10-17T00:00): a midnight there is meant.

    Taskwarrior passes the command line as argv 'args:task …'. A name is an abbreviation of the
    field (sched:), at least two letters; words after -- are text. Only a T time counts, so
    due:sod and due:tomorrow are dates and still get the default.
    """
    line = next((a[5:] for a in sys.argv[1:] if a.startswith('args:')), '')
    line = line.split(' -- ', 1)[0]
    fields = set()
    for m in re.finditer(r'(?:^|\s)([a-z]{2,}):(\S+)', line):
        name, value = m.groups()
        if re.search(r'\dT\d', value):
            fields.update(f for f in DATE_FIELDS if f.startswith(name))
    return fields


cfg = _read_config()
explicit = _explicit_times()

for field in changed:
    key = f'time-defaults.{field}'
    if field not in explicit and key in cfg and _is_local_midnight(new[field]):
        new[field] = _apply_time(new[field], cfg[key])

print(json.dumps(new))
