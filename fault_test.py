"""
fault_test.py: trigger FitFindr's failure paths on purpose and show what the
user would see.

    python fault_test.py               all scenarios, including one live model run
    python fault_test.py --skip-live   skip the live control run (no API calls)

Run it from the project root, next to app.py.

How the failures are made:
  * MCP down      the real MCP client asks the real server for a tool that
                  doesn't exist, so MCPError is raised by the real code path.
  * Rate limit    a fake model client answers "429" every time, so the real
                  generate() retry loop runs all its attempts. Only the
                  sleeping between attempts is skipped.
  * Bad key       a fake model client says the key is invalid, so the real
                  generate() raises ModelUnavailable.
  * Partial       the fake client answers once, then returns 429 forever, so
                  suggest_outfit succeeds and create_fit_card fails.
  * Control       nothing patched. A live run that must still succeed.
"""

import sys
import time
from types import SimpleNamespace
from unittest.mock import patch

import config
import agent
import generate
import mcp_client
from utils.data_loader import get_example_wardrobe

QUERY = "vintage graphic tee under $30"

# Failure runs must really call the model path, never hand back a cached answer.
config.CACHE_ENABLED = False


def _fake_client(*outcomes):
    """
    A stand-in for the model client. Each call to generate_content takes the
    next outcome: an Exception is raised, a string is returned as the reply
    text. The last outcome repeats forever. Also returns a call counter.
    """
    calls = {"n": 0}

    def generate_content(**kwargs):
        outcome = outcomes[min(calls["n"], len(outcomes) - 1)]
        calls["n"] += 1
        if isinstance(outcome, Exception):
            raise outcome
        return SimpleNamespace(text=outcome, usage_metadata=None)

    client = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
    return client, calls


def _no_sleep():
    """Replace generate's `time` with one that doesn't actually wait."""
    return patch.object(
        generate, "time",
        SimpleNamespace(sleep=lambda seconds: None, monotonic=time.monotonic),
    )


def _run():
    return agent.run_agent(QUERY, get_example_wardrobe())


# Each scenario returns (session, notes, problems).

def scenario_mcp_down():
    real_call_tool = mcp_client.call_tool
    with patch.object(agent, "call_tool",
                      lambda name, args: real_call_tool("search_listingz", args)):
        return _run(), [], []


def scenario_rate_limit():
    client, calls = _fake_client(Exception("429 Resource exhausted"))
    with patch("generate._get_client", return_value=client), _no_sleep():
        session = _run()
    notes = [f"model attempts: {calls['n']} (config.MAX_RETRIES = {config.MAX_RETRIES})"]
    problems = []
    if calls["n"] != config.MAX_RETRIES:
        problems.append(f"expected {config.MAX_RETRIES} attempts, saw {calls['n']}")
    return session, notes, problems


def scenario_bad_key():
    client, calls = _fake_client(Exception("API key not valid. Please pass a valid API key."))
    with patch("generate._get_client", return_value=client), _no_sleep():
        session = _run()
    return session, [f"model attempts: {calls['n']}"], []


def scenario_partial():
    client, calls = _fake_client("Pair it with baggy jeans.", Exception("429 Resource exhausted"))
    with patch("generate._get_client", return_value=client), _no_sleep():
        session = _run()
    notes = [
        f"model attempts: {calls['n']}",
        f"outfit kept in session: {session['outfit_suggestion']!r}",
    ]
    return session, notes, []


def scenario_control():
    return _run(), [], []


# name, function, phrase the error must contain (None = no error expected),
# fields that must be None, fields that must be set, needs the live model
SCENARIOS = [
    ("MCP search unreachable", scenario_mcp_down,
     "couldn't reach the search service",
     ["selected_item", "outfit_suggestion", "fit_card"], [], False),
    ("Rate limit exhausted (outfit step)", scenario_rate_limit,
     "rate limit ran out",
     ["outfit_suggestion", "fit_card"], ["selected_item"], False),
    ("Bad API key", scenario_bad_key,
     "rejected your api key",
     ["outfit_suggestion", "fit_card"], ["selected_item"], False),
    ("Rate limit exhausted (fit card step only)", scenario_partial,
     "rate limit ran out",
     ["fit_card"], ["selected_item", "outfit_suggestion"], False),
    ("Control: nothing broken (live model)", scenario_control,
     None,
     ["error"], ["selected_item", "outfit_suggestion", "fit_card"], True),
]


def check(session, expect_error, must_be_none, must_be_set):
    problems = []
    error = session.get("error")
    if expect_error is None:
        if error:
            problems.append(f"unexpected error: {error}")
    elif not error or expect_error not in error.lower():
        problems.append(f"error should contain {expect_error!r}, got {error!r}")
    for field in must_be_none:
        if session.get(field) is not None:
            problems.append(f"{field} should be None, got {str(session[field])[:60]!r}")
    for field in must_be_set:
        if session.get(field) is None:
            problems.append(f"{field} should be set, but is None")
    return problems


def main():
    skip_live = "--skip-live" in sys.argv
    results = []

    for name, func, expect_error, must_be_none, must_be_set, needs_live in SCENARIOS:
        print("\n" + "=" * 72)
        print(f"SCENARIO: {name}")
        print("=" * 72)

        if needs_live and skip_live:
            print("skipped (--skip-live)")
            results.append((name, "SKIP"))
            continue

        # Earlier scenarios log fake attempts. Clear them so the pacing code
        # doesn't make a later scenario really wait for the minute to pass.
        generate._call_times.clear()

        try:
            session, notes, problems = func()
        except Exception as exc:  # noqa: BLE001 — an escaped exception IS the failure
            print(f"\n  ESCAPED: {type(exc).__name__}: {str(exc)[:200]}")
            results.append((name, "FAIL"))
            continue

        problems = problems + check(session, expect_error, must_be_none, must_be_set)

        print("\n  User sees:")
        print(f"    {session.get('error') or '(no error; run completed)'}")
        for note in notes:
            print(f"  {note}")
        for problem in problems:
            print(f"  PROBLEM: {problem}")
        results.append((name, "FAIL" if problems else "PASS"))

    print("\n" + "=" * 72)
    print("SUMMARY")
    print("=" * 72)
    for name, outcome in results:
        print(f"  [{outcome}] {name}")

    sys.exit(1 if any(outcome == "FAIL" for _, outcome in results) else 0)


if __name__ == "__main__":
    main()