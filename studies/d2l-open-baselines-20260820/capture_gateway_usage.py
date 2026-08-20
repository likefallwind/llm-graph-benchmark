from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.request import Request, urlopen


def read_secret(path: Path, name: str) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key, value = stripped.split("=", 1)
            if key.strip() == name:
                return value.strip().strip("'\"").split(",", 1)[0].strip()
    raise ValueError(f"{name} is not set in {path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--api-key-file", type=Path, required=True)
    parser.add_argument("--api-key-name", default="GATEWAY_KEYS")
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    token = read_secret(args.api_key_file, args.api_key_name)
    endpoint = args.base_url.removesuffix("/v1").rstrip("/") + "/stats"
    request = Request(endpoint, headers={"Authorization": f"Bearer {token}"})
    with urlopen(request, timeout=30) as response:
        stats = json.load(response)

    totals = stats.get("totals", {})
    submission = json.loads(args.submission.read_text(encoding="utf-8"))
    runtime = submission.setdefault("runtime", {})
    runtime["input_tokens"] = int(totals.get("prompt_tokens", 0))
    runtime["output_tokens"] = int(totals.get("completion_tokens", 0))
    metadata = submission.setdefault("metadata", {})
    metadata["gateway_usage_accounting"] = {
        "isolation": "dedicated gateway process and empty stats file",
        "requests": int(totals.get("requests", 0)),
        "reasoning_tokens": int(totals.get("reasoning_tokens", 0)),
        "actual_models": sorted(stats.get("models", {})),
        "cost_accounting": "subscription plan; no per-request USD estimate",
    }

    args.submission.write_text(
        json.dumps(submission, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
