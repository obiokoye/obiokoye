"""Keep the "30 Days of AI Agents" section of README.md up to date.

Runs in GitHub Actions (see .github/workflows/update-series.yml). It:
  1. works out today's day number (Day 1 = 2026-11-10, Lagos time),
  2. asks the GitHub API which series repos exist and have commits,
  3. rewrites everything between the SERIES markers in README.md.

Run it locally from the repo root with:  python .github/workflows/scripts/update_series.py
To change a description or a future project, edit PLAN below.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import date, datetime
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

OWNER = "obiokoye"
START = date(2026, 11, 10)
TOTAL = 30
TIMEZONE = "Africa/Lagos"
# The profile README: the nearest README.md above this script (works wherever the script lives).
README = next(p / "README.md" for p in Path(__file__).resolve().parents if (p / "README.md").exists())
BEGIN, END = "<!-- SERIES:START -->", "<!-- SERIES:END -->"

# (repo, stack, description)
PLAN: list[tuple[str, str, str]] = [
    ("cli-tool-agent", "python", "Terminal agent with tool calling"),
    ("streaming-chat-agent", "typescript", "Next.js chat app with streaming responses and live tool calls"),
    ("laravel-ai-assistant", "laravel", "Laravel + Prism PHP assistant with tool calling"),
    ("doc-extractor", "python", "Receipts and invoices to validated JSON with Pydantic"),
    ("pdf-rag-chat", "python", "Chat with your PDFs, with page citations (RAG)"),
    ("web-research-agent", "typescript", "Searches the web and writes a summary with citations"),
    ("ai-ticket-triage", "laravel", "Queue jobs that classify tickets, set priority and draft replies"),
    ("react-agent-from-scratch", "python", "ReAct agent loop with no framework"),
    ("langgraph-approval-agent", "python", "Stateful LangGraph agent that pauses for human approval"),
    ("mcp-sqlite-server", "typescript", "MCP server exposing SQLite tools to AI clients"),
    ("mcp-client-agent", "python", "Agent that connects to any MCP server and uses its tools"),
    ("text-to-sql-agent", "python", "Plain English to safe, read-only SQL with guardrails"),
    ("laravel-mcp-server", "laravel", "Exposes a Laravel app's data and actions over MCP"),
    ("browser-agent", "typescript", "Playwright agent that navigates websites and fills forms, with guardrails and human approval"),
    ("content-crew", "python", "Researcher, writer and editor agents working as a crew (CrewAI)"),
    ("pr-review-agent", "python", "GitHub Action that reviews pull requests with an LLM and posts inline comments"),
    ("memory-agent", "typescript", "Chat agent with long-term vector memory"),
    ("agent-evals", "python", "Eval harness for agents with LLM-as-judge scoring"),
    ("laravel-doc-qa", "laravel", "Document Q&A in Laravel with pgvector"),
    ("meeting-actions-agent", "typescript", "Meeting transcript to action items, owners and deadlines"),
    ("agent-observability", "python", "Tracing, token cost and latency tracking for agent runs"),
    ("job-application-agent", "python", "Tailors a CV and cover letter to a job posting"),
    ("support-widget-rag", "typescript", "Embeddable FAQ chatbot widget for any website (RAG)"),
    ("whatsapp-ai-agent", "laravel", "WhatsApp Business webhook AI agent for small businesses"),
    ("data-analyst-agent", "python", "Upload a CSV; the agent writes pandas code and charts"),
    ("hitl-dashboard", "typescript", "Dashboard to approve or reject agent actions (human in the loop)"),
    ("agent-guardrails", "python", "Prompt-injection defences with an attack test suite"),
    ("ai-saas-starter", "laravel", "Multi-tenant Laravel AI SaaS starter with usage metering and API keys"),
    ("deep-research-agent", "typescript", "Plans research, runs parallel sub-agents and writes a cited report"),
    ("ai-hiring-assistant", "mixed", "Capstone: Laravel API + Python agent service + Next.js UI for screening candidates"),
]


def today_day(today: date | None = None) -> int:
    today = today or datetime.now(ZoneInfo(TIMEZONE)).date()
    return max(0, min(TOTAL, (today - START).days + 1))


def _get(path: str) -> tuple[int, object]:
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "series-updater"},
    )
    token = os.getenv("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status, json.loads(resp.read() or b"null")
    except urllib.error.HTTPError as exc:
        return exc.code, None


class ApiError(RuntimeError):
    """GitHub answered with something unexpected (rate limit, outage). Don't touch the README."""


def is_shipped(repo: str) -> bool:
    """True if the repo is public and has at least one commit."""
    code, info = _get(f"/repos/{OWNER}/{repo}")
    if code == 404:
        return False
    if code != 200 or not isinstance(info, dict):
        raise ApiError(f"GET /repos/{OWNER}/{repo} returned {code}")
    if info.get("private"):
        return False
    code, commits = _get(f"/repos/{OWNER}/{repo}/commits?per_page=1")
    if code == 409:  # empty repository
        return False
    if code != 200:
        raise ApiError(f"GET /repos/{OWNER}/{repo}/commits returned {code}")
    return bool(commits)


def badge(label: str, message: str, color: str) -> str:
    def enc(s: str) -> str:
        return quote(s.replace("-", "--").replace("_", "__"), safe="")

    return f"https://img.shields.io/badge/{enc(label)}-{enc(message)}-{color}?style=for-the-badge"


def render(day: int, shipped: set[int]) -> str:
    done = len(shipped)
    word = "project" if done == 1 else "projects"
    lines = [
        BEGIN,
        "<!-- This section is generated by .github/workflows/scripts/update_series.py. Edits here are overwritten. -->",
        "<p>",
        f'  <img src="{badge("day", f"{day} / {TOTAL}", "D9B45A")}" alt="Day {day} of {TOTAL}" />',
        f'  <img src="{badge("shipped", f"{done} {word}", "2F8F75")}" alt="{done} shipped" />',
        "</p>",
        "",
        "| Day | Project | Stack | What it does |",
        "|-----|---------|-------|--------------|",
    ]
    for n, (repo, stack, plan_desc) in enumerate(PLAN, 1):
        if n in shipped:
            lines.append(f"| {n} | [{repo}](https://github.com/{OWNER}/{repo}) | {stack} | {plan_desc} |")
        elif n <= day:
            lines.append(f"| {n} | {repo} | {stack} | ⏳ In progress: {plan_desc} |")
    remaining = TOTAL - max(day, max(shipped, default=0))
    if remaining > 0:
        lines += ["", f"<sub>🔜 {remaining} more to come. This table updates itself every few hours.</sub>"]
    lines.append(END)
    return "\n".join(lines)


def main() -> int:
    text = README.read_text(encoding="utf-8")
    if BEGIN not in text or END not in text:
        print(f"README.md needs {BEGIN} and {END} markers", file=sys.stderr)
        return 1
    day = today_day()
    try:
        shipped = {n for n, (repo, _, _) in enumerate(PLAN, 1) if n <= max(day, 1) and is_shipped(repo)}
    except ApiError as exc:
        print(f"Skipping update: {exc}", file=sys.stderr)
        return 1
    section = render(day, shipped)
    new = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END), lambda _: section, text, flags=re.DOTALL)
    if new != text:
        README.write_text(new, encoding="utf-8")
        print(f"Updated: day {day}, {len(shipped)} shipped")
    else:
        print("No changes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
