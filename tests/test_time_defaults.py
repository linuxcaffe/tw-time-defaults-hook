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


def run(hook, env, *tasks):
    out = subprocess.run([sys.executable, str(ROOT / hook)], env=env, check=True, text=True,
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
