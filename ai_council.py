#!/usr/bin/env python3
import argparse
import asyncio
import datetime as dt
import json
import shutil
import sys
import uuid
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent

try:
    import yaml
except ImportError:
    yaml = None

KNOWN_AGENT_COMMANDS = {
    "claude": {"command": "claude", "args": ["-p", "{{prompt}}"], "timeout": 120},
    "codex": {"command": "python3", "args": ["agent_adapter.py", "codex", "{{prompt}}"], "timeout": 180},
    "hermes": {"command": "hermes", "args": ["-z", "{{prompt}}"], "timeout": 120},
    "openclaw": {"command": "openclaw", "args": ["infer", "model", "run", "--prompt", "{{prompt}}"], "timeout": 180},
}

EXAMPLE_CONFIG = """summary_agent: claude
output_dir: runs

agents:
  claude:
    command: claude
    args: ["-p", "{{prompt}}"]
    timeout: 120

  codex:
    command: python3
    args: ["agent_adapter.py", "codex", "{{prompt}}"]
    timeout: 180

  hermes:
    command: hermes
    args: ["-z", "{{prompt}}"]
    timeout: 120

  openclaw:
    command: openclaw
    args: ["infer", "model", "run", "--prompt", "{{prompt}}"]
    timeout: 180
"""


@dataclass
class AgentResult:
    name: str
    ok: bool
    stdout: str
    stderr: str
    returncode: int | None
    error: str | None
    duration_seconds: float


@dataclass
class AgentHealth:
    name: str
    status: str
    command: str
    found: bool
    ok: bool
    stdout_excerpt: str
    stderr_excerpt: str
    error: str | None
    duration_seconds: float

@dataclass
class CouncilRound:
    number: int
    prompts: dict[str, str]
    results: list[AgentResult]


def default_config_path() -> Path:
    local = ROOT_DIR / "agents.yaml"
    if local.exists():
        return local
    return Path.home() / ".ai-council.yaml"


def require_yaml() -> None:
    if yaml is None:
        raise RuntimeError("Missing dependency: PyYAML. Install with: pip install -r requirements.txt")


def validate_config(config: dict, config_path: Path) -> None:
    if not isinstance(config, dict):
        raise RuntimeError(f"Config must be a YAML mapping: {config_path}")
    agents = config.get("agents")
    if not isinstance(agents, dict) or not agents:
        raise RuntimeError("Config must define at least one agent under 'agents'.")
    summary_agent = config.get("summary_agent")
    if summary_agent and summary_agent not in agents:
        raise RuntimeError(f"summary_agent not found in agents: {summary_agent}")
    output_dir = config.get("output_dir", "runs")
    if not isinstance(output_dir, str) or not output_dir.strip():
        raise RuntimeError("output_dir must be a non-empty string.")
    for name, agent in agents.items():
        if not isinstance(name, str) or not name.strip():
            raise RuntimeError("Agent names must be non-empty strings.")
        if not isinstance(agent, dict):
            raise RuntimeError(f"Agent '{name}' must be a YAML mapping.")
        command = agent.get("command")
        if not isinstance(command, str) or not command.strip():
            raise RuntimeError(f"Agent '{name}' must define a non-empty command.")
        args = agent.get("args", [])
        if not isinstance(args, list):
            raise RuntimeError(f"Agent '{name}' args must be a list.")
        timeout = agent.get("timeout", 120)
        if not isinstance(timeout, int | float) or timeout <= 0:
            raise RuntimeError(f"Agent '{name}' timeout must be a positive number.")


def load_config(config_path: Path) -> dict:
    require_yaml()
    if not config_path.exists():
        raise RuntimeError(f"Config file not found: {config_path}. Run: ./ai-council init")
    with config_path.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}
    validate_config(config, config_path)
    return config


def discovered_config() -> dict:
    agents = {
        name: spec
        for name, spec in KNOWN_AGENT_COMMANDS.items()
        if shutil.which(spec["command"])
    }
    if not agents:
        agents = {"claude": KNOWN_AGENT_COMMANDS["claude"]}
    summary_agent = "claude" if "claude" in agents else next(iter(agents))
    return {"summary_agent": summary_agent, "output_dir": "runs", "agents": agents}


def write_config(config_path: Path, config: dict) -> None:
    require_yaml()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")


def load_or_create_config(config_path: Path, auto_init: bool) -> dict:
    if config_path.exists():
        return load_config(config_path)
    if not auto_init:
        raise RuntimeError(f"Config file not found: {config_path}. Run: ./ai-council init")
    config = discovered_config()
    write_config(config_path, config)
    print(f"已自动生成配置：{config_path}")
    print("可用智能体：" + ", ".join(config["agents"].keys()))
    return config


def init_config(config_path: Path, force: bool) -> None:
    if config_path.exists() and not force:
        raise RuntimeError(f"Config already exists: {config_path}. Use --force to overwrite.")
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(EXAMPLE_CONFIG, encoding="utf-8")


def render_args(args: list, prompt: str) -> list[str]:
    rendered = []
    for arg in args:
        value = str(arg).replace("{{prompt}}", prompt)
        if value == "agent_adapter.py":
            value = str(ROOT_DIR / value)
        rendered.append(value)
    return rendered


def selected_agents(config: dict, only: list[str] | None, except_: list[str] | None) -> dict:
    agents = dict(config["agents"])
    if only:
        missing = [name for name in only if name not in agents]
        if missing:
            raise RuntimeError(f"Unknown agent(s): {', '.join(missing)}")
        agents = {name: agents[name] for name in only}
    if except_:
        agents = {name: agent for name, agent in agents.items() if name not in except_}
    if not agents:
        raise RuntimeError("No agents selected.")
    return agents


async def run_agent(name: str, agent: dict, prompt: str) -> AgentResult:
    start = asyncio.get_running_loop().time()
    command = str(agent.get("command", "")).strip()
    args = render_args(agent.get("args", []), prompt)
    timeout = float(agent.get("timeout", 120))

    if not command:
        return AgentResult(name, False, "", "", None, "Missing command", 0.0)
    if shutil.which(command) is None:
        return AgentResult(name, False, "", "", None, f"Command not found: {command}", 0.0)

    try:
        process = await asyncio.create_subprocess_exec(
            command,
            *args,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            duration = asyncio.get_running_loop().time() - start
            return AgentResult(name, False, "", "", None, f"Timed out after {timeout:g}s", duration)

        stdout = stdout_bytes.decode("utf-8", errors="replace").strip()
        stderr = stderr_bytes.decode("utf-8", errors="replace").strip()
        duration = asyncio.get_running_loop().time() - start
        ok = process.returncode == 0
        error = None if ok else f"Exited with code {process.returncode}"
        return AgentResult(name, ok, stdout, stderr, process.returncode, error, duration)
    except Exception as exc:
        duration = asyncio.get_running_loop().time() - start
        return AgentResult(name, False, "", "", None, str(exc), duration)


async def run_all_agents(agents: dict, prompt: str) -> list[AgentResult]:
    tasks = [run_agent(name, agent, prompt) for name, agent in agents.items()]
    return await asyncio.gather(*tasks)


async def run_agent_prompts(agents: dict, prompts: dict[str, str]) -> list[AgentResult]:
    tasks = [run_agent(name, agent, prompts[name]) for name, agent in agents.items()]
    return await asyncio.gather(*tasks)


def render_round_transcript(rounds: list[CouncilRound]) -> str:
    sections = []
    for council_round in rounds:
        sections.append(f"# 第 {council_round.number} 轮")
        for result in council_round.results:
            status = "success" if result.ok else f"failed: {result.error}"
            output = result.stdout or result.stderr or "(no output)"
            sections.append(f"## {result.name}\nStatus: {status}\n\n{output}")
    return "\n\n".join(sections)


def build_calibration_prompt(question: str, agent_name: str, previous_rounds: list[CouncilRound], guidance: str | None = None) -> str:
    transcript = render_round_transcript(previous_rounds)
    guidance_section = f"\n本轮用户额外指导：{guidance}\n" if guidance else ""
    return f"""你是多 AI council 中的智能体：{agent_name}。

原始问题：{question}
{guidance_section}
下面是所有智能体前面轮次的回答：

{transcript}

现在请你进入“串供/互相校准”模式：
- 先吸收其他智能体的有效观点。
- 如果你上一轮有遗漏、错误或表达不准，请修正。
- 如果其他智能体说得不对，不要盲从，请明确指出。
- 区分共识、分歧、证据强弱和仍不确定的地方。
- 不要为了形成一致而掩盖少数派但有价值的观点。

请按以下结构输出：
## 接受的观点

## 不同意或需要降级的观点

## 新增或修正的判断

## 校准后的最终回答

## 仍不确定的地方

## 置信度
请用“高 / 中 / 低”表示，并简要说明原因。
"""


def print_round(question: str, council_round: CouncilRound) -> None:
    print(format_text_report(question, [council_round], None, None, include_summary=False))
    print("", flush=True)


def next_round_guidance(next_round: int) -> str | None:
    print(f"继续第 {next_round} 轮串供/校准？")
    print("- 直接回车：停止")
    print("- 输入 y：继续")
    print("- 输入一句话：带着这句指导继续")
    answer = input("> ").strip()
    if not answer or answer.lower() in {"n", "no", "stop", "停止"}:
        return None
    if answer.lower() in {"y", "yes", "继续"}:
        return ""
    return answer


def build_initial_prompt(question: str, agent_name: str) -> str:
    return f"""你是多 AI council 中的智能体：{agent_name}。

请先独立回答用户问题，不要假设其他智能体会补充你遗漏的内容。

原始问题：{question}

请按以下结构输出：
## 结论

## 主要依据

## 不确定点

## 反对意见或风险

## 建议

## 置信度
请用“高 / 中 / 低”表示，并简要说明原因。
"""


async def run_council(agents: dict, question: str, rounds_count: int, ask_each_round: bool = False) -> list[CouncilRound]:
    if rounds_count < 1:
        raise RuntimeError("--rounds must be at least 1.")

    council_rounds = []
    first_prompts = {name: build_initial_prompt(question, name) for name in agents}
    first_results = await run_agent_prompts(agents, first_prompts)
    council_rounds.append(CouncilRound(1, first_prompts, first_results))

    if ask_each_round:
        print_round(question, council_rounds[-1])

    round_number = 2
    while round_number <= rounds_count:
        guidance = ""
        if ask_each_round:
            guidance = next_round_guidance(round_number)
            if guidance is None:
                break
        prompts = {name: build_calibration_prompt(question, name, council_rounds, guidance) for name in agents}
        results = await run_agent_prompts(agents, prompts)
        council_rounds.append(CouncilRound(round_number, prompts, results))
        if ask_each_round:
            print_round(question, council_rounds[-1])
        round_number += 1

    return council_rounds


def build_summary_prompt(question: str, rounds: list[CouncilRound]) -> str:
    transcript = render_round_transcript(rounds)
    return f"""你是最终答案合成器兼质量审查员。请基于多个 AI 智能体对同一个问题的多轮独立回答、互相校准与用户补充指导，产出一份面向原问题的最终高质量回答。

原始问题：{question}

多轮回答记录：

{transcript}

你的目标不是简单总结谁说了什么，而是给用户一份尽可能完善、准确、可直接使用、可审计的最终答案。

要求：
1. 直接回答原始问题。
2. 综合各模型的有效观点，去掉重复、空话和明显不可靠内容。
3. 明确区分共识、分歧、少数派观点和证据强弱。
4. 如果各模型有冲突，选择更有依据的一方，并说明为什么。
5. 对没有足够证据的判断要降级表达，不要装作确定。
6. 检查是否答非所问、是否有无依据断言、是否遗漏用户要求。
7. 如果问题涉及用户本人偏好、习惯或怪癖，请区分“较有把握”“可能存在”“需要更多证据”。

请按以下结构输出：
# 最终串供答案

## 结论

## 主要依据

## 共识

## 分歧与少数派观点

## 质量审查
说明是否存在答非所问、无依据断言、遗漏要求或需要降级的判断。

## 仍不确定或需要更多证据的地方

## 置信度
请用“高 / 中 / 低”表示，并简要说明原因。

## 如果要继续追问，最值得问的问题
"""


async def summarize(config: dict, question: str, rounds: list[CouncilRound]) -> AgentResult | None:
    summary_agent_name = config.get("summary_agent")
    if not summary_agent_name:
        return None
    agent = config["agents"].get(summary_agent_name)
    if not agent:
        return AgentResult(summary_agent_name, False, "", "", None, "summary_agent not found in agents", 0.0)
    return await run_agent(summary_agent_name, agent, build_summary_prompt(question, rounds))


def report_data(
    question: str,
    rounds: list[CouncilRound],
    summary: AgentResult | None,
    run_dir: Path | None,
    effective_question: str | None = None,
    history_context: str = "",
) -> dict:
    return {
        "question": question,
        "original_question": question,
        "effective_question": effective_question or question,
        "history_context": history_context,
        "run_dir": str(run_dir) if run_dir else None,
        "rounds": [
            {
                "number": council_round.number,
                "prompts": council_round.prompts,
                "results": [asdict(result) for result in council_round.results],
            }
            for council_round in rounds
        ],
        "final_results": [asdict(result) for result in rounds[-1].results] if rounds else [],
        "summary": asdict(summary) if summary else None,
        "final_answer": asdict(summary) if summary else None,
    }


def append_result(lines: list[str], result: AgentResult) -> None:
    if result.ok:
        lines.append(result.stdout or "(无输出)")
    else:
        lines.append(f"调用失败：{result.error}")
        if result.stderr:
            lines.append(result.stderr)


def format_text_report(question: str, rounds: list[CouncilRound], summary: AgentResult | None, run_dir: Path | None, include_summary: bool = True) -> str:
    lines = [f"问题：{question}", "", f"Council 轮次：{len(rounds)}", ""]
    for council_round in rounds:
        title = "第 1 轮：独立回答" if council_round.number == 1 else f"第 {council_round.number} 轮：串供/校准"
        lines.append(f"=== {title} ===")
        lines.append("调用状态：")
        for result in council_round.results:
            status = "成功" if result.ok else f"失败（{result.error}）"
            lines.append(f"- {result.name}: {status}, {result.duration_seconds:.2f}s")
        lines.append("")
        for result in council_round.results:
            lines.append(f"--- {result.name} ---")
            append_result(lines, result)
            lines.append("")

    if include_summary:
        lines.append("=== 最终串供答案 ===")
        append_summary(lines, summary)
        if run_dir:
            lines.extend(["", f"原始结果已保存到：{run_dir}"])
    return "\n".join(lines)


def format_markdown_report(question: str, rounds: list[CouncilRound], summary: AgentResult | None, run_dir: Path | None) -> str:
    lines = ["# ai-council 串供/校准报告", "", f"**问题：** {question}", "", f"**Council 轮次：** {len(rounds)}", ""]
    for council_round in rounds:
        title = "第 1 轮：独立回答" if council_round.number == 1 else f"第 {council_round.number} 轮：串供/校准"
        lines.extend([f"## {title}", "", "### 调用状态"])
        for result in council_round.results:
            status = "成功" if result.ok else f"失败：{result.error}"
            lines.append(f"- **{result.name}**：{status}，{result.duration_seconds:.2f}s")
        lines.append("")
        for result in council_round.results:
            lines.extend([f"### {result.name}", ""])
            append_result(lines, result)
            lines.append("")

    lines.extend(["## 最终串供答案", ""])
    append_summary(lines, summary)
    if run_dir:
        lines.extend(["", f"原始结果已保存到：`{run_dir}`"])
    return "\n".join(lines)


def append_summary(lines: list[str], summary: AgentResult | None) -> None:
    if summary is None:
        lines.append("未生成最终合成答案；请参考最后一轮各智能体的校准后回答。")
    elif summary.ok:
        lines.append(summary.stdout or "(最终答案智能体无输出)")
    else:
        lines.append(f"最终答案生成失败：{summary.error}")
        if summary.stderr:
            lines.append(summary.stderr)


def format_report(format_: str, question: str, rounds: list[CouncilRound], summary: AgentResult | None, run_dir: Path | None) -> str:
    if format_ == "json":
        return json.dumps(report_data(question, rounds, summary, run_dir), ensure_ascii=False, indent=2)
    if format_ == "markdown":
        return format_markdown_report(question, rounds, summary, run_dir)
    return format_text_report(question, rounds, summary, run_dir)


def safe_name(name: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in name)


def new_run_dir(output_dir: Path) -> Path:
    for _ in range(10):
        timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:-3]
        run_dir = output_dir / f"{timestamp}-{uuid.uuid4().hex[:6]}"
        try:
            run_dir.mkdir(parents=True, exist_ok=False)
            return run_dir
        except FileExistsError:
            continue
    raise RuntimeError("Could not create unique run directory.")


def save_run(
    output_dir: Path,
    question: str,
    rounds: list[CouncilRound],
    summary: AgentResult | None,
    effective_question: str | None = None,
    history_context: str = "",
) -> Path:
    run_dir = new_run_dir(output_dir)

    (run_dir / "question.txt").write_text(question, encoding="utf-8")
    for council_round in rounds:
        for result in council_round.results:
            prefix = f"round-{council_round.number:02d}.{safe_name(result.name)}"
            (run_dir / f"{prefix}.prompt.txt").write_text(council_round.prompts[result.name], encoding="utf-8")
            (run_dir / f"{prefix}.stdout.txt").write_text(result.stdout, encoding="utf-8")
            (run_dir / f"{prefix}.stderr.txt").write_text(result.stderr, encoding="utf-8")
    if summary is not None:
        final_prompt = build_summary_prompt(question, rounds)
        (run_dir / "summary.prompt.txt").write_text(final_prompt, encoding="utf-8")
        (run_dir / "summary.stdout.txt").write_text(summary.stdout, encoding="utf-8")
        (run_dir / "summary.stderr.txt").write_text(summary.stderr, encoding="utf-8")
        (run_dir / "final-answer.prompt.txt").write_text(final_prompt, encoding="utf-8")
        (run_dir / "final-answer.md").write_text(summary.stdout, encoding="utf-8")

    (run_dir / "result.json").write_text(
        json.dumps(report_data(question, rounds, summary, run_dir, effective_question, history_context), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (run_dir / "report.md").write_text(format_markdown_report(question, rounds, summary, run_dir), encoding="utf-8")
    return run_dir


def config_output_dir(config: dict) -> Path:
    path = Path(config.get("output_dir", "runs"))
    if not path.is_absolute():
        path = ROOT_DIR / path
    return path


def parse_csv(value: str | None) -> list[str] | None:
    if not value:
        return None
    return [item.strip() for item in value.split(",") if item.strip()]


def read_question(args: argparse.Namespace) -> str:
    if args.stdin:
        question = sys.stdin.read().strip()
    else:
        if args.words and args.words[0] in {"ask", "串供"}:
            words = args.words[1:]
        else:
            words = args.words
        question = " ".join(words).strip()
        if not question and sys.stdin.isatty():
            question = input("你想问什么？\n> ").strip()
    if not question:
        raise RuntimeError("Question is required. Pass it as an argument or use --stdin.")
    return question


async def check_agent_health(name: str, agent: dict, timeout: float = 20) -> AgentHealth:
    command = str(agent.get("command", "")).strip()
    found = bool(command and shutil.which(command))
    if not found:
        return AgentHealth(name, "command_missing", command, False, False, "", "", f"Command not found: {command}", 0.0)
    checked_agent = dict(agent)
    checked_agent["timeout"] = min(float(agent.get("timeout", timeout)), timeout)
    result = await run_agent(name, checked_agent, "只输出 OK，不要输出其他内容。")
    stdout_excerpt = result.stdout[:200]
    stderr_excerpt = result.stderr[:200]
    if not result.ok:
        if result.error and result.error.startswith("Timed out"):
            status = "timeout"
        else:
            status = "failed"
    elif not result.stdout.strip():
        status = "empty_output"
    else:
        status = "ok"
    return AgentHealth(name, status, command, True, status == "ok", stdout_excerpt, stderr_excerpt, result.error, result.duration_seconds)


async def doctor_agents(config: dict, only: list[str] | None = None, except_: list[str] | None = None) -> list[AgentHealth]:
    agents = selected_agents(config, only, except_)
    return await asyncio.gather(*(check_agent_health(name, agent) for name, agent in agents.items()))


def print_doctor_report(items: list[AgentHealth]) -> None:
    for item in items:
        print(f"{item.name}: {item.status} ({item.duration_seconds:.2f}s)")
        print(f"  command: {item.command or '(missing)'}")
        if item.error:
            print(f"  error: {item.error}")
        if item.stdout_excerpt:
            print(f"  stdout: {item.stdout_excerpt}")
        if item.stderr_excerpt:
            print(f"  stderr: {item.stderr_excerpt}")


def print_agent_list(config: dict) -> None:
    summary_agent = config.get("summary_agent")
    for name, agent in config["agents"].items():
        marker = " summary" if name == summary_agent else ""
        command = agent.get("command", "")
        args = " ".join(str(arg) for arg in agent.get("args", []))
        timeout = agent.get("timeout", 120)
        found = "found" if command and shutil.which(str(command)) else "missing"
        print(f"{name}{marker}: {command} {args} timeout={timeout}s [{found}]")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ask multiple local AI agents, let them see each other, and aggregate calibrated answers.",
        epilog="Commands: init, list, doctor, ask, 串供. You can also pass a question directly.",
    )
    parser.add_argument("words", nargs="*", help="Command or question")
    parser.add_argument("--config", default=str(default_config_path()), help="Path to YAML config file")
    parser.add_argument("--force", action="store_true", help="Overwrite existing config when using init")
    parser.add_argument("--only", help="Comma-separated agent names to include")
    parser.add_argument("--except", dest="except_", help="Comma-separated agent names to exclude")
    parser.add_argument("--stdin", action="store_true", help="Read question from stdin")
    parser.add_argument("--no-summary", action="store_true", help="Skip summary generation")
    parser.add_argument("--no-save", action="store_true", help="Do not save run files")
    parser.add_argument("--format", choices=("text", "markdown", "json"), default="text", help="Output format")
    parser.add_argument("--rounds", type=int, default=1, help="Maximum council rounds. 1 = independent answers only; 2+ = mutual calibration")
    parser.add_argument("--council", action="store_true", help="Enable calibration ability. Shortcut for at least --rounds 2")
    parser.add_argument("--ask-each-round", action="store_true", help="After each round, ask whether to run another calibration round")
    parser.add_argument("--final-only", action="store_true", help="Print only the final synthesized answer")
    parser.add_argument("--dry-run", action="store_true", help="Print selected agents and question without calling agents")
    return parser


def command_name(args: argparse.Namespace) -> str:
    if args.words and args.words[0] in {"init", "list", "doctor", "ask", "串供"}:
        return args.words[0]
    return "ask"


async def handle_ask(args: argparse.Namespace, shortcut_council: bool = False) -> int:
    config = load_or_create_config(Path(args.config), auto_init=shortcut_council)
    question = read_question(args)
    agents = selected_agents(config, parse_csv(args.only), parse_csv(args.except_))
    if args.dry_run:
        print(f"问题：{question}")
        print("将调用智能体：" + ", ".join(agents.keys()))
        return 0
    if shortcut_council:
        args.ask_each_round = True
        args.rounds = max(args.rounds, 5)
    rounds_count = max(args.rounds, 2) if args.council or args.ask_each_round else args.rounds
    rounds = await run_council(agents, question, rounds_count, ask_each_round=args.ask_each_round)
    summary = None if args.no_summary else await summarize(config, question, rounds)
    run_dir = None if args.no_save else save_run(config_output_dir(config), question, rounds, summary)
    if args.final_only:
        summary_lines = []
        append_summary(summary_lines, summary)
        print("\n".join(summary_lines))
    elif args.ask_each_round and args.format == "text":
        print("=== 最终串供答案 ===")
        summary_lines = []
        append_summary(summary_lines, summary)
        print("\n".join(summary_lines))
        if run_dir:
            print(f"\n原始结果已保存到：{run_dir}")
    else:
        print(format_report(args.format, question, rounds, summary, run_dir))
    return 0 if any(result.ok for result in rounds[-1].results) else 1


async def main_async() -> int:
    parser = build_parser()
    args, unknown = parser.parse_known_args()
    if any(item.startswith("-") for item in unknown):
        parser.error(f"unrecognized arguments: {' '.join(unknown)}")
    args.words.extend(unknown)
    command = command_name(args)

    try:
        if command == "init":
            config_path = Path(args.config if args.config != str(default_config_path()) else "agents.yaml")
            init_config(config_path, args.force)
            print(f"Config written to: {config_path}")
            return 0
        if command == "list":
            print_agent_list(load_config(Path(args.config)))
            return 0
        if command == "doctor":
            items = await doctor_agents(load_config(Path(args.config)), parse_csv(args.only), parse_csv(args.except_))
            print_doctor_report(items)
            return 0 if all(item.ok for item in items) else 1
        return await handle_ask(args, shortcut_council=command == "串供")
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


def main() -> None:
    raise SystemExit(asyncio.run(main_async()))


if __name__ == "__main__":
    main()
