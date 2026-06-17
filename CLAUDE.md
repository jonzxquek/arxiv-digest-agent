# ArXiv Research Digest Agent — Claude Code Guidelines

## Project overview

A multi-agent AI pipeline built with CrewAI that fetches recent ArXiv papers on a topic, filters them for relevance, clusters them by theme, and writes a structured newsletter digest exported as a PDF.

**Environment:** macOS · Python 3.11.9 · virtualenv (venv/) · VS Code
**LLM:** Groq free tier — llama-3.3-70b-versatile
**All dependencies:** installed via requirements.txt

---

## File structure

| File | Purpose |
|---|---|
| `.env` | GROQ_API_KEY and OPENAI_API_KEY — never read, print, or log these |
| `agents.py` | All CrewAI Agent definitions + LLM config |
| `tasks.py` | All CrewAI Task definitions + context chaining |
| `tools.py` | Custom ArxivSearchTool (BaseTool subclass) |
| `main.py` | Crew entry point + hallucination ID check |
| `renderer.py` | PDF generation via fpdf2 — NOT YET BUILT |
| `test_arxiv.py` | Standalone ArXiv API test — no LLM, no cost |
| `outputs/` | PDF and JSON run outputs saved here |
| `venv/` | Virtual environment — never modify |

---

## Pipeline architecture

Agents run in CrewAI sequential process. Each agent receives the prior agent's full output via context=[prior_task] — NOT via manual passing.

INPUT: topic, category, days_back, max_results (via crew.kickoff inputs)

Agent 1 — Fetcher
  Tool: ArxivSearchTool (wraps arxiv Python library)
  Job:  calls ArXiv API, returns raw JSON array of paper objects
  Note: no LLM reasoning on content — pure data retrieval
  Out:  JSON array of papers

        down-arrow context=[fetch_task]

Agent 2 — Filter and Scorer
  Tools: none — reasons purely on context from Agent 1
  Job:  scores each paper 1-10 for relevance, drops papers below 6,
        adds relevance_score (int) and reason (str) to each kept paper
  Out:  filtered JSON array (same structure + two new fields)

        down-arrow context=[filter_task]

Agent 3 — Thematic Clusterer (NOT YET BUILT)
  Job:  groups filtered papers into 3-5 named research themes
  Out:  structured JSON dict mapping theme names to paper lists

        down-arrow context=[cluster_task]

Agent 4 — Digest Writer (NOT YET BUILT)
  Job:  writes newsletter in markdown with intro, theme sections,
        spotlight paper, and what-to-watch outlook paragraph
  Out:  clean markdown string

        down-arrow (not an agent)

PDF Renderer — renderer.py (NOT YET BUILT)
  Deterministic Python function, no LLM involved
  Converts markdown to styled PDF using fpdf2
  Saves to outputs/digest_YYYY-MM-DD.pdf

---

## Current build state

| Component | Status | Notes |
|---|---|---|
| Agent 1 Fetcher | COMPLETE | Verified returning real ArXiv papers |
| Agent 2 Filter and Scorer | COMPLETE | Hallucination fix applied, ID check in main.py |
| Agent 3 Clusterer | NOT BUILT | Next step |
| Agent 4 Digest Writer | NOT BUILT | After Agent 3 |
| PDF Renderer | NOT BUILT | After Agent 4 |
| Week-over-week memory | NOT BUILT | JSON files saved to outputs/ |
| CLI entry point | NOT BUILT | Final step |

---

## Data contract between agents

Every paper object flowing through the pipeline must maintain these fields exactly. Agents must not rename, drop, or reformat them.

id:              string  — ArXiv URL e.g. http://arxiv.org/abs/2506.xxxxx
title:           string  — full paper title
authors:         array   — up to 3 author name strings
abstract:        string  — truncated to 200 chars
published:       string  — YYYY-MM-DD format
url:             string  — same as id
relevance_score: int     — added by Agent 2, range 6-10
reason:          string  — added by Agent 2, one sentence

Agents 3 and 4 add structure AROUND paper objects — never TO them.

---

## Key technical decisions — do not change without asking

1. load_dotenv() is at the top of agents.py, not just main.py
When main.py imports agents.py, Python immediately executes it including ChatGroq() — before main.py's own load_dotenv() runs. Without this, Groq throws a missing API key error on import.

2. Filter agent has max_iter=2
Intentionally low. This agent has a simple, well-defined job. If it cannot complete in 2 steps the prompt is the problem — not the iteration count. Raising max_iter here masks prompt issues rather than fixing them.

3. Filter task description contains strict grounding instructions
Agent 2 was hallucinating fabricated papers using training knowledge instead of scoring the actual fetched papers. Every constraint in the description is load-bearing. Do not simplify or shorten it.

4. context=[prior_task] — not manual passing
CrewAI injects the prior task's raw output automatically when context is set. Manually extracting and passing output creates duplication and breaks flow.

5. Hallucination ID check in main.py
After the crew runs, main.py diffs IDs from fetch_task.output.raw against the filter output. Any returned ID not in the fetched set is a fabricated paper. This is a hard verification step — do not remove it.

6. Abstract truncation to 200 chars in tools.py
Keeps token usage within Groq's 12,000 TPM free tier limit. Full abstracts at 20 papers would risk hitting the per-minute window.

7. Monkey-patch in main.py before CrewAI imports
CrewAI adds an Anthropic-specific cache marker that Groq rejects. The patch must run before any CrewAI import. Import order in main.py is load-bearing — do not reorder imports.

8. Temperature set to 0.2 across all agents
Lower temperature = more deterministic output = more reliable JSON structure. Do not raise above 0.3.

9. Agent 1 uses GPT-4o Mini (OpenAI) not Groq Llama
Llama 3.3 70B was hallucinating papers by skipping the arxiv_search tool call entirely and generating papers from training knowledge. GPT-4o Mini has significantly more reliable tool-calling behaviour. Agent 1 is the only agent using OpenAI — Agents 2, 3, 4 remain on Groq Llama. Requires OPENAI_API_KEY in .env and langchain-openai package installed.

---

## Rate limit — Groq free tier

Limit: 12,000 tokens per minute (TPM) · 30 requests per minute
Model: llama-3.3-70b-versatile

| Agent | Estimated tokens |
|---|---|
| Agent 1 Fetcher | ~500 |
| Agent 2 Filter | ~6,000 (heaviest — processes all abstracts) |
| Agent 3 Clusterer | ~3,000 |
| Agent 4 Writer | ~4,000 |
| Full pipeline total | ~13,500 across 3-4 minutes runtime |

Current 2-agent run (Agents 1+2): ~7,100 tokens — safely under limit.

---

## Rate limit — OpenAI free credit (Agent 1 only)

Model: gpt-4o-mini
Free credit: $5 on signup — approximately 2,000+ Agent 1 runs
Monitor usage at: platform.openai.com → Settings → Billing

| Agent | Platform | Model |
|---|---|---|
| Agent 1 Fetcher | OpenAI | gpt-4o-mini |
| Agent 2 Filter | Groq | llama-3.3-70b-versatile |
| Agent 3 Clusterer | Groq | llama-3.3-70b-versatile |
| Agent 4 Writer | Groq | llama-3.3-70b-versatile |

---

## Rate limit rules — read before running

- Do NOT run python main.py repeatedly — wait at least 60 seconds between runs
- Do NOT run the full pipeline just to test syntax — use py_compile instead
- Do NOT increase max_results beyond 5 on the free tier
- To test Agent 1 only, comment out filter_agent and filter_task from the Crew

Syntax check without making any API calls:
python -m py_compile agents.py
python -m py_compile tasks.py
python -m py_compile main.py

---

## LLM configuration

Large model — used for Agents 2, 3, 4 (reasoning-heavy tasks):
llm_large = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.2,
    max_retries=3,
)

# Fetcher model — used for Agent 1 (tool-calling reliability)
# GPT-4o Mini is used here instead of Groq because Llama 3.3 70B
# was unreliably skipping tool calls and hallucinating papers from
# training knowledge. GPT-4o Mini has superior tool-calling compliance.
llm_fetcher = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.2,
    max_retries=3,
)

Fast model — available for Agent 1 or formatting tasks if needed:
llm_fast = ChatGroq(model="llama-3.1-8b-instant", temperature=0.2)
(currently commented out — not in use)

---

## Known issues and workarounds

cache_breakpoint bug
CrewAI adds an Anthropic-specific cache marker that Groq rejects with an API error. Fixed via monkey-patch at the top of main.py before any CrewAI imports. Do not move, remove, or reorder this patch.

JSON fence wrapping
LLMs sometimes wrap JSON output in json fences despite instructions. If this reappears, strip it in main.py before json.loads():
raw = result.raw.strip().removeprefix("```json").removesuffix("```").strip()

Abstract truncation
Abstracts are cut to 200 chars in tools.py intentionally. Do not increase without recalculating the token budget first.

---

## How to run

source venv/bin/activate          — activate environment first
python main.py                    — full pipeline run
python test_arxiv.py              — data layer only, no LLM, no API cost
python -m py_compile agents.py   — syntax check, no API call

---

## What you must never do

- Run python main.py to verify a change — use py_compile instead
- Reorder imports in main.py — the monkey-patch order is load-bearing
- Simplify the filter_task description — every constraint is intentional
- Remove the hallucination ID check from main.py
- Add tools to Agent 2 — it is intentionally tool-free
- Change the data contract field names between agents
- Suggest paid LLMs or paid APIs — this project is free tier only
- Modify test_arxiv.py — it is a verification script, not pipeline code
- Read, print, or log the contents of .env
- Use llm_large on the fetcher_agent — it must stay on llm_fetcher (GPT-4o Mini) due to tool-calling reliability requirements

---

## Behaviour rules for Claude Code

- Do NOT write or suggest code unprompted
- Do NOT run python main.py to test changes
- WAIT for an explicit instruction before doing anything
- When given an error, diagnose the cause before suggesting a fix
- When asked to make a change, make only that change — nothing else
- After any file edit, show the complete final file for verification
- If a requested change conflicts with a key technical decision above, flag it and explain why before proceeding
