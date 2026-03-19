

import json
import os


llm_tracker = {
    "total_tokens": 0,
    "prompt_tokens": 0,
    "completion_tokens": 0
}
_llm_tracker_file = "./llm_tracker.json"


def initTracker(dir: str|None = None, model: str|None = None) :
    global _llm_tracker_file, llm_tracker
    _llm_tracker_file = os.path.join(dir, f"{model}_usages.json")

    # nếu file tồn tại thì load
    if os.path.exists(_llm_tracker_file):
        try:
            with open(_llm_tracker_file, "r", encoding="utf-8") as f:
                llm_tracker = json.load(f)
        except Exception:
            llm_tracker = {
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0
        }
    else:
        llm_tracker ={
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0
        }

    with open(_llm_tracker_file, "w", encoding="utf-8") as f:
        json.dump(llm_tracker, f, indent=2, ensure_ascii=False)


def add_usage(prompt_tokens: int, completion_tokens: int):
    global llm_tracker, _llm_tracker_file

    llm_tracker["prompt_tokens"] += prompt_tokens
    llm_tracker["completion_tokens"] += completion_tokens
    llm_tracker["total_tokens"] += (prompt_tokens + completion_tokens)
    with open(_llm_tracker_file, "w", encoding="utf-8") as f:
        json.dump(llm_tracker, f, indent=2, ensure_ascii=False)

    
