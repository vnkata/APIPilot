import json
import sys
from pathlib import Path


def summarize_llm_trackers_locally(api_name: str | None = None):
    # 1. Định nghĩa thư mục gốc để quét
    base_dir = Path("./cache")

    if not base_dir.exists():
        base_dir = Path("./.cache")
        if not base_dir.exists():
            print(
                "❌ Không tìm thấy thư mục './cache' hoặc './.cache'."
            )
            return

    print(f"📁 Thư mục gốc đang quét: {base_dir.resolve()}")

    if api_name:
        print(f"🔍 Chỉ xử lý API: {api_name}")

        candidate_dirs = [
            d
            for d in base_dir.iterdir()
            if d.is_dir() and d.name.startswith(api_name)
        ]
    else:
        candidate_dirs = [
            d for d in base_dir.iterdir() if d.is_dir()
        ]

    processed_count = 0

    metrics = [
        "prompt_tokens",
        "completion_tokens",
        "cached_tokens",
        "reasoning_tokens",
        "total_tokens",
    ]

    for directory in candidate_dirs:
        target_jsonl_path = directory / "llm_tracker.jsonl"

        if not target_jsonl_path.exists():
            continue

        output_json_path = (
            directory / "token_usage_constraints.json"
        )

        local_summary = {}

        try:
            with open(
                target_jsonl_path,
                "r",
                encoding="utf-8",
            ) as f:
                for line in f:
                    line = line.strip()

                    if not line:
                        continue

                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    caller = data.get("caller", "Unknown")

                    if caller not in local_summary:
                        local_summary[caller] = {
                            metric: 0 for metric in metrics
                        }

                    for metric in metrics:
                        local_summary[caller][metric] += (
                            data.get(metric, 0) or 0
                        )

            total_summary = {
                metric: 0 for metric in metrics
            }

            for caller_data in local_summary.values():
                for metric in metrics:
                    total_summary[metric] += caller_data.get(
                        metric, 0
                    )

            local_summary["Total"] = total_summary

            with open(
                output_json_path,
                "w",
                encoding="utf-8",
            ) as json_file:
                json.dump(
                    local_summary,
                    json_file,
                    ensure_ascii=False,
                    indent=4,
                )

            processed_count += 1

            print(
                f"✅ Đã tạo: "
                f"{output_json_path.relative_to(base_dir)}"
            )

        except Exception as e:
            print(
                f"⚠️ Lỗi xử lý file tại "
                f"{target_jsonl_path}: {e}"
            )

    print("\n" + "=" * 60)
    print(
        f"🎉 Hoàn thành! Đã tạo {processed_count} file "
        f"'token_usage_constraints.json'."
    )
    print("=" * 60)


if __name__ == "__main__":
    api_name = sys.argv[1] if len(sys.argv) > 1 else None
    summarize_llm_trackers_locally(api_name)