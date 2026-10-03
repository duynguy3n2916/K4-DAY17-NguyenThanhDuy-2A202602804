from __future__ import annotations

from pathlib import Path
from dataclasses import replace

from agent_advanced import AdvancedAgent
from agent_baseline import BaselineAgent
from config import load_config
from memory_store import UserProfileStore


def make_config(tmp_path: Path):
    """Student TODO: build an isolated config for tests."""

    # Hint:
    # - point `state_dir` into tmp_path
    # - reduce compact threshold so compaction happens quickly in tests
    return replace(load_config(tmp_path), compact_threshold_tokens=150, compact_keep_messages=2)


def test_user_markdown_read_write_edit(tmp_path: Path) -> None:
    """Student TODO: verify `User.md` can be created, updated, and edited."""

    store = UserProfileStore(tmp_path / "profiles")
    path = store.write_text("duy", "# User profile\n- location: Huế\n")
    assert path.exists()
    assert "Huế" in store.read_text("duy")
    assert store.edit_text("duy", "Huế", "Đà Nẵng")
    assert "Đà Nẵng" in store.read_text("duy")
    assert not store.edit_text("duy", "Hà Nội", "Huế")
    assert store.file_size("duy") > 0


def test_compact_trigger(tmp_path: Path) -> None:
    """Student TODO: verify long threads trigger compaction."""

    agent = AdvancedAgent(make_config(tmp_path), force_offline=True)
    for _ in range(8):
        agent.reply("duy", "long-thread", "Đây là một đoạn hội thoại dài về memory. " * 12)
    context = agent.compact_memory.context("long-thread")
    assert agent.compaction_count("long-thread") > 0
    assert len(context["messages"]) <= 2
    assert context["summary"]


def test_cross_session_recall(tmp_path: Path) -> None:
    """Student TODO: verify advanced remembers across sessions and baseline does not."""

    config = make_config(tmp_path)
    baseline = BaselineAgent(config, force_offline=True)
    advanced = AdvancedAgent(config, force_offline=True)
    statement = "Mình tên là DũngCT."
    baseline.reply("duy", "old", statement)
    advanced.reply("duy", "old", statement)
    question = "Mình tên gì?"
    baseline_answer = baseline.reply("duy", "new", question)["response"]
    advanced_answer = advanced.reply("duy", "new", question)["response"]
    assert "DũngCT" not in baseline_answer
    assert "DũngCT" in advanced_answer
    assert advanced.memory_file_size("duy") > 0


def test_compact_reduces_prompt_load_on_long_thread(tmp_path: Path) -> None:
    """Student TODO: compare prompt load of baseline vs advanced on a long thread."""

    config = make_config(tmp_path)
    baseline = BaselineAgent(config, force_offline=True)
    advanced = AdvancedAgent(config, force_offline=True)
    for _ in range(12):
        message = "Mình đang so sánh chi phí prompt khi lịch sử hội thoại tăng. " * 10
        baseline.reply("duy", "long", message)
        advanced.reply("duy", "long", message)
    assert advanced.compaction_count("long") > 0
    assert advanced.prompt_token_usage("long") < baseline.prompt_token_usage("long")
