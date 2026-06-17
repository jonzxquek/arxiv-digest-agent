from crewai import Agent, LLM
from tools import ArxivSearchTool

llm_large = LLM(
    model="groq/llama-3.3-70b-versatile",
    temperature=0.2
)

arxiv_tool = ArxivSearchTool()

fetcher_agent = Agent(
    role="ArXiv Research Fetcher",
    goal=(
        "Fetch the most recent and relevant research papers from ArXiv "
        "on the given topic and return them as a clean structured list"
    ),
    backstory=(
        "You are a precise research librarian with deep knowledge of academic "
        "publishing. You retrieve papers efficiently and return clean and complete "
        "data without summarising or editorialising - your job is data retrieval, "
        "not analysis."
    ),
    tools=[arxiv_tool],
    llm=llm_large,
    verbose=True,
    max_iter=3
)
