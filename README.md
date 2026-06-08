# Local AI Council / 串供

> Local-first multi-agent council for independent answers, calibration, synthesis, and audit trails.

Local AI Council lets you ask one question once, send it to multiple local AI CLIs, compare their independent answers, run calibration rounds, and produce a final synthesized answer with full local records.

It is **not** a neural-network Mixture of Experts implementation. It is a lightweight orchestration tool for local AI agents.

## For coding agents reading this repo

Start here:

1. Read this README for product intent and user-facing workflows.
2. Read [AGENTS.md](AGENTS.md) for implementation map, safety rules, and agent-specific guidance.
3. Read [agent.json](agent.json) for machine-readable install/run/check entrypoints.
4. Run `./check` before and after changes.
5. Do not commit local configs, run outputs, memory files, `.env` files, or generated artifacts.

Main files:

| File | Purpose |
| --- | --- |
| `ai_council.py` | Core CLI, config, subprocess agent calls, prompt protocol, reports, `doctor` |
| `web_app.py` | FastAPI backend for GUI, sessions, history, memory, Web safety checks |
| `web_static/index.html` | Single-file browser UI |
| `agent_adapter.py` | Non-interactive adapters for CLIs that need special handling |
| `agents.yaml.example` | Example local agent configuration |
| `agent.json` | Machine-readable manifest for agents: install, check, ask, GUI, outputs, safety |
| `skills/local-ai-council/SKILL.md` | Skill-style instructions for agents that support local skills |
| `test_core.py` | Core tests that do not require real AI CLIs |
| `test_web.py` | Web/API/security/context regression tests |
| `bootstrap` | One-command setup for new users |
| `check` | Local pre-commit self-check |
| `preflight` | GitHub safety scan for obvious local/private content |

## What problem this solves

Using one AI model for important work is fragile:

- it can be confident but wrong;
- it may miss edge cases;
- it usually gives one perspective;
- it may not expose uncertainty;
- its reasoning process is hard to audit later.

Local AI Council turns your existing local AI tools into a review committee:

1. **Independent round** — each agent answers without seeing the others.
2. **Calibration rounds** — agents see prior answers and can accept, reject, or revise.
3. **Final synthesis** — a summary agent produces a structured final answer.
4. **Audit trail** — prompts, outputs, errors, timings, reports, and final answers are saved locally.

Useful for:

- architecture review;
- code review;
- technical decisions;
- product decisions;
- research and comparison;
- debugging plans;
- multi-model answer verification;
- personal AI workflow experiments.

## Current status

Current stage: **v0.2 / Alpha**.

Works today:

- CLI and local Web GUI;
- multiple local AI CLIs via `agents.yaml`;
- independent first round;
- optional multi-round calibration;
- structured final synthesis;
- `doctor` command to verify real agent usability;
- history and lightweight memory;
- local saved reports;
- no-real-agent test suite.

Known limitations:

- memory is still simple keyword-style recall;
- long multi-round runs can still grow large because full transcripts are used;
- GUI is usable but not polished;
- remote hosting is not supported; use locally on `127.0.0.1`;
- future v0.3 should introduce RoundDigest / CouncilState to reduce context growth.

## Quick start

### 1. Clone

```bash
git clone <repo-url>
cd local-ai-council
```

If your local directory still uses another name, just `cd` into that directory.

### 2. Bootstrap

```bash
./bootstrap
```

This creates a virtual environment, installs dependencies, sets script permissions, creates a default config if needed, and runs local checks.

Manual setup:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
chmod +x ai-council 串供 gui check bootstrap preflight
./check
```

### 3. Check configured agents

```bash
./ai-council list
./ai-council doctor
```

`list` checks whether commands exist in `PATH`.

`doctor` actually calls each agent with a short prompt and reports:

| Status | Meaning |
| --- | --- |
| `ok` | Agent produced output successfully |
| `command_missing` | Command not found |
| `timeout` | Agent did not finish in time |
| `empty_output` | Command succeeded but returned no output |
| `failed` | Non-zero exit or execution error |

### 4. Run the GUI

```bash
./gui
```

Open:

```text
http://127.0.0.1:7860
```

macOS users can also double-click:

```text
打开串供.command
```

### 5. Ask from CLI

One independent round:

```bash
./ai-council "What should this project improve next?"
```

Interactive council mode:

```bash
./串供 "What should this project improve next?"
```

Fixed 3-round run:

```bash
./ai-council "What should this project improve next?" --rounds 3
```

Only print final synthesis:

```bash
./ai-council "What should this project improve next?" --rounds 3 --final-only
```

## Agent-native usage

This repo is intended to be usable by both humans and coding agents. Agents should prefer the machine-readable entrypoints instead of guessing commands from prose.

### Machine-readable manifest

[`agent.json`](agent.json) describes:

- what this tool does;
- how to bootstrap, check, ask, run doctor, and launch the GUI;
- where outputs are saved;
- which files are sensitive and must not be published;
- local safety boundaries.

A coding agent can run the standard flow:

```bash
./bootstrap
./check
./ai-council doctor
./ai-council "What should this project improve next?" --rounds 2 --final-only
```

### Skill-style package

[`skills/local-ai-council/SKILL.md`](skills/local-ai-council/SKILL.md) provides a skill-style wrapper for agents that support local skills. Helper scripts live under `skills/local-ai-council/scripts/`:

```bash
skills/local-ai-council/scripts/check
skills/local-ai-council/scripts/doctor
skills/local-ai-council/scripts/ask "What should this project improve next?" 2
skills/local-ai-council/scripts/gui
```

### MCP vs Skills

The current repo ships a skill-style interface first because it is simple, local, clone-friendly, and requires no long-running protocol server. MCP is a good next layer when agents need stable tool calls such as `ask_council`, `doctor_agents`, `list_runs`, and `read_run` across multiple clients.

Recommended path:

1. Use `agent.json` + `skills/local-ai-council/` for immediate agent discovery and execution.
2. Add an MCP server when the CLI/GUI behavior stabilizes enough to expose as typed tools.
3. Keep the CLI as the source of truth so humans, skills, and MCP share one implementation.

## GUI features

The GUI supports:

- real agent health checks;
- question input;
- agent selection;
- independent first-round answers;
- multi-round calibration;
- collapsible long rounds;
- copy buttons for each agent answer and final answer;
- final synthesis;
- history list and detail view;
- selected history as context for new questions;
- lightweight memory injection;
- local report saving.

## Configuration

Default config lookup order:

1. project-local `agents.yaml`;
2. `~/.ai-council.yaml`.

`agents.yaml` is intentionally ignored by git because it may reveal local commands, paths, or private setup details.

Example:

```yaml
summary_agent: claude
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
```

Field meanings:

| Field | Meaning |
| --- | --- |
| `summary_agent` | Agent used for final synthesis; must exist in `agents` |
| `output_dir` | Local run directory; relative paths resolve from project root |
| `command` | Local executable |
| `args` | Argument array; `{{prompt}}` is replaced with the prompt |
| `timeout` | Per-agent timeout in seconds |

The project executes commands as argument arrays and does not use `shell=True` for user prompts.

## Adding a new agent

Add an entry to `agents.yaml`:

```yaml
agents:
  my_agent:
    command: my-ai-cli
    args: ["run", "--prompt", "{{prompt}}"]
    timeout: 120
```

Then verify:

```bash
./ai-council doctor --only my_agent
```

A good agent command should:

- run non-interactively;
- accept the prompt as an argument;
- write the final answer to stdout;
- return non-zero on failure;
- not wait for terminal stdin.

If a CLI needs special output cleanup, add an adapter in `agent_adapter.py` and test it with `doctor`.

## Prompt protocol

First round asks each agent for:

- conclusion;
- main evidence;
- uncertainty;
- objections or risks;
- recommendation;
- confidence.

Calibration rounds ask each agent for:

- accepted points;
- rejected or downgraded points;
- new or corrected judgment;
- calibrated final answer;
- remaining uncertainty;
- confidence.

Final synthesis asks for:

- conclusion;
- main evidence;
- consensus;
- disagreements and minority views;
- quality review;
- remaining uncertainty;
- confidence;
- best next question.

## Saved data

Runs are saved under:

```text
runs/YYYYMMDD-HHMMSS-mmm-xxxxxx/
```

Typical files:

- `question.txt`
- `round-01.<agent>.prompt.txt`
- `round-01.<agent>.stdout.txt`
- `round-01.<agent>.stderr.txt`
- `summary.prompt.txt`
- `summary.stdout.txt`
- `summary.stderr.txt`
- `final-answer.prompt.txt`
- `final-answer.md`
- `result.json`
- `report.md`

Lightweight GUI memory is saved under:

```text
council_memory/memories.jsonl
```

Both `runs/` and `council_memory/` are gitignored.

## Tests and pre-upload checks

Run before commits or uploads:

```bash
./check
```

This runs:

```bash
python -m py_compile ai_council.py web_app.py agent_adapter.py test_core.py test_web.py
python test_core.py
python test_web.py
./preflight
```

`preflight` checks for obvious local/private content such as local user paths, common key names, private key blocks, and common access key formats.

The tests use fake agents, so they do not require Claude, Codex, Hermes, OpenClaw, or any paid provider.

## GitHub upload checklist

Before pushing publicly:

```bash
./check
git status --short
```

Make sure these are **not** included:

- `agents.yaml`
- `.env` or `.env.*`
- `.venv/`
- `runs/`
- `council_memory/`
- `__pycache__/`
- `*.egg-info/`
- screenshots or logs containing private prompts
- local absolute paths or company/user-specific names
- API keys, access credentials, private tokens, private key files

Expected public files include source code, tests, docs, examples, and scripts.

## Security model

Local AI Council is a local high-privilege tool because `agents.yaml` can define local commands.

Rules:

- Do not load untrusted `agents.yaml` files.
- Do not expose the GUI outside `127.0.0.1` unless authentication is added.
- Web API does not accept arbitrary config paths.
- History IDs are validated to prevent path traversal.
- Do not share `runs/` or `council_memory/` without reviewing contents.
- Do not add shell-string execution for user-controlled content.

## Troubleshooting

### `doctor` says `command_missing`

Check that the command is installed and visible in PATH:

```bash
which claude
which codex
which hermes
```

If GUI cannot find a command that works in your terminal, launch GUI from terminal:

```bash
./gui
```

### `doctor` times out

Likely causes:

- first-time login is required;
- CLI entered interactive mode;
- non-interactive flags are wrong;
- model/provider is slow.

Run the command manually and confirm it prints an answer without waiting for stdin.

### Codex complains about terminal stdin

Use the included adapter:

```yaml
codex:
  command: python3
  args: ["agent_adapter.py", "codex", "{{prompt}}"]
  timeout: 180
```

### No real AI CLI installed

Use fake agents for tests:

```yaml
summary_agent: agent_a
output_dir: runs

agents:
  agent_a:
    command: python3
    args: ["-c", "import sys; print('agent_a says: ' + sys.argv[1])", "{{prompt}}"]
    timeout: 10

  agent_b:
    command: python3
    args: ["-c", "import sys; print('agent_b says: ' + sys.argv[1])", "{{prompt}}"]
    timeout: 10
```

Then run:

```bash
./ai-council doctor --config test-agents.yaml
./ai-council "test question" --config test-agents.yaml
```

## Roadmap

### v0.2 Trustworthy council basics

- [x] `doctor` health checks;
- [x] GUI health status;
- [x] history context in later rounds and final synthesis;
- [x] Web config path hardening;
- [x] run ID path validation;
- [x] project-root path stability;
- [x] no-real-agent tests;
- [x] pre-upload sensitive content scan;
- [ ] session TTL and finalization slimming;
- [ ] metadata-only `result.json` index.

### v0.3 Structured deliberation protocol

- [x] lightweight RoundDigest;
- [x] lightweight CouncilState;
- [x] final synthesis uses CouncilState as primary input instead of raw transcript-only summarization;
- [x] structured state saved in `result.json` and report;
- [ ] Claim / Evidence / Risk / Confidence as first-class structured objects;
- [ ] consensus/disagreement matrix;
- [ ] richer quality panel in final report.

### v0.4 Distribution and ecosystem

- [ ] CI;
- [ ] screenshots/GIF demo;
- [ ] plugin-style adapters;
- [ ] more install paths;
- [ ] richer contribution docs;
- [ ] packaged release.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

Good contributions:

- new CLI adapters;
- known working non-interactive command examples;
- GUI improvements;
- tests and safety checks;
- memory retrieval improvements;
- RoundDigest / CouncilState design;
- docs, examples, screenshots, tutorials.

Before opening a PR:

```bash
./check
```

If you touched real agent integrations:

```bash
./ai-council doctor
```

## License

MIT
