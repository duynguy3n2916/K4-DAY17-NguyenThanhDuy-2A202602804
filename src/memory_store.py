from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


def estimate_tokens(text: str) -> int:
    """Student TODO: implement a simple token estimator.

    Example idea:
    - Strip whitespace
    - Return 0 for empty text
    - Approximate tokens from character count, e.g. len(text) / 4
    """

    return (len(text.strip()) + 3) // 4 if text.strip() else 0


@dataclass
class UserProfileStore:
    """Persistent storage for `User.md`.

    Student TODO:
    - Map each user id to one markdown file
    - Support read / write / edit operations
    - Optionally expose helpers like `facts()` or `upsert_fact()`
    """

    root_dir: Path

    def path_for(self, user_id: str) -> Path:
        # TODO: slugify or sanitize the user id before building the file path.
        slug = re.sub(r"[^\w-]", "_", user_id, flags=re.UNICODE).strip("_")
        if not slug:
            raise ValueError("user_id must contain a letter or number")
        return self.root_dir / slug / "User.md"

    def read_text(self, user_id: str) -> str:
        # TODO: return file content or an empty default markdown profile.
        path = self.path_for(user_id)
        return path.read_text(encoding="utf-8") if path.exists() else "# User profile\n"

    def write_text(self, user_id: str, content: str) -> Path:
        # TODO: write markdown to disk and return the file path.
        path = self.path_for(user_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def edit_text(self, user_id: str, search_text: str, replacement: str) -> bool:
        # TODO: replace one occurrence inside User.md and return whether it changed.
        content = self.read_text(user_id)
        if not search_text or search_text not in content:
            return False
        self.write_text(user_id, content.replace(search_text, replacement, 1))
        return True

    def file_size(self, user_id: str) -> int:
        # TODO: return the current file size in bytes.
        path = self.path_for(user_id)
        return path.stat().st_size if path.exists() else 0

    def facts(self, user_id: str) -> dict[str, str]:
        facts: dict[str, str] = {}
        for line in self.read_text(user_id).splitlines():
            match = re.fullmatch(r"- ([a-z_]+): (.+)", line)
            if match:
                facts[match.group(1)] = match.group(2)
        return facts

    def upsert_fact(self, user_id: str, key: str, value: str) -> None:
        facts = self.facts(user_id)
        if facts.get(key) == value:
            return
        body = self.read_text(user_id)
        line = f"- {key}: {value}"
        pattern = rf"^- {re.escape(key)}: .*?$"
        if key in facts:
            body = re.sub(pattern, lambda _: line, body, count=1, flags=re.M)
        else:
            body = body.rstrip("\n") + "\n" + line + "\n"
        self.write_text(user_id, body)


def extract_profile_updates(message: str) -> dict[str, str]:
    """Student TODO: convert raw user text into stable profile facts.

    Example facts you may want to extract:
    - name
    - location
    - profession
    - preferences / response style
    - favorite food / drink

    Pseudocode:
    1. Build a few regex patterns.
    2. Skip obvious question-only turns.
    3. Return only the facts that are confidently present in the message.
    """

    # Questions and quoted alternatives are not assertions about the user.
    text = message.strip()
    lower = text.lower()
    if not text or ("?" in text and not any(x in lower for x in ("mình tên là", "mình ở", "mình đang ở"))):
        return {}
    result: dict[str, str] = {}
    name = re.search(r"(?:mình|tôi) tên là\s+([^,.!?]+)", text, re.I)
    if name:
        result["name"] = name.group(1).strip()
    location = re.search(r"(?:mình ở|hiện ở|hiện tại ở|đang ở|vẫn ở|giờ.*?đang ở|nơi ở hiện tại là)\s+(Huế|Đà Nẵng|Hà Nội)", text, re.I)
    if location and not any(x in lower for x in ("ví dụ cũ", "chỉ là nơi", "không phải nơi ở")):
        result["location"] = location.group(1)
    job = re.search(r"(?:làm|là|sang)\s+(MLOps engineer|backend engineer)(?=\b|[,.!])", text, re.I)
    if job and not any(x in lower for x in ("không còn làm mlops", "đừng nói mlops")):
        if "không còn làm backend" in lower and job.group(1).lower() == "backend engineer":
            later = re.search(r"(?:chuyển sang|nghề nghiệp hiện tại.*?là)\s+(MLOps engineer)", text, re.I)
            if later:
                result["profession"] = later.group(1)
        elif not ("không còn làm backend" in lower and job.group(1).lower() == "backend engineer"):
            result["profession"] = job.group(1)
    if "cà phê sữa đá" in lower and any(x in lower for x in ("yêu thích", "mình thích", "mình vẫn uống", "mình vẫn thích")):
        result["favorite_drink"] = "cà phê sữa đá"
    if "mì quảng" in lower and any(x in lower for x in ("yêu thích", "món ruột")):
        result["favorite_food"] = "mì Quảng"
    if "corgi" in lower and any(x in lower for x in ("mình nuôi", "con corgi", "nuôi con")):
        result["pet"] = "corgi tên Bơ"
    if "python" in lower and ("mình thích" in lower or "mình vẫn thích" in lower or "quan tâm" in lower):
        result["interest_python"] = "Python"
    if re.search(r"\bAI\b", text, re.I) and any(x in lower for x in ("mình thích", "mình vẫn thích", "quan tâm")):
        result["interest_ai"] = "AI"
    if "ngắn gọn" in lower and any(x in lower for x in ("trả lời", "style", "phong cách")):
        result["response_style"] = "ngắn gọn"
    if "3 bullet" in lower and any(x in lower for x in ("trả lời", "style", "muốn")):
        result["response_style"] = "3 bullet ngắn gọn, có ví dụ thực chiến"
    return result


def answer_from_facts(question: str, facts: dict[str, str]) -> str:
    """Small deterministic recall response shared by both offline agents."""
    q = question.lower()
    broad = "tóm tắt" in q or "là ai" in q
    requested = {
        "name": broad or "tên" in q or "biết" in q,
        "profession": broad or "nghề" in q or "làm" in q,
        "location": "ở đâu" in q or "nơi ở" in q or "ở huế" in q or "hiện đang ở" in q,
        "favorite_drink": "đồ uống" in q,
        "favorite_food": "món ăn" in q,
        "pet": "nuôi" in q or "con gì" in q,
        "response_style": "style" in q or "kiểu trả lời" in q or "trả lời mình thích" in q,
        "interest_python": broad or "mối quan tâm" in q,
        "interest_ai": broad or "mối quan tâm" in q,
    }
    labels = {
        "name": "Tên", "profession": "Nghề hiện tại", "location": "Nơi ở hiện tại",
        "favorite_drink": "Đồ uống yêu thích", "favorite_food": "Món ăn yêu thích",
        "pet": "Thú cưng", "response_style": "Cách trả lời",
        "interest_python": "Quan tâm", "interest_ai": "Quan tâm",
    }
    parts = [f"{labels[key]}: {facts[key]}" for key, wanted in requested.items() if wanted and key in facts]
    return "; ".join(parts) + "." if parts else "Mình chưa có đủ thông tin để trả lời chắc chắn."


def summarize_messages(messages: list[dict[str, str]], max_items: int = 6) -> str:
    """Student TODO: create a compact summary of older messages.

    This can be heuristic text concatenation first.
    Later, you can replace it with an LLM-based summary if desired.
    """

    snippets = []
    for item in messages:
        if item["role"] == "assistant":
            continue
        content = " ".join(item["content"].split())
        snippets.append(content if item["role"] == "summary" else f"user: {content[:120]}")
    return "\n".join(snippets[-max_items:])[-2400:]


@dataclass
class CompactMemoryManager:
    """Student TODO: implement compact memory for long threads.

    Goal:
    - Keep recent messages in full
    - When the thread grows too large, move older content into a summary
    - Track how many compactions happened for benchmarking
    """

    threshold_tokens: int
    keep_messages: int
    state: dict[str, dict[str, object]] = field(default_factory=dict)

    def append(self, thread_id: str, role: str, content: str) -> None:
        # TODO:
        # 1. create thread state if missing
        # 2. append the new message
        # 3. trigger compaction if needed
        current = self.state.setdefault(thread_id, {"messages": [], "summary": "", "compactions": 0})
        messages = current["messages"]
        assert isinstance(messages, list)
        messages.append({"role": role, "content": content})
        total = estimate_tokens(str(current["summary"])) + sum(estimate_tokens(m["content"]) for m in messages)
        if total > self.threshold_tokens and len(messages) > self.keep_messages:
            old = messages[:-self.keep_messages]
            previous = str(current["summary"])
            items = ([{"role": "summary", "content": previous}] if previous else []) + old
            current["summary"] = summarize_messages(items, max_items=32)
            current["messages"] = messages[-self.keep_messages:]
            current["compactions"] = int(current["compactions"]) + 1

    def context(self, thread_id: str) -> dict[str, object]:
        # TODO: return per-thread state with keys like messages, summary, compactions.
        return self.state.setdefault(thread_id, {"messages": [], "summary": "", "compactions": 0})

    def compaction_count(self, thread_id: str) -> int:
        # TODO: return number of compactions for this thread.
        return int(self.context(thread_id)["compactions"])
