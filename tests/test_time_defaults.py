"""Run both hooks as Taskwarrior does (JSON on stdin) in a non-UTC zone.

    python3 -m pytest -q tests/

Local midnight in America/Toronto is T040000Z (EDT) or T050000Z (EST), never T000000Z,
which is what on-modify used to look for before checking.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TASK = {'uuid': 'a', 'description': 'x', 'entry': '20261015T120000Z', 'status': 'pending'}


@pytest.fixture
def env(tmp_path):
    rc = tmp_path / 'taskrc'
    rc.write_text('time-defaults.due = 21:00\ntime-defaults.scheduled = 09:00\n')
    return {**os.environ, 'TASKRC': str(rc), 'TZ': 'America/Toronto'}


def run(hook, env, *tasks, args=None):
    # Taskwarrior passes the command line as argv: api:2 args:task … command:… rc:… data:… version:…
    argv = ['api:2', f'args:{args}', 'command:x', 'version:2.6.2'] if args else []
    out = subprocess.run([sys.executable, str(ROOT / hook), *argv], env=env, check=True, text=True,
                         capture_output=True, input=''.join(json.dumps(t) + '\n' for t in tasks))
    return json.loads(out.stdout)


def test_add_moves_local_midnight(env):
    assert run('on-add_time-defaults.py', env, {**TASK, 'due': '20261016T040000Z'})['due'] == '20261017T010000Z'


def test_modify_moves_local_midnight(env):
    new = run('on-modify_time-defaults.py', env, TASK, {**TASK, 'due': '20261016T040000Z'})
    assert new['due'] == '20261017T010000Z'           # 21:00 EDT on the 16th


def test_modify_uses_winter_offset(env):
    new = run('on-modify_time-defaults.py', env, TASK, {**TASK, 'scheduled': '20261216T050000Z'})
    assert new['scheduled'] == '20261216T140000Z'     # 09:00 EST


def test_modify_leaves_a_time(env):
    new = run('on-modify_time-defaults.py', env, TASK, {**TASK, 'due': '20261016T180000Z'})
    assert new['due'] == '20261016T180000Z'


def test_modify_leaves_an_unchanged_midnight(env):
    old = {**TASK, 'due': '20261016T040000Z'}
    new = run('on-modify_time-defaults.py', env, old, {**old, 'description': 'renamed'})
    assert new['due'] == '20261016T040000Z'


def test_modify_leaves_unconfigured_field(env):
    new = run('on-modify_time-defaults.py', env, TASK, {**TASK, 'wait': '20261016T040000Z'})
    assert new['wait'] == '20261016T040000Z'


# An explicit time in the command (2026-10-17T00:00:00) is meant: midnight stays midnight. That's
# how tw-web's Calendar writes an all-day task. Only a T time counts; due:sod is a date.
MID = '20261017T040000Z'                                  # local midnight, the 17th (EDT)


def test_modify_keeps_an_explicit_midnight(env):
    new = run('on-modify_time-defaults.py', env, TASK, {**TASK, 'scheduled': MID},
              args='task a1b2 modify scheduled:2026-10-17T00:00:00')
    assert new['scheduled'] == MID


def test_modify_date_only_still_gets_the_default(env):
    new = run('on-modify_time-defaults.py', env, TASK, {**TASK, 'scheduled': MID},
              args='task a1b2 modify scheduled:2026-10-17')
    assert new['scheduled'] == '20261017T130000Z'          # 09:00 EDT


@pytest.mark.parametrize('term', ['due:sod', 'due:tomorrow', "due:'2026-10-17'"])
def test_modify_named_dates_are_dates(env, term):
    new = run('on-modify_time-defaults.py', env, TASK, {**TASK, 'due': MID},
              args=f'task 5 modify {term}')
    assert new['due'] == '20261018T010000Z'                # 21:00 EDT


def test_modify_explicit_time_is_per_field(env):
    # sched has a time, due doesn't: only due gets its default
    new = run('on-modify_time-defaults.py', env, TASK, {**TASK, 'scheduled': MID, 'due': MID},
              args='task 5 modify sched:2026-10-17T00:00 due:2026-10-17')
    assert new['scheduled'] == MID and new['due'] == '20261018T010000Z'


def test_modify_ignores_the_description(env):
    # Words after -- are text, not attributes
    new = run('on-modify_time-defaults.py', env, TASK, {**TASK, 'due': MID},
              args='task 5 modify due:2026-10-17 -- see due:2026-10-17T00:00 notes')
    assert new['due'] == '20261018T010000Z'


def test_add_keeps_an_explicit_midnight(env):
    new = run('on-add_time-defaults.py', env, {**TASK, 'due': MID},
              args='task add x due:2026-10-17T00:00:00')
    assert new['due'] == MID


def test_add_date_only_still_gets_the_default(env):
    new = run('on-add_time-defaults.py', env, {**TASK, 'due': MID}, args='task add x due:2026-10-17')
    assert new['due'] == '20261018T010000Z'
