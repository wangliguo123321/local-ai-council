import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def test_bilingual_readmes() -> None:
    english = ROOT / "README.md"
    chinese = ROOT / "README.zh-CN.md"
    assert english.exists()
    assert chinese.exists()
    english_text = english.read_text(encoding="utf-8")
    chinese_text = chinese.read_text(encoding="utf-8")
    assert "[中文](README.zh-CN.md)" in english_text
    assert "[English](README.md)" in chinese_text
    assert "Agent-native" in english_text
    assert "Agent-native" in chinese_text


def test_agent_manifest() -> None:
    manifest_path = ROOT / "agent.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["name"] == "local-ai-council"
    assert data["kind"] == "local-agent-tool"
    assert data["entrypoints"]["bootstrap"] == "./bootstrap"
    assert data["documentation"]["english"] == "README.md"
    assert data["documentation"]["chinese"] == "README.zh-CN.md"
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
    test_bilingual_readmes()
    test_agent_manifest()
    test_skill_files()
    print("agent-package-tests-ok")


if __name__ == "__main__":
    main()
