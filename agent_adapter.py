#!/usr/bin/env python3
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path


def run(args: list[str]) -> int:
    completed = subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if completed.returncode != 0:
        if completed.stdout:
            print(completed.stdout, end="")
        if completed.stderr:
            print(completed.stderr, end="", file=sys.stderr)
        return completed.returncode
    return 0


def codex(prompt: str) -> int:
    with tempfile.NamedTemporaryFile("r", encoding="utf-8", delete=False) as f:
        output_path = Path(f.name)
    try:
        completed = subprocess.run(
            [
                "codex",
                "exec",
                "--skip-git-repo-check",
                "--color",
                "never",
                "--output-last-message",
                str(output_path),
                prompt,
            ],
            text=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if completed.returncode != 0:
            if completed.stdout:
                print(completed.stdout, end="")
            if completed.stderr:
                print(completed.stderr, end="", file=sys.stderr)
            return completed.returncode
        print(output_path.read_text(encoding="utf-8").strip())
        return 0
    finally:
        output_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("agent", choices=("codex",))
    parser.add_argument("prompt")
    args = parser.parse_args()
    if args.agent == "codex":
        return codex(args.prompt)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
