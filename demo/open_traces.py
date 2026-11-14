"""Open the two LangSmith traces that prove access levels: the newest `ask`, plus the newest trace of the
same question asked by a different person. Works on Windows, macOS and Linux.

Run from the repo root with the backend venv (it has the langsmith package):
    Windows:      backend\\.venv\\Scripts\\python demo\\open_traces.py sanctions
    macOS/Linux:  backend/.venv/bin/python demo/open_traces.py sanctions

The optional word ("sanctions") limits it to questions containing that word. Reads LANGSMITH_API_KEY
from the repo-root .env. Log into smith.langchain.com in your default browser first.
"""
import os
import sys
import webbrowser
from pathlib import Path

env = Path(__file__).resolve().parent.parent / ".env"
if env.exists():
    for line in env.read_text().splitlines():
        if line.startswith("LANGSMITH_API_KEY=") and not os.getenv("LANGSMITH_API_KEY"):
            os.environ["LANGSMITH_API_KEY"] = line.split("=", 1)[1].strip().strip('"')

from langsmith import Client  # noqa: E402

PROJECT = os.getenv("LANGSMITH_PROJECT", "default")
c = Client()


def meta(r):
    return (r.extra or {}).get("metadata", {})


asks = [r for r in c.list_runs(project_name=PROJECT, is_root=True, limit=100)
        if r.name == "ask" and meta(r).get("allowed_scopes") is not None]
want = next((a for a in sys.argv[1:] if not a.startswith("--")), None)
if want:
    asks = [r for r in asks if want.lower() in str((r.inputs or {}).get("question", "")).lower()]
if not asks:
    sys.exit("No ask traces found yet. Ask a question in the app, wait a few seconds, and run this again.")

first = asks[0]
q, who = (first.inputs or {}).get("question"), meta(first).get("viewer_id")
pair = next((r for r in asks[1:] if (r.inputs or {}).get("question") == q
             and meta(r).get("viewer_id") != who and meta(r).get("memory_on", True)), None)

for r in [x for x in (pair, first) if x]:  # older first, so the newest tab lands in front
    m = meta(r)
    url = c.get_run_url(run=r, project_name=PROJECT)
    print(f"--- {m.get('viewer_name')}: allowed {m.get('allowed_scopes')}, used {m.get('used_memory_ids')}, "
          f"withheld {m.get('blocked_count')}")
    print(f"    {url}")
    if "--no-open" not in sys.argv:
        webbrowser.open_new_tab(url)
if not pair:
    print("Only one person has asked this question so far. Ask it as the other role, then run again.")
