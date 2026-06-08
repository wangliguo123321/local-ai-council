---
name: local-ai-council
description: Use a local multi-agent AI council to ask multiple configured AI CLIs, run calibration rounds, synthesize a final answer, and save an audit trail.
---

# Local AI Council Skill

Use this skill when the user wants multiple local AI agents to answer the same question, compare independent outputs, calibrate across rounds, or produce a final synthesized answer with local records.

## What this skill does

- Runs `./ai-council` against locally configured AI CLIs.
- Supports independent first-round answers and optional calibration rounds.
- Produces a final synthesized answer.
- Saves prompts, outputs, reports, and structured CouncilState under `runs/`.
- Can launch a local GUI through `./gui`.

## First-time setup

From the repository root:

```bash
./bootstrap
```

Then verify the project and configured local AI CLIs:

```bash
./check
./ai-council doctor
```

`./check` uses fake agents and does not require real AI CLIs. `doctor` calls configured real CLIs and may fail if the local machine has not installed or logged into those tools.

## Non-interactive use

For a final synthesized answer:

```bash
./ai-council "{{question}}" --rounds 2 --final-only
```

For a full text report:

```bash
./ai-council "{{question}}" --rounds 2
```

For interactive calibration:

```bash
./串供 "{{question}}"
```

## GUI use

```bash
./gui
```

Open `http://127.0.0.1:7860` if the browser does not open automatically.

## Safety and privacy

- Do not expose the GUI beyond `127.0.0.1` unless authentication is added.
- Do not commit or publish `agents.yaml`, `runs/`, `council_memory/`, `.env`, or generated artifacts.
- Treat `agents.yaml` as high privilege because it defines local commands.
- The project executes configured commands as argument arrays and should not introduce shell-string execution for user prompts.

## When modifying this skill/project

Run before and after changes:

```bash
./check
```

If you changed real agent integration, also run:

```bash
./ai-council doctor
```
