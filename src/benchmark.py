from __future__ import annotations

import json
import tempfile
from dataclasses import replace
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_advanced import AdvancedAgent
from agent_baseline import BaselineAgent
from config import load_config
from tabulate import tabulate


@dataclass
class BenchmarkRow:
    agent_name: str
    agent_tokens_only: int
    prompt_tokens_processed: int
    recall_score: float
    response_quality: float
    memory_growth_bytes: int
    compactions: int


def load_conversations(path: Path) -> list[dict[str, Any]]:
    """Student TODO: read JSON conversations from disk."""

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Expected a list of conversations in {path}")
    return data


def recall_points(answer: str, expected: list[str]) -> float:
    """Student TODO: return 0 / 0.5 / 1 depending on how many expected facts appear."""

    if not expected:
        return 1.0
    answer_folded = answer.casefold()
    return sum(fact.casefold() in answer_folded for fact in expected) / len(expected)


def heuristic_quality(answer: str, expected: list[str]) -> float:
    """Student TODO: add a lightweight quality score for offline mode."""

    if not answer.strip() or answer.startswith("Mình chưa"):
        return 0.0
    return round(0.3 + 0.7 * recall_points(answer, expected), 3)


def run_agent_benchmark(agent_name: str, agent, conversations: list[dict[str, Any]], config) -> BenchmarkRow:
    """Student TODO: evaluate one agent over many conversations.

    Pseudocode:
    1. Feed all turns to the agent.
    2. Track `agent tokens only`.
    3. Track `prompt tokens processed`.
    4. Ask recall questions in a fresh thread.
    5. Compute average recall and quality.
    6. Record memory file growth and compaction count.
    """

    threads: list[str] = []
    recall_scores: list[float] = []
    quality_scores: list[float] = []
    users = {item["user_id"] for item in conversations}
    before = {user: agent.memory_file_size(user) if hasattr(agent, "memory_file_size") else 0 for user in users}

    for conversation in conversations:
        thread = conversation["id"]
        user = conversation["user_id"]
        threads.append(thread)
        for turn in conversation["turns"]:
            agent.reply(user, thread, turn)
        for index, item in enumerate(conversation["recall_questions"]):
            recall_thread = f"{thread}-recall-{index}"
            threads.append(recall_thread)
            response = agent.reply(user, recall_thread, item["question"])["response"]
            recall_scores.append(recall_points(response, item["expected_contains"]))
            quality_scores.append(heuristic_quality(response, item["expected_contains"]))

    growth = sum((agent.memory_file_size(user) if hasattr(agent, "memory_file_size") else 0) - before[user] for user in users)
    return BenchmarkRow(
        agent_name=agent_name,
        agent_tokens_only=sum(agent.token_usage(thread) for thread in threads),
        prompt_tokens_processed=sum(agent.prompt_token_usage(thread) for thread in threads),
        recall_score=sum(recall_scores) / len(recall_scores) if recall_scores else 0.0,
        response_quality=sum(quality_scores) / len(quality_scores) if quality_scores else 0.0,
        memory_growth_bytes=growth,
        compactions=sum(agent.compaction_count(thread) for thread in threads),
    )


def format_rows(rows: list[BenchmarkRow]) -> str:
    """Student TODO: print a markdown table or tabulated output."""

    headers = ["Agent", "Agent tokens only", "Prompt tokens processed", "Cross-session recall", "Response quality", "Memory growth (bytes)", "Compactions"]
    values = [[r.agent_name, r.agent_tokens_only, r.prompt_tokens_processed,
               f"{r.recall_score:.1%}", f"{r.response_quality:.1%}",
               r.memory_growth_bytes, r.compactions] for r in rows]
    return tabulate(values, headers=headers, tablefmt="github")


def main() -> None:
    """Student TODO: run both benchmark suites.

    Required benchmark sections:
    - Standard benchmark from `data/conversations.json`
    - Long-context stress benchmark from `data/advanced_long_context.json`

    Compare:
    - Baseline
    - Advanced

    Keep the same output columns as the solved lab:
    - Agent tokens only
    - Prompt tokens processed
    - Cross-session recall
    - Response quality
    - Memory growth (bytes)
    - Compactions
    """

    config = load_config(Path(__file__).resolve().parent.parent)

    # TODO:
    # - load both datasets from root/data
    # - initialize baseline and advanced agents
    # - run benchmarks
    # - print comparison tables
    suites = [
        ("Standard Benchmark", config.data_dir / "conversations.json"),
        ("Long-Context Stress Benchmark", config.data_dir / "advanced_long_context.json"),
    ]
    for title, path in suites:
        conversations = load_conversations(path)
        with tempfile.TemporaryDirectory(prefix="day17-benchmark-") as temp_dir:
            isolated = replace(config, state_dir=Path(temp_dir))
            baseline = BaselineAgent(isolated, force_offline=True)
            advanced = AdvancedAgent(isolated, force_offline=True)
            rows = [
                run_agent_benchmark("Baseline", baseline, conversations, isolated),
                run_agent_benchmark("Advanced", advanced, conversations, isolated),
            ]
        print(f"\n## {title}\n{format_rows(rows)}")


if __name__ == "__main__":
    main()
