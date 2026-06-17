# ArXiv Digest Agent

A CrewAI-powered agent that fetches recent research papers from ArXiv on a given topic and returns them as a structured JSON list.

## What it does

- Searches ArXiv for papers published within a configurable number of days
- Filters by research category (e.g. `cs.AI`, `cs.LG`, `cs.CL`)
- Returns paper title, authors, abstract, published date, and URL
- Powered by Groq's `llama-3.3-70b-versatile` model via LiteLLM

## Project structure

```
main.py       # Entry point — configures inputs and kicks off the crew
agents.py     # Defines the LLM-powered fetcher agent
tasks.py      # Defines the task/instructions given to the agent
tools.py      # Defines the ArXiv search tool the agent can call
```

## Setup

1. Clone the repo and create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the root directory:
```
GROQ_API_KEY=your_key_here
```
Get your free API key at [console.groq.com](https://console.groq.com).

## Usage

Configure your search in `main.py`:

```python
inputs = {
    "topic": "retrieval augmented generation",
    "category": "cs.AI",
    "days_back": 7,
    "max_results": 10,
}
```

Then run:
```bash
python main.py
```

## Dependencies

- [CrewAI](https://github.com/crewAIInc/crewAI) — agent orchestration
- [LiteLLM](https://github.com/BerriAI/litellm) — LLM provider routing
- [arxiv](https://github.com/lukasschwab/arxiv.py) — ArXiv API client
- [LangChain Groq](https://github.com/langchain-ai/langchain) — Groq integration
