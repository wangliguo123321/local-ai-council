# Local AI Council / 串供

**语言：** [English](README.md) | [中文](README.zh-CN.md)

> 本地优先的多智能体 council 工具：让多个本机 AI CLI 独立回答、互相校准、生成最终答案，并保存完整审计记录。

Local AI Council 可以让你只问一次问题，自动调用多个本机 AI CLI，对比它们的独立回答，运行多轮“串供/校准”，并生成一份最终综合答案。

它**不是**神经网络意义上的 Mixture of Experts。它是一个轻量的本地 AI 智能体编排工具。

## 给 coding agent / AI agent 的入口

如果你是正在阅读这个仓库的 agent，请从这里开始：

1. 阅读本 README，理解产品目标和用户流程。
2. 阅读 [AGENTS.md](AGENTS.md)，理解实现地图、安全规则和 agent 开发约束。
3. 阅读 [agent.json](agent.json)，获取机器可读的安装、检查、运行入口。
4. 修改前后都运行 `./check`。
5. 不要提交本地配置、运行输出、记忆文件、`.env` 文件或生成产物。

主要文件：

| 文件 | 作用 |
| --- | --- |
| `ai_council.py` | 核心 CLI、配置、子进程调用、提示词协议、报告、`doctor` |
| `web_app.py` | FastAPI 后端，负责 GUI、会话、历史、记忆和 Web 安全检查 |
| `web_static/index.html` | 单文件浏览器 UI |
| `agent_adapter.py` | 为需要特殊非交互调用方式的 CLI 提供适配器 |
| `agents.yaml.example` | 本地智能体配置示例 |
| `agent.json` | 面向 agent 的机器可读 manifest：安装、检查、提问、GUI、输出、安全边界 |
| `skills/local-ai-council/SKILL.md` | 面向支持 local skills 的 agent 的 skill 风格说明 |
| `test_core.py` | 不依赖真实 AI CLI 的核心测试 |
| `test_web.py` | Web/API/安全/上下文回归测试 |
| `test_agent_package.py` | agent manifest 和 skill 包装测试 |
| `bootstrap` | 新用户一键初始化 |
| `check` | 本地提交前自检 |
| `preflight` | 上传 GitHub 前的敏感内容扫描 |

## 解决什么问题

只依赖一个 AI 模型处理重要问题很脆弱：

- 它可能自信但错误；
- 它可能漏掉边界情况；
- 它通常只给出一种视角；
- 它未必暴露不确定性；
- 它的判断过程不方便事后审计。

Local AI Council 会把你已有的本地 AI 工具变成一个评审委员会：

1. **独立回答**：每个智能体先在不知道其他答案的情况下独立回答。
2. **串供/校准**：后续轮次中，智能体看到其他答案，可以接受、反驳、修正或降级观点。
3. **最终综合**：summary agent 基于结构化审议状态生成最终答案。
4. **审计记录**：提示词、输出、错误、耗时、报告和最终答案都保存在本地。

适合用于：

- 架构评审；
- 代码评审；
- 技术决策；
- 产品决策；
- 调研和对比；
- Debug 方案评估；
- 多模型答案验证；
- 个人 AI 工作流实验。

## 当前状态

当前阶段：**v0.3 / Alpha**。

目前可用：

- CLI 和本地 Web GUI；
- 通过 `agents.yaml` 调用多个本地 AI CLI；
- 第一轮独立回答；
- 可选多轮串供/校准；
- 基于 CouncilState 的结构化最终综合；
- `doctor` 命令验证真实智能体是否可用；
- 历史记录和轻量记忆；
- 本地报告保存；
- agent-native manifest 和 skill 风格入口；
- 不依赖真实 AI CLI 的测试套件。

已知限制：

- 记忆仍是简单关键词召回；
- 多轮长对话仍可能产生较大的上下文和运行记录；
- GUI 可用但还不够精致；
- 不支持远程托管，请在 `127.0.0.1` 本机使用；
- Claim / Evidence / Risk / Confidence 还没有完全对象化。

## 快速开始

### 1. 克隆

```bash
git clone <repo-url>
cd local-ai-council
```

如果你的本地目录还叫别的名字，直接进入对应目录即可。

### 2. 初始化

```bash
./bootstrap
```

它会创建虚拟环境、安装依赖、设置脚本权限、在需要时创建默认配置，并运行本地检查。

手动安装：

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
chmod +x ai-council 串供 gui check bootstrap preflight
./check
```

### 3. 检查已配置智能体

```bash
./ai-council list
./ai-council doctor
```

`list` 检查命令是否存在于 `PATH`。

`doctor` 会真实调用每个智能体，返回：

| 状态 | 含义 |
| --- | --- |
| `ok` | 智能体成功输出内容 |
| `command_missing` | 命令不存在 |
| `timeout` | 超时 |
| `empty_output` | 命令成功但无输出 |
| `failed` | 非零退出码或执行错误 |

### 4. 启动 GUI

```bash
./gui
```

打开：

```text
http://127.0.0.1:7860
```

macOS 用户也可以双击：

```text
打开串供.command
```

### 5. CLI 提问

只跑一轮独立回答：

```bash
./ai-council "这个项目下一步应该优化什么？"
```

交互式串供模式：

```bash
./串供 "这个项目下一步应该优化什么？"
```

固定 3 轮：

```bash
./ai-council "这个项目下一步应该优化什么？" --rounds 3
```

只输出最终答案：

```bash
./ai-council "这个项目下一步应该优化什么？" --rounds 3 --final-only
```

## Agent-native 用法

这个仓库既面向人，也面向 coding agent。agent 不应该从自然语言文档里猜命令，而应该优先读取机器可读入口。

### 机器可读 manifest

[`agent.json`](agent.json) 描述了：

- 这个工具能做什么；
- 如何 bootstrap、check、ask、doctor、启动 GUI；
- 输出保存在哪里；
- 哪些文件敏感，不能发布；
- 本地安全边界。

agent 可以运行标准流程：

```bash
./bootstrap
./check
./ai-council doctor
./ai-council "这个项目下一步应该优化什么？" --rounds 2 --final-only
```

### Skill 风格包

[`skills/local-ai-council/SKILL.md`](skills/local-ai-council/SKILL.md) 提供了适合支持 local skills 的 agent 读取的说明。辅助脚本在 `skills/local-ai-council/scripts/`：

```bash
skills/local-ai-council/scripts/check
skills/local-ai-council/scripts/doctor
skills/local-ai-council/scripts/ask "这个项目下一步应该优化什么？" 2
skills/local-ai-council/scripts/gui
```

### MCP vs Skills

当前仓库先提供 skill 风格接口，因为它简单、本地优先、clone 后可用，不需要额外运行协议服务。MCP 更适合作为下一层：当需要让多个客户端稳定调用 `ask_council`、`doctor_agents`、`list_runs`、`read_run` 等 typed tools 时，再增加 MCP server。

推荐路线：

1. 先用 `agent.json` + `skills/local-ai-council/` 实现 agent 发现和执行。
2. 当 CLI/GUI 行为更稳定后，再新增 MCP server。
3. 始终让 CLI 做唯一事实来源，skills 和 MCP 都只包装 `./ai-council`，不要复制核心逻辑。

## GUI 功能

GUI 支持：

- 真实智能体健康检查；
- 问题输入；
- 智能体选择；
- 第一轮独立回答；
- 多轮串供/校准；
- 长轮次折叠；
- 每个 AI 输出和最终答案的一键复制；
- 最终综合；
- 历史列表和详情；
- 选择历史作为新问题上下文；
- 轻量记忆注入；
- 本地报告保存。

## 配置

默认配置查找顺序：

1. 项目本地 `agents.yaml`；
2. `~/.ai-council.yaml`。

`agents.yaml` 被 git 忽略，因为它可能暴露本地命令、路径或私有配置。

示例：

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

字段说明：

| 字段 | 含义 |
| --- | --- |
| `summary_agent` | 用于最终综合的智能体，必须存在于 `agents` 中 |
| `output_dir` | 本地运行记录目录，相对路径基于项目根目录解析 |
| `command` | 本地可执行命令 |
| `args` | 参数数组，`{{prompt}}` 会被替换为提示词 |
| `timeout` | 单个智能体超时时间，单位秒 |

项目以参数数组执行命令，不使用 `shell=True` 处理用户问题。

## 添加新智能体

在 `agents.yaml` 中增加：

```yaml
agents:
  my_agent:
    command: my-ai-cli
    args: ["run", "--prompt", "{{prompt}}"]
    timeout: 120
```

然后验证：

```bash
./ai-council doctor --only my_agent
```

一个好的智能体命令应该：

- 非交互运行；
- 接受 prompt 参数；
- 将最终答案写到 stdout；
- 失败时返回非零退出码；
- 不等待终端 stdin。

如果某个 CLI 需要特殊输出清理，可以在 `agent_adapter.py` 中新增适配器，并用 `doctor` 测试。

## 提示词协议

第一轮要求每个智能体输出：

- 结论；
- 主要依据；
- 不确定点；
- 反对意见或风险；
- 建议；
- 置信度。

校准轮要求每个智能体输出：

- 接受的观点；
- 不同意或需要降级的观点；
- 新增或修正的判断；
- 校准后的最终回答；
- 仍不确定的地方；
- 置信度。

最终综合要求输出：

- 结论；
- 主要依据；
- 共识；
- 分歧与少数派观点；
- 裁决理由；
- 质量审查；
- 仍不确定的地方；
- 置信度；
- 最值得继续追问的问题。

## 保存的数据

运行记录保存在：

```text
runs/YYYYMMDD-HHMMSS-mmm-xxxxxx/
```

典型文件：

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

轻量 GUI 记忆保存在：

```text
council_memory/memories.jsonl
```

`runs/` 和 `council_memory/` 都被 git 忽略。

## 测试和上传前检查

提交或上传前运行：

```bash
./check
```

它会运行：

```bash
python -m py_compile ai_council.py web_app.py agent_adapter.py test_core.py test_web.py test_agent_package.py
python test_core.py
python test_web.py
python test_agent_package.py
./preflight
```

`preflight` 会扫描明显本地/私有内容，例如本地用户路径、常见 key 名、私钥块和常见 access key 格式。

测试使用 fake agents，不需要 Claude、Codex、Hermes、OpenClaw 或任何付费服务。

## GitHub 上传检查清单

公开 push 前运行：

```bash
./check
git status --short
```

确认不要包含：

- `agents.yaml`
- `.env` 或 `.env.*`
- `.venv/`
- `runs/`
- `council_memory/`
- `__pycache__/`
- `*.egg-info/`
- 截图或包含私有 prompt 的日志
- 本地绝对路径或公司/用户专属名称
- API key、访问凭证、私有 token、私钥文件

预期公开文件包括源码、测试、文档、示例和脚本。

## 安全模型

Local AI Council 是一个本地高权限工具，因为 `agents.yaml` 可以定义本地命令。

规则：

- 不要加载不可信的 `agents.yaml`。
- 除非加入认证，否则不要把 GUI 暴露到 `127.0.0.1` 之外。
- Web API 不接受任意 config 路径。
- 历史 ID 会被校验，防止路径穿越。
- 不要在未审查内容前分享 `runs/` 或 `council_memory/`。
- 不要为用户可控内容添加 shell 字符串执行。

## Roadmap

### v0.2 Trustworthy council basics

- [x] `doctor` 健康检查；
- [x] GUI 健康状态；
- [x] 历史上下文进入后续轮次和最终综合；
- [x] Web config 路径加固；
- [x] run ID 路径校验；
- [x] 项目根路径稳定；
- [x] 不依赖真实智能体的测试；
- [x] 上传前敏感内容扫描；
- [ ] session TTL 和 finalization 瘦身；
- [ ] metadata-only `result.json` index。

### v0.3 Structured deliberation protocol

- [x] 轻量 RoundDigest；
- [x] 轻量 CouncilState；
- [x] 最终综合以 CouncilState 为主输入，不再只依赖原始 transcript；
- [x] `result.json` 和 report 保存结构化状态；
- [ ] Claim / Evidence / Risk / Confidence 对象化；
- [ ] 共识/分歧矩阵；
- [ ] 更丰富的质量审查面板。

### v0.4 Distribution and ecosystem

- [ ] CI；
- [ ] 截图/GIF demo；
- [ ] 插件式 adapters；
- [ ] 更多安装路径；
- [ ] 更丰富的贡献文档；
- [ ] MCP server；
- [ ] 打包发布。

## 贡献

见 [CONTRIBUTING.md](CONTRIBUTING.md)。

适合贡献的方向：

- 新 CLI adapter；
- 已知可用的非交互命令示例；
- GUI 改进；
- 测试和安全检查；
- 记忆检索改进；
- RoundDigest / CouncilState 设计；
- 文档、示例、截图、教程。

提交 PR 前：

```bash
./check
```

如果改了真实智能体集成：

```bash
./ai-council doctor
```

## License

MIT
