import os
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
from agents import fetcher_agent
from tasks import fetch_task

load_dotenv()

# These are the runtime variables that get injected into the task description in tasks.py
# Anywhere you see {topic} or {category} in tasks.py, crewAI replaces those with these values
# This happens when .kickoff() is called — how you control what the agent searches for without touching the agent or task definitions
inputs = {
    "topic": "retrieval augmented generation",
    "category": "cs.AI",
    "days_back": 7,
    "max_results": 10,
}

crew = Crew(
    agents=[fetcher_agent],  # list of workers available
    tasks=[fetch_task],  # list of jobs to do
    process=Process.sequential,
    verbose=True
)

if __name__ == "__main__":
    print("\n=== Running Agent 1: Fetcher ===\n")
    result = crew.kickoff(inputs=inputs)
    print("\n=== Raw output ===\n")
    print(result.raw)
