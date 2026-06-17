import json
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv  # Parses the values in the .env file
#This is a module inside the CrewAI library (not your code). CrewAI built a prompt caching feature specifically for Anthropic/Claude models. 
#When an agent sends messages to the LLM, this module stamps a special marker called cache_breakpoint onto the system message
#it's Anthropic's way of saying "cache everything up to this point."
#Problem is CrewAI stamps this marker on all LLM calls, including Groq. Groq's API doesnt know what cache_breakpoint is and immediately rejects the request with
#an error 
import crewai.llms.cache as _crewai_cache
_crewai_cache.mark_cache_breakpoint = lambda msg: msg
#This line replaces CrewAI's mark_cache_breakpoint function with the do-nothing version.
#So when CrewAI tries to stamp a message with the cache marker, it calls our 
#replacement instead — which just hands the message back untouched, with no cache_breakpoint added.
from crewai import Crew, Process
from agents import fetcher_agent, filter_agent
from tasks import fetch_task, filter_task

load_dotenv()

# These are the runtime variables that get injected into the task description in tasks.py
# Anywhere you see {topic} or {category} in tasks.py, crewAI replaces those with these values
# This happens when .kickoff() is called — how you control what the agent searches for without touching the agent or task definitions
inputs = {
    "topic": "retrieval augmented generation",
    "category": "cs.AI",
    "days_back": 30,
    "max_results": 5,
}

crew = Crew(
    agents=[fetcher_agent, filter_agent],  # list of workers available
    tasks=[fetch_task, filter_task],  # list of jobs to do
    process=Process.sequential,
    verbose=True
)

if __name__ == "__main__":
    print("\n=== Running Agents 1 + 2: Fetcher → Filter ===\n")
    result = crew.kickoff(inputs=inputs)

    print("\n=== Raw output from Filter agent ===\n")
    print(result.raw)

    try:
        match = re.search(r'\[.*\]', result.raw, re.DOTALL)
        if not match:
            raise json.JSONDecodeError("No JSON array found", result.raw, 0)
        filtered_papers = json.loads(match.group(0))

        # Pull the fetched task output to compare IDs
        if fetch_task.output is None:
            print("\n⚠️  Fetch task produced no output — cannot verify IDs.")
        else:
            match2 = re.search(r'\[.*\]', fetch_task.output.raw, re.DOTALL)
            fetched_papers = json.loads(match2.group(0)) if match2 else []

            # Date-window check — catches Agent 1 hallucinations (fabricated papers from training data
            # tend to be old; real fetched papers must fall within the requested days_back window)
            cutoff = datetime.now() - timedelta(days=inputs["days_back"] + 1)
            outside_window = [
                p for p in fetched_papers
                if datetime.strptime(p.get("published", "1900-01-01"), "%Y-%m-%d") < cutoff
            ]
            if outside_window:
                print(f"\n⚠️  DATE-WINDOW VIOLATION — {len(outside_window)} fetched paper(s) are outside the {inputs['days_back']}-day window (Agent 1 hallucination suspected):")
                for p in outside_window:
                    print(f"   [{p.get('published', '?')}] {p.get('title', p.get('id', '?'))}")
            else:
                print(f"\n✅ Date-window check passed — all {len(fetched_papers)} fetched papers are within the {inputs['days_back']}-day window.")

            fetched_ids = {p["id"] for p in fetched_papers}
            returned_ids = {p["id"] for p in filtered_papers}

            hallucinated = returned_ids - fetched_ids

            if hallucinated:
                print(f"\n⚠️  HALLUCINATION DETECTED — {len(hallucinated)} fabricated paper(s):")
                for hid in hallucinated:
                    print(f"   {hid}")
            else:
                print(f"\n✅ Valid JSON. {len(filtered_papers)} papers passed — all IDs verified against input.")
                for p in filtered_papers:
                    print(f"  [{p.get('relevance_score', '?')}/10] {p['title']}")

    except json.JSONDecodeError:
        print("\n⚠️  Output was not valid JSON. Check the filter agent's prompt.")
