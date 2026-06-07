import asyncio
import json
import tempfile
from pathlib import Path

import yaml

from ai_council import (
    AgentResult,
    CouncilRound,
    build_calibration_prompt,
    build_initial_prompt,
    build_summary_prompt,
    doctor_agents,
    load_config,
    run_council,
    save_run,
)


def test_config_validation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "bad.yaml"
        path.write_text("summary_agent: missing\nagents:\n  a:\n    command: python3\n", encoding="utf-8")
        try:
            load_config(path)
        except RuntimeError as exc:
            assert "summary_agent not found" in str(exc)
        else:
            raise AssertionError("invalid summary_agent should fail")

        path.write_text(
            yaml.safe_dump(
                {
                    "summary_agent": "a",
                    "output_dir": "runs",
                    "agents": {"a": {"command": "python3", "args": [], "timeout": 3}},
                },
                allow_unicode=True,
            ),
            encoding="utf-8",
        )
        assert load_config(path)["summary_agent"] == "a"


def test_structured_prompts() -> None:
    initial = build_initial_prompt("问题", "a")
    assert "## 结论" in initial
    assert "## 置信度" in initial

    rounds = [CouncilRound(1, {"a": initial}, [AgentResult("a", True, "## 结论\n答案", "", 0, None, 0.1)])]
    calibration = build_calibration_prompt("问题", "a", rounds, "补充")
    assert "## 接受的观点" in calibration
    assert "## 校准后的最终回答" in calibration

    summary = build_summary_prompt("问题", rounds)
    assert "## 分歧与少数派观点" in summary
    assert "## 质量审查" in summary


def test_unique_save_run() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp)
        result = AgentResult("a", True, "ok", "", 0, None, 0.1)
        rounds = [CouncilRound(1, {"a": "prompt"}, [result])]
        first = save_run(output_dir, "问题", rounds, result)
        second = save_run(output_dir, "问题", rounds, result)
        assert first != second
        assert (first / "result.json").exists()
        data = json.loads((first / "result.json").read_text(encoding="utf-8"))
        assert data["question"] == "问题"


def test_fake_agent_flow() -> None:
    async def run() -> None:
        agents = {
            "a": {
                "command": "python3",
                "args": ["-c", "import sys; print('ok:' + sys.argv[1][:20])", "{{prompt}}"],
                "timeout": 5,
            }
        }
        rounds = await run_council(agents, "测试问题", 2)
        assert len(rounds) == 2
        assert all(result.ok for council_round in rounds for result in council_round.results)
        assert "## 结论" in rounds[0].prompts["a"]
        assert "## 接受的观点" in rounds[1].prompts["a"]

    asyncio.run(run())


def test_doctor_agents() -> None:
    async def run() -> None:
        config = {
            "summary_agent": "a",
            "output_dir": "runs",
            "agents": {
                "a": {
                    "command": "python3",
                    "args": ["-c", "print('OK')"],
                    "timeout": 5,
                }
            },
        }
        items = await doctor_agents(config)
        assert len(items) == 1
        assert items[0].ok
        assert items[0].status == "ok"

    asyncio.run(run())


def main() -> None:
    test_config_validation()
    test_structured_prompts()
    test_unique_save_run()
    test_fake_agent_flow()
    test_doctor_agents()
    print("core-tests-ok")


if __name__ == "__main__":
    main()
