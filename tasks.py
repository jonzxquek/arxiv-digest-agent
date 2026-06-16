from crewai import Task
from agents import fetcher_agent

fetch_task = Task(
    description=(
        "Search ArXiv for recent papers on the topic: '{topic}'.\n"
        "Use the category: '{category}'.\n"
        "Look back '{days_back}' days.\n"
        "Fetch up to 50 papers.\n"
        "Return the full list of papers as a JSON array. "
        "Do not summarise or filter — return everything you find."
    ),
    expected_output=(
        "A JSON array of paper objects. Each object must have: "
        "id, title, authors, abstract, published date, and url."
        ),
    agent = fetcher_agent,
)
