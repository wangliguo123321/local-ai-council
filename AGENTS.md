# Agent Guide for Local AI Council

This repository is designed to be understandable and modifiable by coding agents.

## Project purpose

Local AI Council is a local-first multi-agent orchestration tool. It calls multiple local AI CLIs with the same question, records independent answers, optionally runs calibration rounds, and synthesizes a final answer with an audit trail.

It is not a neural-network Mixture of Experts implementation.

## Main entry points

- `ai_council.py` — core CLI, config loading, agent execution, prompts, reports, doctor checks.
- `web_app.py` — FastAPI backend for local GUI, sessions, history, memory, doctor API.
- `web_static/index.html` — single-file GUI.
- `agent_adapter.py` — wrappers for CLIs that need special non-interactive handling.
- `agents.yaml.example` — example agent configuration.
- `test_core.py` — core no-real-agent tests.
- `test_web.py` — FastAPI/security/context tests.

## How to run locally

```bash
./bootstrap
./check
./ai-council doctor
./gui
```

If no real AI CLI is installed, `./check` still works because tests use fake agents.

## Agent-native package

- `agent.json` is the machine-readable manifest for install/check/ask/GUI entrypoints.
- `skills/local-ai-council/SKILL.md` is the skill-style entrypoint for agents that support local skills.
- Keep the CLI as the source of truth; skills and future MCP tools should wrap `./ai-council`, not duplicate council logic.
- If adding an MCP server later, expose stable typed tools around existing capabilities: `ask_council`, `doctor_agents`, `list_runs`, and `read_run`.

## Safety rules

- Do not use `shell=True` with user-provided content.
- Keep command execution as argument arrays.
- Treat `agents.yaml` as sensitive because it can execute local commands.
- Do not commit `agents.yaml`, `runs/`, `council_memory/`, `.env`, or generated build artifacts.
- Web routes must validate IDs and paths; never expose arbitrary local file reads or command execution.
- The GUI is intended for `127.0.0.1` local use unless authentication is added.

## Design constraints

- Prefer local-first behavior.
- Prefer explicit saved audit trails over opaque summaries.
- First round should remain independent; later rounds can see other answers.
- `doctor` should validate real non-interactive usability, not just `PATH` presence.
- Keep tests runnable without real external AI CLIs.

## Before changing behavior

Run:

```bash
./check
```

If touching real agent integration, also run:

```bash
./ai-council doctor
```

## Recommended next improvements

- Session TTL and finalization slimming.
- `result.json` as metadata index instead of duplicating large text.
- RoundDigest / CouncilState to avoid context explosion.
- More adapters for non-interactive AI CLIs.
- Better memory management and deletion controls.
