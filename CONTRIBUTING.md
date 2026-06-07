# Contributing

Thanks for helping improve Local AI Council.

## Development setup

```bash
./bootstrap
```

Run checks before submitting changes:

```bash
./check
```

If you changed real agent configuration, also run:

```bash
./ai-council doctor
```

## Good first contributions

- Add an adapter for another AI CLI.
- Document a known working non-interactive command for an AI tool.
- Improve GUI usability.
- Add tests for config parsing, path safety, or history behavior.
- Improve memory retrieval and memory management.
- Add screenshots, GIFs, or tutorials.

## Adding an agent

Prefer non-interactive commands. A good agent command should:

- accept the prompt as an argument;
- not wait for terminal stdin;
- write the final answer to stdout;
- return non-zero on failure;
- support timeout safely.

Example:

```yaml
agents:
  my_agent:
    command: my-ai-cli
    args: ["run", "--prompt", "{{prompt}}"]
    timeout: 120
```

Then test:

```bash
./ai-council doctor --only my_agent
```

## Security expectations

Do not add code that executes shell strings with `shell=True` for user-provided content. Keep command execution as argument arrays.

Web routes should treat this as a local high-privilege tool. Validate IDs and paths, and do not expose arbitrary local command execution through the GUI.

## Pull request checklist

- [ ] `./check` passes.
- [ ] README or docs updated if behavior changed.
- [ ] New agent integrations include a `doctor` example.
- [ ] Security-sensitive path/config changes include tests.
