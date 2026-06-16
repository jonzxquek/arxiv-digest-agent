import os
from dotenv import load_dotenv
from crewai import Crew, Process
from agents import fetcher_agent
from tasks import fetch_task

load_dotenv()

inputs = {
    "topic": "retrieval augmented generation",
    "category": "cs.AI",
    "days_back": "7",
}

crew = Crew(
    agents=[fetcher_agent],
    tasks=[fetch_task],
    process=Process.sequential,
    verbose=True
)

if __name__ == "__main__":
    print("\n=== Running Agent 1: Fetcher ===\n")
    result = crew.kickoff(inputs=inputs)
    print("\n=== Raw output ===\n")
    print(result.raw)
