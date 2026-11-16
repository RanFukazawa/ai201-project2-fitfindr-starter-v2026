"""
capstone_eval.py: run the five capstone criteria against serve.py.

    python capstone_eval.py 1          trial 1
    python capstone_eval.py 2          trial 2 (a separate run, changing nothing)
    python capstone_eval.py 3          trial 3
    python capstone_eval.py --summary  print the run-log table from the three trials

Run it from the project root, next to serve.py. Needs a working .env key
(criterion 4 makes real, uncached model calls).

Every request goes through serve.py's real /ask route using Flask's test
client, so serve.py's real log_run() writes the log. The log file is pointed
at results/capstone_trial_N_log.jsonl for the run, so your cost log in
logs/runs.jsonl stays untouched.

How each failure is made:
  empty_body    POST {} (no query).
  mcp_down      the real MCP client asks the real server for a tool that
                doesn't exist, so the real MCPError is raised.
  key_outfit    a fake model client says the key is invalid on the first call.
  key_card      ...answers once (the outfit), then says the key is invalid.
  rate_outfit   a fake model client answers "429 ... retry in 29.7s" every
                time, so the real retry loop in generate.py runs every attempt.
  rate_card     ...answers once (the outfit), then 429s forever.
The sleeps the retry loop asks for are recorded, not performed.
"""

import json
import sys
import time
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import patch

import config

# Failure runs must really reach the model path, never get a cached answer.
config.CACHE_ENABLED = False

import agent  # noqa: E402
import generate  # noqa: E402
import mcp_client  # noqa: E402
import serve  # noqa: E402

RESULTS = config.ROOT / "results"
QUERY = "vintage graphic tee under $30"
EMPTY_QUERY = "designer ballgown size XXS under $5"
LIVE_QUERIES = [
    "vintage graphic tee under $30",
    "90s track jacket in size M",
    "silk slip dress in midi length under $40",
    "denim jacket under $50",
    "graphic hoodie",
]
KEY_ERROR = "API key not valid. Please pass a valid API key."
RATE_ERROR = "429 Resource exhausted. Please retry in 29.7s"

# The 10 failing requests from criteria 1, 2 and 5.
FAILURE_SET = (["empty_body"] * 2 + ["mcp_down"] * 3
               + ["key_outfit"] * 3 + ["rate_outfit"] * 2)
# The 5 situations from criterion 3.
SITUATIONS = ["mcp_down", "rate_outfit", "rate_card", "key_outfit", "key_card"]

CRITERIA = [
    ("1. Every failing request leaves exactly one log record", "10 of 10"),
    ("2. Rate-limit retry waits total 30 s or less", "2 of 2"),
    ("3. Failure message is true to the session", "5 of 5"),
    ("4. Original behaviour still works", "5/5 + 1/1"),
    ("5. No failing request ends in a crash", "10 of 10"),
]


# ── fault injection ───────────────────────────────────────────────────────────

def _fake_client(*outcomes):
    """Each generate_content call takes the next outcome (an Exception is
    raised, a string is returned as the reply). The last outcome repeats."""
    calls = {"n": 0}

    def generate_content(**kwargs):
        outcome = outcomes[min(calls["n"], len(outcomes) - 1)]
        calls["n"] += 1
        if isinstance(outcome, Exception):
            raise outcome
        return SimpleNamespace(text=outcome, usage_metadata=None)

    return SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))


def _apply_fault(stack, kind, sleeps):
    if kind == "mcp_down":
        real = mcp_client.call_tool
        stack.enter_context(patch.object(
            agent, "call_tool", lambda name, args: real("search_listingz", args)))
    elif kind in ("key_outfit", "key_card", "rate_outfit", "rate_card"):
        error = KEY_ERROR if kind.startswith("key") else RATE_ERROR
        if kind.endswith("outfit"):
            outcomes = (Exception(error),)
        else:
            outcomes = ("Pair it with baggy jeans.", Exception(error))
        stack.enter_context(patch("generate._get_client",
                                  return_value=_fake_client(*outcomes)))
        stack.enter_context(patch.object(
            generate, "time",
            SimpleNamespace(sleep=sleeps.append, monotonic=time.monotonic)))


# ── talking to serve.py ───────────────────────────────────────────────────────

def _count_lines(path):
    return len(path.read_text(encoding="utf-8").splitlines()) if path.exists() else 0


def _new_lines(path, before):
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()[before:]
    return [json.loads(line) for line in lines]


def _post(client, log_path, body):
    before = _count_lines(log_path)
    response = client.post("/ask", json=body)
    return response.status_code, (response.get_json(silent=True) or {}), _new_lines(log_path, before)


def _run_request(client, log_path, kind):
    generate._call_times.clear()   # so the pacing guard never adds real waits
    sleeps = []
    body = {} if kind == "empty_body" else {"query": QUERY}
    with ExitStack() as stack:
        _apply_fault(stack, kind, sleeps)
        status, resp, lines = _post(client, log_path, body)
    return {
        "kind": kind,
        "status": status,
        "error": resp.get("error"),
        "selected_title": (resp.get("selected_item") or {}).get("title"),
        "outfit_suggestion": resp.get("outfit_suggestion"),
        "fit_card": resp.get("fit_card"),
        "log_lines": lines,
        "sleeps_requested": sleeps,
        "sleep_total_s": round(sum(sleeps), 1),
    }


def _run_live(client, log_path):
    records = []
    for query in LIVE_QUERIES:
        status, resp, lines = _post(client, log_path, {"query": query})
        ok = (status == 200 and resp.get("error") is None
              and bool((resp.get("fit_card") or "").strip()))
        records.append({"query": query, "status": status, "ok": ok,
                        "error": resp.get("error"), "log_lines": lines})
    status, resp, lines = _post(client, log_path, {"query": EMPTY_QUERY})
    logged = lines[0] if lines else {}
    ok = (status == 200 and bool(resp.get("error"))
          and resp.get("outfit_suggestion") is None
          and logged.get("model_calls") == 0)
    empty = {"query": EMPTY_QUERY, "status": status, "ok": ok,
             "error": resp.get("error"), "log_lines": lines}
    return records, empty


# ── the checks ────────────────────────────────────────────────────────────────

def _log_ok(record):
    lines = record["log_lines"]
    return (len(lines) == 1 and lines[0].get("status") != "completed"
            and bool(lines[0].get("error")))


def _crash_ok(record):
    if record["kind"] == "empty_body":
        return record["status"] == 400
    return record["status"] == 200 and bool(record["error"])


def _message_problems(record):
    """Why the failure message is NOT true to the session (empty list = true)."""
    msg = (record["error"] or "").lower()
    if not msg:
        return ["no message at all"]
    problems = []
    if "write the outfit" in msg and record["outfit_suggestion"] is not None:
        problems.append("message says the outfit was not written, but outfit_suggestion is set")
    if "caption" in msg and record["fit_card"] is not None:
        problems.append("message says the caption was not written, but fit_card is set")
    if "i found " in msg:
        title = record["selected_title"]
        if title is None:
            problems.append("message names a listing, but selected_item is None")
        elif title.lower() not in msg:
            problems.append("message names a different listing than selected_item")
    return problems


# ── one trial ─────────────────────────────────────────────────────────────────

def run_trial(n):
    RESULTS.mkdir(exist_ok=True)
    log_path = RESULTS / f"capstone_trial_{n}_log.jsonl"
    if log_path.exists():
        log_path.unlink()
    generate._session_calls = 0   # stay clear of the session request budget

    client = serve.app.test_client()
    with patch.object(serve, "LOG_FILE", log_path):
        print(f"\n--- Trial {n}: criterion 4 (live model, real pacing) ---")
        live, empty = _run_live(client, log_path)
        print(f"--- Trial {n}: the 10 failing requests ---")
        failures = [_run_request(client, log_path, kind) for kind in FAILURE_SET]
        print(f"--- Trial {n}: the 5 message situations ---")
        situations = [_run_request(client, log_path, kind) for kind in SITUATIONS]

    rate = [r for r in failures if r["kind"] == "rate_outfit"]
    counts = {
        "1": [sum(_log_ok(r) for r in failures), len(failures)],
        "2": [sum(r["sleep_total_s"] <= 30 for r in rate), len(rate)],
        "3": [sum(not _message_problems(r) for r in situations), len(situations)],
        "4": [sum(r["ok"] for r in live) + int(empty["ok"]), len(live) + 1],
        "5": [sum(_crash_ok(r) for r in failures), len(failures)],
    }

    out = RESULTS / f"capstone_trial_{n}.json"
    out.write_text(json.dumps(
        {"trial": n, "counts": counts, "live": live, "empty_search": empty,
         "failures": failures, "situations": situations},
        indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n" + "=" * 72)
    print(f"TRIAL {n} RESULTS")
    print("=" * 72)
    for (name, target), key in zip(CRITERIA, "12345"):
        ok, total = counts[key]
        print(f"  {name}: {ok}/{total}   (target {target})")
    print("\nCriterion 2, retry waits requested (seconds):")
    for r in rate:
        print(f"  {r['sleeps_requested']} -> total {r['sleep_total_s']}")
    print("\nCriterion 3, message problems:")
    for r in situations:
        problems = _message_problems(r)
        print(f"  {r['kind']:<12} {'OK' if not problems else 'PROBLEM: ' + '; '.join(problems)}")
    print(f"\nSaved {out.name} and {log_path.name} in results/")


# ── the run-log table ─────────────────────────────────────────────────────────

def summarize():
    trials = []
    for n in (1, 2, 3):
        path = RESULTS / f"capstone_trial_{n}.json"
        if not path.exists():
            print(f"Missing {path.name}. Run: python capstone_eval.py {n}")
            return
        trials.append(json.loads(path.read_text(encoding="utf-8")))

    print("| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |")
    print("|---|---|---|---|---|---|")
    for (name, target), key in zip(CRITERIA, "12345"):
        cells = []
        met = True
        for t in trials:
            ok, total = t["counts"][key]
            cells.append(f"{ok}/{total}")
            met = met and ok == total
        print(f"| {name} | {target} | " + " | ".join(cells)
              + f" | {'MET' if met else 'MISSED'} |")


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--summary":
        summarize()
    elif len(sys.argv) == 2 and sys.argv[1] in ("1", "2", "3"):
        run_trial(int(sys.argv[1]))
    else:
        print(__doc__)
        sys.exit(2)