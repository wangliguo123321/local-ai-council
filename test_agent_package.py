import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def test_agent_manifest() -> None:
    manifest_path = ROOT / "agent.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["name"] == "local-ai-council"
    assert data["kind"] == "local-agent-tool"
    assert data["entrypoints"]["bootstrap"] == "./bootstrap"
    assert "doctor" in data["entrypoints"]
    assert "ask" in data["entrypoints"]
    assert "runs/" in data["configuration"]["sensitive_files"]


SCRIPT_NAMES = ["bootstrap", "check", "doctor", "ask", "gui"]


def test_skill_files() -> None:
    skill_dir = ROOT / "skills" / "local-ai-council"
    skill = skill_dir / "SKILL.md"
    assert skill.exists()
    text = skill.read_text(encoding="utf-8")
    assert "./ai-council" in text
    assert "./check" in text
    for name in SCRIPT_NAMES:
        script = skill_dir / "scripts" / name
        assert script.exists()
        assert script.read_text(encoding="utf-8").startswith("#!/usr/bin/env bash")


def main() -> None:
    test_agent_manifest()
    test_skill_files()
    print("agent-package-tests-ok")


if __name__ == "__main__":
    main()
