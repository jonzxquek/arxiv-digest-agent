import arxiv # Importing the ArXiv python library that talks to the API
import json
from datetime import datetime, timedelta, timezone
from crewai.tools import BaseTool # The base class your tool inherits from
from pydantic import BaseModel, Field # For defining and validating the tool's inputs

class ArxivSearchInput(BaseModel):
    topic: str = Field(description="The research topic to search for")
    category: str = Field(description="ArXiv category code e.g. cs.AI, cs.LG, cs.CL")
    days_back: int = Field(description="How many days back to search")
    max_results: int = Field(description="Maximum number of papers to fetch")

# Defines what inputs the tool accepts and their types. The description fields are important - theyre not just documentation
# The LLM actually reads them to udnerstand what value to pass for each argument
# Pydantic validates that the LLM passes the right types before _run() is even called

class ArxivSearchTool(BaseTool):
    name: str = "arxiv_search" # How the LLM refers to this tool when it decides to call it
    description: str = (
        "Searches ArXiv for recent research papers on a given topic. "
        "Returns a list of papers with title, authors, abstract, and URL"
    ) # What the LLM reads to decide whether to use this tool at all
    args_schema: type[BaseModel] = ArxivSearchInput # Links the input schema above so CrewAI knows what arguements to expect and validate

    def _run(self, topic: str, category: str, days_back: int = 7, max_results: int = 50) -> str: # Actual logic
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

        search = arxiv.Search(
            query=f"{topic} AND cat:{category}",
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending,
        )
        # Builds the ArXiv search query. AND cat:{catergory} filters by catergory (eg.cs.AI). Results are sorted newest first

        papers = []
        client = arxiv.Client()

        for result in client.results(search):
            if result.published < cutoff:
                break
            papers.append({
                "id":        result.entry_id,
                "title":     result.title,
                "authors":   [a.name for a in result.authors[:3]],
                "abstract":  result.summary.replace("\n", " ").strip()[:200],
                "published": result.published.strftime("%Y-%m-%d"),
            })

        if not papers:
            return "No papers found for this topic and date range."

        return json.dumps(papers, indent=2)
        # Converts the list of paper dicts into a formatted JSON string and returns it to the LLM
