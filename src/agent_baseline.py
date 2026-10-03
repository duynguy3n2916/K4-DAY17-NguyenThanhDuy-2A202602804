from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from config import LabConfig, load_config
from memory_store import answer_from_facts, estimate_tokens, extract_profile_updates
from model_provider import build_chat_model


@dataclass
class SessionState:
    messages: list[dict[str, str]] = field(default_factory=list)
    token_usage: int = 0
    prompt_tokens_processed: int = 0


class BaselineAgent:
    """Student TODO: implement Agent A.

    Requirements:
    - Within-session memory only
    - No persistent `User.md`
    - Should forget long-term facts across new threads
    """

    def __init__(self, config: LabConfig | None = None, force_offline: bool = False) -> None:
        self.config = config or load_config()
        self.force_offline = force_offline
        self.sessions: dict[str, SessionState] = {}

        # TODO: optionally initialize a real LangChain/LangGraph agent when dependencies exist.
        self.langchain_agent = None if force_offline else self._maybe_build_langchain_agent()

    def reply(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        """Student TODO: return the agent response and token accounting.

        Pseudocode:
        - If a live agent exists, call the live path.
        - Otherwise use a deterministic offline path.
        """

        if self.langchain_agent is None:
            return self._reply_offline(thread_id, message)
        session = self.sessions.setdefault(thread_id, SessionState())
        session.messages.append({"role": "user", "content": message})
        prompt = [(m["role"], m["content"]) for m in session.messages]
        prompt_tokens = sum(estimate_tokens(m["content"]) for m in session.messages)
        response = str(self.langchain_agent.invoke(prompt).content)
        session.messages.append({"role": "assistant", "content": response})
        session.token_usage += estimate_tokens(message) + estimate_tokens(response)
        session.prompt_tokens_processed += prompt_tokens
        return {"response": response, "tokens": session.token_usage, "prompt_tokens": session.prompt_tokens_processed}

    def token_usage(self, thread_id: str) -> int:
        # TODO: return cumulative agent token count for one thread.
        return self.sessions.get(thread_id, SessionState()).token_usage

    def prompt_token_usage(self, thread_id: str) -> int:
        # TODO: estimate how much prompt context this baseline kept processing.
        return self.sessions.get(thread_id, SessionState()).prompt_tokens_processed

    def compaction_count(self, thread_id: str) -> int:
        # Baseline has no compact memory.
        return 0

    def _reply_offline(self, thread_id: str, message: str) -> dict[str, Any]:
        """Student TODO: implement a simple offline behavior.

        Suggested behavior:
        - Store the new user message in the session
        - Generate a short deterministic reply
        - Update token counts
        - Never remember facts across different thread ids
        """

        session = self.sessions.setdefault(thread_id, SessionState())
        session.messages.append({"role": "user", "content": message})
        prompt_tokens = sum(estimate_tokens(m["content"]) for m in session.messages)
        facts: dict[str, str] = {}
        for item in session.messages:
            if item["role"] == "user":
                facts.update(extract_profile_updates(item["content"]))
        response = answer_from_facts(message, facts)
        if response.startswith("Mình chưa") and not ("?" in message or "nhắc" in message.lower()):
            response = "Mình đã ghi nhận thông tin trong cuộc trò chuyện này."
        session.messages.append({"role": "assistant", "content": response})
        session.token_usage += estimate_tokens(message) + estimate_tokens(response)
        session.prompt_tokens_processed += prompt_tokens
        return {"response": response, "tokens": session.token_usage, "prompt_tokens": session.prompt_tokens_processed}

    def _maybe_build_langchain_agent(self):
        """Student TODO: optionally wire `create_agent` + `InMemorySaver` here.

        Use `build_chat_model(self.config.model)` so the baseline can run with any supported provider.
        """

        if not self.config.model.api_key and self.config.model.provider != "ollama":
            return None
        return build_chat_model(self.config.model)
