- Project: https://github.com/linuxcaffe/tw-time-defaults-hook
- Issues:  https://github.com/linuxcaffe/tw-time-defaults-hook/issues

# time-defaults

A Taskwarrior hook that applies configurable default times to date-only task fields.

---

## Why this exists

When you add a task with `due:today` or `scheduled:friday`, Taskwarrior stores midnight as the
time component. Midnight is rarely what you mean. A due date of today at midnight is already
overdue by the time you wake up; a scheduled date at midnight fires urgency calculations at the
wrong moment.

This hook intercepts those midnight timestamps on add and modify, replacing them with times that
actually match your workflow — configured once, applied automatically.

---

## What this means for you

Set `due:friday` and it lands at your configured end-of-day time. Set `scheduled:tomorrow` and it
appears in your list at your configured start-of-day. No more midnight phantom urgency.

---

## Configuration

`~/.task/config/time-defaults.rc` — created on install, edit to taste:

```ini
time-defaults.due       = 21:00
time-defaults.scheduled = 09:00
time-defaults.wait      = 06:00
time-defaults.until     = 23:59
```

Comment out any field to leave it at midnight (disabling the default for that field).
Times are in 24-hour `HH:MM` format, interpreted in your **local timezone**.

Add to `~/.taskrc`:

```ini
include ~/.task/config/time-defaults.rc
```

---

## Installation

### Option 1 — Install script

```bash
curl -fsSL https://raw.githubusercontent.com/linuxcaffe/tw-time-defaults-hook/main/time-defaults.install | bash
```

Installs both hooks to `~/.task/hooks/` and a starter config to `~/.task/config/`.

### Option 2 — Via [awesome-taskwarrior](https://github.com/linuxcaffe/awesome-taskwarrior)

```bash
tw -I time-defaults
```

### Option 3 — Manual

```bash
BASE=https://raw.githubusercontent.com/linuxcaffe/tw-time-defaults-hook/main

curl -fsSL "$BASE/on-add_time-defaults.py"    -o ~/.task/hooks/on-add_time-defaults.py
curl -fsSL "$BASE/on-modify_time-defaults.py" -o ~/.task/hooks/on-modify_time-defaults.py
chmod +x ~/.task/hooks/on-*_time-defaults.py

# Config (skip if already present)
[[ -f ~/.task/config/time-defaults.rc ]] || \
    curl -fsSL "$BASE/time-defaults.rc" -o ~/.task/config/time-defaults.rc
```

Then add to `~/.taskrc`:

```ini
include ~/.task/config/time-defaults.rc
```

Verify: `task add test due:today && task 1 info | grep Due`

---

## Usage

No commands needed — the hook fires automatically on `task add` and `task modify`.

```bash
task add write release notes due:friday
# → due stored as friday at 21:00 (your configured time), not midnight

task add prepare slides scheduled:tomorrow
# → scheduled stored as tomorrow at 09:00, not midnight

task modify 42 wait:monday
# → wait stored as monday at 06:00, not midnight
```

Explicitly specifying a time bypasses the hook entirely:

```bash
task add urgent fix due:today+2h     # → 2 hours from now, unchanged
task add meeting due:2026-04-01T14:00 # → 14:00, unchanged
```

---

## How it works

Both hooks use a **two-phase lazy import** pattern for minimal overhead on the common case:

**Phase 1** (always): read stdin JSON, check whether any date field is present. If not —
the vast majority of task operations — output the task unchanged and exit immediately
without loading `datetime` or reading the config file.

**Phase 2** (only when a date field is present): check whether the field is at local
midnight. If so, read the config from TASKRC (following includes, no subprocess calls)
and apply the configured default time.

The result: zero overhead on tasks without date fields, minimal overhead on the rest.

---

## Project status

Active. Tested on Taskwarrior 2.6.x, Linux.

---

## Metadata

- License: MIT
- Language: Python 3
- Requires: Taskwarrior 2.6.x, Python 3.6+
- Version: 1.0.0
