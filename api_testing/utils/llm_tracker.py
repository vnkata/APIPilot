from datetime import datetime, timezone
import json
import os
from dataclasses import dataclass

@dataclass
class LLMUsage:
    prompt_tokens: int
    completion_tokens: int
    cached_tokens: int = 0
    reasoning_tokens: int = 0

llm_tracker = {
    "total_tokens": 0,
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "cached_tokens": 0,
    "reasoning_tokens": 0
}

_llm_tracker_file = "./llm_tracker.json"

def initTracker(dir: str | None = None, model: str | None = None):
    global _llm_tracker_file, llm_tracker
    _llm_tracker_file = os.path.join(dir, f"{model}_usages.json")

    default_tracker = {
        "total_tokens": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "cached_tokens": 0,
        "reasoning_tokens": 0
    }

    if os.path.exists(_llm_tracker_file):
        try:
            with open(_llm_tracker_file, "r", encoding="utf-8") as f:
                llm_tracker = json.load(f)

            # backward compatibility
            for k, v in default_tracker.items():
                llm_tracker.setdefault(k, v)

        except Exception:
            llm_tracker = default_tracker.copy()
    else:
        llm_tracker = default_tracker.copy()

    with open(_llm_tracker_file, "w", encoding="utf-8") as f:
        json.dump(llm_tracker, f, indent=2, ensure_ascii=False)

def add_usage(
        caller: str = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        cached_tokens: int = 0,
        reasoning_tokens: int = 0,
    ):
    global llm_tracker, _llm_tracker_file
    llm_tracker["prompt_tokens"] += prompt_tokens
    llm_tracker["completion_tokens"] += completion_tokens
    llm_tracker["cached_tokens"] += cached_tokens
    llm_tracker["reasoning_tokens"] += reasoning_tokens
    llm_tracker["total_tokens"] += (
        prompt_tokens + completion_tokens
    )
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "caller": caller,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "cached_tokens": cached_tokens,
        "reasoning_tokens": reasoning_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
    }
    usage_file = _llm_tracker_file.replace("json","jsonl")
    with open(usage_file, "a", encoding="utf-8") as f:
        print("write useage file", usage_file)
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    with open(_llm_tracker_file, "w", encoding="utf-8") as f:
        json.dump(llm_tracker, f, indent=2, ensure_ascii=False)

