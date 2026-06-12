import csv
import json
import sys
from pathlib import Path


def convert_each_json_individually(api_name: str | None = None):
    # 1. Định nghĩa thư mục gốc để quét
    base_dir = Path("./cache")

    headers = [
        "method",
        "property",
        "spec",
        "runtime",
        "final",
        "type",
        "tp",
        "fp",
    ]

    # Fallback sang .cache
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
        candidate_dirs = [d for d in base_dir.iterdir() if d.is_dir()]

    processed_count = 0

    for directory in candidate_dirs:
        target_json_path = directory / "constraint_miner.json"

        if not target_json_path.exists():
            continue

        output_csv_path = directory / "constraint_miner.csv"

        try:
            with open(target_json_path, "r", encoding="utf-8") as f:
                json_data = json.load(f)

            with open(
                output_csv_path,
                mode="w",
                encoding="utf-8",
                newline="",
            ) as csv_file:
                writer = csv.DictWriter(
                    csv_file,
                    fieldnames=headers,
                )
                writer.writeheader()

                for method, properties in json_data.items():
                    for property_path, details in properties.items():
                        writer.writerow(
                            {
                                "method": method,
                                "property": property_path,
                                "spec": details.get("spec"),
                                "runtime": details.get("runtime"),
                                "final": details.get("final"),
                                "type": details.get("type"),
                                "tp": "",
                                "fp": "",
                            }
                        )

            processed_count += 1

            print(
                f"✅ Đã xử lý xong: "
                f"{directory.relative_to(base_dir)}/constraint_miner.csv"
            )

        except Exception as e:
            print(
                f"⚠️ Lỗi xử lý file tại "
                f"{target_json_path}: {e}"
            )

    print("\n" + "=" * 50)
    print(
        f"🎉 Hoàn thành! Tổng cộng đã xử lý {processed_count} folder."
    )
    print("=" * 50)


if __name__ == "__main__":
    api_name = sys.argv[1] if len(sys.argv) > 1 else None
    convert_each_json_individually(api_name)