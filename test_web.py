import json
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

import web_app
from web_app import app


def write_config(path: Path, output_dir: Path) -> None:
    path.write_text(
        f"""summary_agent: agent_a
output_dir: {output_dir}
agents:
  agent_a:
    command: python3
    args:
      - -c
      - "import sys; print(sys.argv[1])"
      - "{{{{prompt}}}}"
    timeout: 10
""",
        encoding="utf-8",
    )


def test_web_security_and_context() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        config_path = tmp_path / "agents.yaml"
        runs_dir = tmp_path / "runs"
        write_config(config_path, runs_dir)

        old_default_config_path = web_app.default_config_path
        old_memory_dir = web_app.MEMORY_DIR
        old_memory_file = web_app.MEMORY_FILE
        web_app.default_config_path = lambda: config_path
        web_app.MEMORY_DIR = tmp_path / "memory"
        web_app.MEMORY_FILE = web_app.MEMORY_DIR / "memories.jsonl"
        web_app.sessions.clear()
        try:
            client = TestClient(app)

            blocked = client.post(
                "/api/sessions",
                json={"question": "x", "config": str(config_path), "agents": ["agent_a"]},
            )
            assert blocked.status_code == 400

            first = client.post(
                "/api/sessions",
                json={"question": "历史问题", "agents": ["agent_a"], "max_rounds": 1, "use_memory": False},
            )
            assert first.status_code == 200, first.text
            session = first.json()
            finalized = client.post(f"/api/sessions/{session['session_id']}/finalize")
            assert finalized.status_code == 200, finalized.text
            run_id = Path(finalized.json()["run_dir"]).name

            traversal = client.get("/api/history/../outside")
            assert traversal.status_code in {400, 404}

            second = client.post(
                "/api/sessions",
                json={
                    "question": "后续问题",
                    "agents": ["agent_a"],
                    "max_rounds": 2,
                    "history_ids": [run_id],
                    "use_memory": True,
                },
            )
            assert second.status_code == 200, second.text
            second_session = second.json()
            assert "历史上下文" in second_session["effective_question"]

            continued = client.post(f"/api/sessions/{second_session['session_id']}/continue", json={"guidance": "继续"})
            assert continued.status_code == 200, continued.text
            prompt = continued.json()["rounds"][1]["prompts"]["agent_a"]
            assert "历史上下文" in prompt

            doctor = client.get("/api/doctor")
            assert doctor.status_code == 200, doctor.text
            assert doctor.json()["items"][0]["status"] == "ok"
        finally:
            web_app.default_config_path = old_default_config_path
            web_app.MEMORY_DIR = old_memory_dir
            web_app.MEMORY_FILE = old_memory_file
            web_app.sessions.clear()


def main() -> None:
    test_web_security_and_context()
    print("web-tests-ok")


if __name__ == "__main__":
    main()
