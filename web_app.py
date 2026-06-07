import json
import re
import uuid
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ai_council import (
    ROOT_DIR,
    CouncilRound,
    config_output_dir,
    build_calibration_prompt,
    build_initial_prompt,
    default_config_path,
    doctor_agents,
    load_or_create_config,
    run_agent_prompts,
    save_run,
    selected_agents,
    summarize,
)

app = FastAPI(title="串供")
WEB_STATIC_DIR = ROOT_DIR / "web_static"
MEMORY_DIR = ROOT_DIR / "council_memory"
MEMORY_FILE = MEMORY_DIR / "memories.jsonl"
RUN_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")

app.mount("/static", StaticFiles(directory=WEB_STATIC_DIR), name="static")

sessions: dict[str, dict] = {}


class StartRequest(BaseModel):
    question: str
    agents: list[str] | None = None
    max_rounds: int = 5
    config: str | None = None
    history_ids: list[str] | None = None
    use_memory: bool = True


class ContinueRequest(BaseModel):
    guidance: str = ""


def config_for(path: str | None) -> dict:
    if path:
        raise HTTPException(status_code=400, detail="Web API 不接受自定义 config 路径，请使用默认 agents.yaml 或 ~/.ai-council.yaml")
    return load_or_create_config(default_config_path(), auto_init=True)


def round_payload(council_round: CouncilRound) -> dict:
    return {
        "number": council_round.number,
        "prompts": council_round.prompts,
        "results": [asdict(result) for result in council_round.results],
    }


def session_payload(session_id: str, session: dict) -> dict:
    return {
        "session_id": session_id,
        "question": session["question"],
        "effective_question": session.get("effective_question", session["question"]),
        "history_context": session.get("history_context", ""),
        "max_rounds": session["max_rounds"],
        "rounds": [round_payload(council_round) for council_round in session["rounds"]],
        "final_answer": asdict(session["final_answer"]) if session.get("final_answer") else None,
        "run_dir": str(session["run_dir"]) if session.get("run_dir") else None,
    }


def output_dir() -> Path:
    return config_output_dir(config_for(None))


def checked_run_dir(run_id: str) -> Path:
    if not RUN_ID_RE.fullmatch(run_id) or ".." in run_id:
        raise HTTPException(status_code=400, detail="历史记录 ID 不合法")
    base = output_dir().resolve()
    run_dir = (base / run_id).resolve()
    if base != run_dir and base not in run_dir.parents:
        raise HTTPException(status_code=400, detail="历史记录 ID 不合法")
    return run_dir


def run_id_from_path(path: Path) -> str:
    return path.name


def load_run(run_id: str) -> dict:
    run_dir = checked_run_dir(run_id)
    result_path = run_dir / "result.json"
    if not result_path.exists():
        raise HTTPException(status_code=404, detail="历史记录不存在")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    final_answer_path = run_dir / "final-answer.md"
    report_path = run_dir / "report.md"
    return {
        "id": run_id,
        "run_dir": str(run_dir),
        "result": result,
        "question": result.get("question", ""),
        "final_answer": final_answer_path.read_text(encoding="utf-8") if final_answer_path.exists() else "",
        "report": report_path.read_text(encoding="utf-8") if report_path.exists() else "",
    }


def list_runs(limit: int = 50) -> list[dict]:
    base = output_dir()
    if not base.exists():
        return []
    items = []
    for run_dir in sorted([p for p in base.iterdir() if p.is_dir()], reverse=True):
        result_path = run_dir / "result.json"
        if not result_path.exists():
            continue
        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        final_answer = (run_dir / "final-answer.md").read_text(encoding="utf-8") if (run_dir / "final-answer.md").exists() else ""
        items.append({
            "id": run_id_from_path(run_dir),
            "question": result.get("question", ""),
            "run_dir": str(run_dir),
            "created_at": run_dir.name,
            "round_count": len(result.get("rounds", [])),
            "final_excerpt": final_answer[:240],
        })
        if len(items) >= limit:
            break
    return items


def memory_records() -> list[dict]:
    if not MEMORY_FILE.exists():
        return []
    records = []
    for line in MEMORY_FILE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def add_memory(question: str, final_answer: str, run_dir: Path) -> None:
    if not final_answer.strip():
        return
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    record = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "question": question,
        "summary": final_answer[:2000],
        "run_dir": str(run_dir),
    }
    with MEMORY_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def relevant_memories(question: str, limit: int = 5) -> list[dict]:
    terms = {token for token in question.lower().replace("？", " ").replace("?", " ").split() if token}
    scored = []
    for record in memory_records():
        text = f"{record.get('question', '')}\n{record.get('summary', '')}".lower()
        score = sum(1 for term in terms if term in text)
        if score or not terms:
            scored.append((score, record))
    scored.sort(key=lambda item: (item[0], item[1].get("created_at", "")), reverse=True)
    return [record for _, record in scored[:limit]]


def build_history_context(question: str, history_ids: list[str] | None, use_memory: bool) -> str:
    sections = []
    if history_ids:
        for run_id in history_ids[:5]:
            item = load_run(run_id)
            if item["final_answer"]:
                sections.append(f"## 指定历史：{item['question']}\n{item['final_answer'][:3000]}")
    if use_memory:
        for record in relevant_memories(question):
            sections.append(f"## 相关记忆：{record.get('question', '')}\n{record.get('summary', '')[:1500]}")
    return "\n\n".join(sections)


def build_effective_question(question: str, history_context: str) -> str:
    if not history_context:
        return question
    return f"""请结合以下历史上下文回答新问题。历史上下文只作为参考；如果与新问题无关，请降低权重。\n\n{history_context}\n\n# 新问题\n{question}\n"""


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return Path("web_static/index.html").read_text(encoding="utf-8")


@app.get("/api/config")
def get_config() -> dict:
    config = config_for(None)
    agents = []
    for name, agent in config["agents"].items():
        agents.append({
            "name": name,
            "command": agent.get("command", ""),
            "args": agent.get("args", []),
            "timeout": agent.get("timeout", 120),
            "summary": name == config.get("summary_agent"),
        })
    return {"summary_agent": config.get("summary_agent"), "agents": agents}


@app.get("/api/doctor")
async def doctor() -> dict:
    items = await doctor_agents(config_for(None))
    return {"items": [asdict(item) for item in items]}


@app.get("/api/history")
def history() -> dict:
    return {"items": list_runs()}


@app.get("/api/history/{run_id}")
def history_detail(run_id: str) -> dict:
    return load_run(run_id)


@app.get("/api/memories")
def memories() -> dict:
    return {"items": list(reversed(memory_records()))[:100]}


@app.post("/api/sessions")
async def start_session(request: StartRequest) -> dict:
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="问题不能为空")

    config = config_for(request.config)
    agents = selected_agents(config, request.agents, None)
    history_context = build_history_context(question, request.history_ids, request.use_memory)
    effective_question = build_effective_question(question, history_context)
    first_prompts = {name: build_initial_prompt(effective_question, name) for name in agents}
    first_results = await run_agent_prompts(agents, first_prompts)
    first_round = CouncilRound(1, first_prompts, first_results)

    session_id = uuid.uuid4().hex
    sessions[session_id] = {
        "question": question,
        "effective_question": effective_question,
        "history_context": history_context,
        "config": config,
        "agents": agents,
        "max_rounds": max(1, request.max_rounds),
        "rounds": [first_round],
        "final_answer": None,
        "run_dir": None,
    }
    return session_payload(session_id, sessions[session_id])


@app.post("/api/sessions/{session_id}/continue")
async def continue_session(session_id: str, request: ContinueRequest) -> dict:
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    if len(session["rounds"]) >= session["max_rounds"]:
        raise HTTPException(status_code=400, detail="已达到最大轮数")

    question = session.get("effective_question", session["question"])
    agents = session["agents"]
    rounds = session["rounds"]
    prompts = {
        name: build_calibration_prompt(question, name, rounds, request.guidance.strip())
        for name in agents
    }
    results = await run_agent_prompts(agents, prompts)
    rounds.append(CouncilRound(len(rounds) + 1, prompts, results))
    session["final_answer"] = None
    session["run_dir"] = None
    return session_payload(session_id, session)


@app.post("/api/sessions/{session_id}/finalize")
async def finalize_session(session_id: str) -> dict:
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    question_for_prompt = session.get("effective_question", session["question"])
    run_output_dir = config_output_dir(session["config"])
    final_answer = await summarize(session["config"], question_for_prompt, session["rounds"])
    run_dir = save_run(
        run_output_dir,
        session["question"],
        session["rounds"],
        final_answer,
        effective_question=question_for_prompt,
        history_context=session.get("history_context", ""),
    )
    session["final_answer"] = final_answer
    session["run_dir"] = run_dir
    if final_answer and final_answer.ok:
        add_memory(session["question"], final_answer.stdout, run_dir)
    return session_payload(session_id, session)


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str) -> dict:
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    return session_payload(session_id, session)
