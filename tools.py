import arxiv
import json
from datetime import datetime, timedelta, timezone
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

class ArxivSearchInput(BaseModel):
    topic: str = Field(description="The research topic to search for")
    category: str = Field(description="ArXiv category code e.g. cs.AI, cs.LG, cs.CL")
    days_back: int = Field(description="How many days back to search")
    max_results: int = Field(description="Maximum number of papers to fetch")

class ArxivSearchTool(BaseTool):
    name: str = "arxiv_search"
    description: str = (
        "Searches ArXiv for recent research papers on a given topic. "
        "Returns a list of papers with title, authors, abstract, and URL"
    )
    args_schema: type[BaseModel] = ArxivSearchInput

    def _run(self, topic: str, category: str, days_back: int = 7, max_results: int = 50) -> str:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

        search = arxiv.Search(
            query=f"{topic} AND cat:{category}",
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending,
        )

        papers = []
        client = arxiv.Client()

        for result in client.results(search):
            if result.published < cutoff:
                break
            papers.append({
                "id":        result.entry_id,
                "title":     result.title,
                "authors":   [a.name for a in result.authors[:3]],
                "abstract":  result.summary.replace("\n", " ").strip(),
                "published": result.published.strftime("%Y-%m-%d"),
                "url":       result.entry_id,
            })

        if not papers:
            return "No papers found for this topic and date range."

        return json.dumps(papers, indent=2)
