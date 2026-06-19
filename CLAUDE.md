# ArXiv Research Digest Agent — Claude Code Guidelines

## Project overview

A multi-agent AI pipeline built with CrewAI that fetches recent ArXiv papers on a topic, filters them for relevance, clusters them by theme, writes a structured newsletter digest, and exports it as a styled PDF.

**Environment:** macOS · Python 3.11.9 · virtualenv (venv/) · VS Code
**LLM:** Agents 1, 3 — OpenAI gpt-4o-mini · Agents 2, 4 — Groq llama-3.3-70b-versatile
**All dependencies:** installed via requirements.txt

---

## File structure

| File | Purpose |
|---|---|
| `.env` | GROQ_API_KEY and OPENAI_API_KEY — never read, print, or log these |
| `agents.py` | All CrewAI Agent definitions + LLM config |
| `tasks.py` | All CrewAI Task definitions + context chaining |
| `tools.py` | Custom ArxivSearchTool (BaseTool subclass) |
| `main.py` | Crew entry point — runs all 4 agents, validates, saves outputs |
| `validators.py` | Output validation for all 4 agents |
| `renderer.py` | PDF generation via fpdf2 — Anthropic-inspired coral colour scheme |
| `test_arxiv.py` | Standalone ArXiv API test — no LLM, no cost |
| `outputs/` | JSON cluster and markdown/PDF digest outputs saved here |
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

Agent 3 — Thematic Clusterer
  Tools: none — reasons purely on context from Agent 2
  Job:  groups filtered papers into 2-5 named research themes,
        returns structured JSON with theme names, descriptions, paper lists
  Out:  JSON object with themes array + total_papers + total_themes

        down-arrow context=[cluster_task]

Agent 4 — Digest Writer
  Tools: none — reasons purely on context from Agent 3
  Job:  writes newsletter in markdown with intro, theme sections,
        spotlight paper, and what-to-watch outlook paragraph
  Out:  clean markdown string

        down-arrow (not an agent)

PDF Renderer — renderer.py
  Deterministic Python function, no LLM involved
  Converts markdown to styled PDF using fpdf2
  Saves to outputs/digest_YYYY-MM-DD.pdf

Validators — validators.py
  validate_filter_output  — hallucination ID check for Agent 2
  validate_date_window    — date range check for Agent 1 fetched papers
  validate_cluster_output — structure + ID + duplicate check for Agent 3
  validate_writer_output  — section presence check for Agent 4

---

## Current build state

| Component | Status | Notes |
|---|---|---|
| Agent 1 Fetcher | COMPLETE | Verified returning real ArXiv papers |
| Agent 2 Filter and Scorer | COMPLETE | Hallucination fix applied, ID check in validators.py |
| Agent 3 Clusterer | COMPLETE | On GPT-4o Mini — Llama ignored theme count constraints |
| Agent 4 Digest Writer | COMPLETE | On Groq Llama — writing task, no tool-calling needed |
| PDF Renderer | COMPLETE | Coral/Anthropic colour scheme, fpdf2 |
| Validators | COMPLETE | All 4 agents validated in validators.py |
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
When main.py imports agents.py, Python immediately executes it including LLM() — before main.py's own load_dotenv() runs. Without this, Groq throws a missing API key error on import.

2. Filter agent has max_iter=2
Intentionally low. This agent has a simple, well-defined job. If it cannot complete in 2 steps the prompt is the problem — not the iteration count. Raising max_iter here masks prompt issues rather than fixing them.

3. Filter task description contains strict grounding instructions
Agent 2 was hallucinating fabricated papers using training knowledge instead of scoring the actual fetched papers. Every constraint in the description is load-bearing. Do not simplify or shorten it.

4. context=[prior_task] — not manual passing
CrewAI injects the prior task's raw output automatically when context is set. Manually extracting and passing output creates duplication and breaks flow.

5. Hallucination ID check in validators.py
validate_filter_output diffs IDs from fetch_task.output.raw against the filter output. Any returned ID not in the fetched set is a fabricated paper. This is a hard verification step — do not remove it.

6. Abstract truncation to 200 chars in tools.py
Keeps token usage within Groq's 12,000 TPM free tier limit. Full abstracts at 20 papers would risk hitting the per-minute window.

7. Monkey-patch in main.py before CrewAI imports
CrewAI adds an Anthropic-specific cache marker that Groq rejects. The patch must run before any CrewAI import. Import order in main.py is load-bearing — do not reorder imports.

8. Temperature set to 0.2 across all agents
Lower temperature = more deterministic output = more reliable JSON structure. Do not raise above 0.3.

9. Agents 1 and 3 use GPT-4o Mini (OpenAI) not Groq Llama
Agent 1: Llama 3.3 70B was hallucinating papers by skipping the arxiv_search tool call entirely. GPT-4o Mini has significantly more reliable tool-calling behaviour.
Agent 3: Llama 3.3 70B consistently ignored the minimum-papers-per-theme constraint across 3+ runs, defaulting to 3 themes regardless of prompt position or framing. GPT-4o Mini follows the constraint correctly.
Agents 2 and 4 remain on Groq Llama — they do not require strict instruction compliance on counting/tool-calling.

10. validate_cluster_output may inject "Other Notable Work" theme
If Agent 3 produces a theme with only 1 paper, the validator moves that paper into a catch-all "Other Notable Work" theme. This modification happens AFTER Agent 4 has already run, so validate_writer_output excludes "Other Notable Work" from its theme presence check — Agent 4 never saw that theme.

11. renderer.py uses safe_text() for all PDF output
Helvetica (fpdf2's built-in font) is Latin-1 only. smart quotes, em dashes, ellipsis, and emoji all cause UnicodeEncodeError. safe_text() replaces these before any cell/multi_cell call. Do not pass raw LLM output directly to fpdf2 without safe_text().

---

## Rate limit — Groq free tier

Limit: 12,000 tokens per minute (TPM) · 30 requests per minute
Model: llama-3.3-70b-versatile

| Agent | Estimated tokens |
|---|---|
| Agent 2 Filter | ~6,000 (heaviest — processes all abstracts) |
| Agent 4 Writer | ~4,000 |
| Full pipeline Groq total (Agents 2 + 4) | ~10,000 across 3-4 minutes runtime |

Agents 1 and 3 are on OpenAI — not counted here.

---

## Rate limit — OpenAI (Agents 1 and 3)

Model: gpt-4o-mini
Free credit: $5 on signup — approximately 2,000+ runs
Monitor usage at: platform.openai.com → Settings → Billing

| Agent | Platform | Model |
|---|---|---|
| Agent 1 Fetcher | OpenAI | gpt-4o-mini |
| Agent 2 Filter | Groq | llama-3.3-70b-versatile |
| Agent 3 Clusterer | OpenAI | gpt-4o-mini |
| Agent 4 Writer | Groq | llama-3.3-70b-versatile |

---

## Rate limit rules — read before running

- Do NOT run python main.py repeatedly — wait at least 60 seconds between runs
- Do NOT run the full pipeline just to test syntax — use py_compile instead
- Do NOT increase max_results beyond 10 on the free tier
- To test Agent 1 only, comment out agents 2-4 and their tasks from the Crew

Syntax check without making any API calls:
python -m py_compile agents.py
python -m py_compile tasks.py
python -m py_compile main.py
python -m py_compile validators.py
python -m py_compile renderer.py

---

## LLM configuration

Large model — used for Agents 2, 4 (reasoning-heavy, no tool-calling):
llm_large = LLM(
    model="groq/llama-3.3-70b-versatile",
    temperature=0.2,
)

Fetcher/compliance model — used for Agents 1, 3 (tool-calling + strict instruction following):
llm_fetcher = LLM(
    model="openai/gpt-4o-mini",
    temperature=0.2,
    max_retries=3,
)

---

## Known issues and workarounds

cache_breakpoint bug
CrewAI adds an Anthropic-specific cache marker that Groq rejects with an API error. Fixed via monkey-patch at the top of main.py before any CrewAI imports. Do not move, remove, or reorder this patch.

Doubled-brace JSON artifact
LLMs sometimes return {{ and }} as outermost braces instead of { and }. validate_cluster_output strips these before json.loads() using a while loop. If this reappears for other agents, apply the same strip pattern.

JSON fence wrapping
LLMs sometimes wrap JSON output in ```json fences despite instructions. If this reappears, strip it before json.loads():
raw = result.raw.strip().removeprefix("```json").removesuffix("```").strip()

Abstract truncation
Abstracts are cut to 200 chars in tools.py intentionally. Do not increase without recalculating the token budget first.

fpdf2 Latin-1 encoding
Helvetica does not support emoji or Unicode characters above U+00FF. Always pass text through safe_text() before rendering to PDF.

---

## How to run

source venv/bin/activate          — activate environment first
python main.py                    — full pipeline run (all 4 agents + PDF)
python renderer.py                — re-render PDF from existing digest .md
python test_arxiv.py              — data layer only, no LLM, no API cost
python -m py_compile agents.py   — syntax check, no API call

---

## What you must never do

- Run python main.py to verify a change — use py_compile instead
- Reorder imports in main.py — the monkey-patch order is load-bearing
- Simplify the filter_task description — every constraint is intentional
- Remove the hallucination ID check from validators.py
- Add tools to Agents 2, 3, or 4 — they are intentionally tool-free
- Change the data contract field names between agents
- Suggest adding more paid API providers without asking — Agents 1 and 3 use OpenAI intentionally; do not expand further without asking
- Modify test_arxiv.py — it is a verification script, not pipeline code
- Read, print, or log the contents of .env
- Use llm_large on fetcher_agent or cluster_agent — both must stay on llm_fetcher (GPT-4o Mini) due to tool-calling and instruction-compliance requirements
- Pass raw LLM text directly to fpdf2 — always use safe_text() first

---

## Behaviour rules for Claude Code

- Do NOT write or suggest code unprompted
- Do NOT run python main.py to test changes
- WAIT for an explicit instruction before doing anything
- When given an error, diagnose the cause before suggesting a fix
- When asked to make a change, make only that change — nothing else
- If a requested change conflicts with a key technical decision above, flag it and explain why before proceeding
