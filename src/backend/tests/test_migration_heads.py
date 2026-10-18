"""HC-MIGHEAD — each Alembic chain has exactly one head and stays linear
(MIG-02, C-MIG-1, C-MIG-2). Two heads mean `upgrade head` is ambiguous, and a
vault could miss a table."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from alembic.script import ScriptDirectory

from core.migrations import _get_alembic_config

CHAINS = ("master", "profile")


def _script(chain: str) -> ScriptDirectory:
    return ScriptDirectory.from_config(_get_alembic_config(chain))


def _single_head(script: ScriptDirectory, label: str) -> str:
    heads = script.get_heads()
    assert len(heads) == 1, (
        f"{label} chain has {len(heads)} heads {sorted(heads)}; expected exactly 1 (C-MIG-2)"
    )
    return heads[0]


@pytest.mark.parametrize("chain", CHAINS)
def test_hc_mighead_001_each_chain_has_exactly_one_head(chain):
    _single_head(_script(chain), chain)


def test_hc_mighead_002_a_forked_chain_is_detected(tmp_path):
    real = _script("profile")
    head = _single_head(real, "profile")
    parent = real.get_revision(head).down_revision
    assert isinstance(parent, str), "profile head has no single parent to fork from"

    fork_dir = tmp_path / "profile"
    shutil.copytree(Path(real.dir), fork_dir, ignore=shutil.ignore_patterns("__pycache__"))
    (fork_dir / "versions" / "999_hc_mighead_fork.py").write_text(
        'revision = "999_hc_mighead_fork"\n'
        f'down_revision = "{parent}"\n'
        "branch_labels = None\n"
        "depends_on = None\n\n\n"
        "def upgrade():\n    pass\n\n\n"
        "def downgrade():\n    pass\n",
        encoding="utf-8",
    )

    with pytest.raises(AssertionError, match="has 2 heads"):
        _single_head(ScriptDirectory(str(fork_dir)), "forked profile")


@pytest.mark.parametrize("chain", CHAINS)
def test_hc_mighead_003_every_revision_has_at_most_one_parent(chain):
    merges = [
        rev.revision
        for rev in _script(chain).walk_revisions()
        if isinstance(rev.down_revision, (tuple, list))
    ]
    assert merges == [], f"{chain} chain has merge revisions {merges}; C-MIG-1 requires linear"
