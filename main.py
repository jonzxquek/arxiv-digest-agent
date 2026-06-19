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
from agents import fetcher_agent, filter_agent, cluster_agent, writer_agent
from tasks import fetch_task, filter_task, cluster_task, writer_task

from validators import (
    validate_filter_output,
    validate_date_window,
    validate_cluster_output,
)

load_dotenv()

# These are the runtime variables that get injected into the task description in tasks.py
# Anywhere you see {topic} or {category} in tasks.py, crewAI replaces those with these values
# This happens when .kickoff() is called — how you control what the agent searches for without touching the agent or task definitions
inputs = {
    "topic": "retrieval augmented generation",
    "category": "cs.AI",
    "days_back": 30,
    "max_results": 10,
}

crew = Crew(
    agents=[fetcher_agent, filter_agent, cluster_agent, writer_agent],  # list of workers available
    tasks=[fetch_task, filter_task, cluster_task, writer_task],  # list of jobs to do
    process=Process.sequential,
    verbose=True
)

if __name__ == "__main__":
    print("\n=== Running Agents 1 + 2 + 3 + 4 ===\n")
    result = crew.kickoff(inputs=inputs)

    print("\n=== Validating outputs ===\n")

    filtered_papers = validate_filter_output(
        raw=filter_task.output.raw,
        fetch_raw=fetch_task.output.raw,
    )

    if not filtered_papers:
        print("\n🛑 Stopping — Agent 2 output failed validation.")
        exit()

    validate_date_window(
        papers=json.loads(
            re.search(r'\[.*\]', fetch_task.output.raw, re.DOTALL).group(0)
        ),
        days_back=int(inputs["days_back"]),
    )

    clustered = validate_cluster_output(
        raw=cluster_task.output.raw,
        filtered_papers=filtered_papers,
    )

    if not clustered:
        print("\n🛑 Stopping — Agent 3 output failed validation.")
        exit()

    output_path = f"outputs/cluster_{datetime.now().strftime('%Y-%m-%d')}.json"
    with open(output_path, "w") as f:
        json.dump(clustered, f, indent=2)
    print(f"\n💾 Cluster output saved to {output_path}")

    digest_path = f"outputs/digest_{datetime.now().strftime('%Y-%m-%d')}.md"
    with open(digest_path, "w") as f:
        f.write(writer_task.output.raw)
    print(f"\n💾 Digest saved to {digest_path}")

    print("\n=== Pipeline complete ===\n")