from dotenv import load_dotenv
load_dotenv()

from crewai import Agent, LLM
#agent - crewAI's class for building an LLM-powered worker
#LLM - crewAI's wrapper for connecting to a language model
from tools import ArxivSearchTool
#Tool defined in tools.py, imported herer so it can be handed to the agent

llm_large = LLM(
    model="groq/llama-3.3-70b-versatile",
    temperature=0.2
)
#configures the language model the agent
#temperature controls how "creative" the LLM is.
# 0 = very deterministic and consistent
# 1 = more random and varied

llm_fetcher = LLM(
    model="openai/gpt-4o-mini",
    temperature=0.2,
    max_retries=3,
)

arxiv_tool = ArxivSearchTool()
# Calling a class to create an object. Agent cant use class itself, needs a live instance

fetcher_agent = Agent(
    role="ArXiv Research Fetcher", #Gives LLM a job title and how it behaves

    goal=(
        "Fetch the most recent and relevant research papers from ArXiv "
        "on the given topic and return them as a clean structured list"
    ),
    # Tells the LLM what its trying to achieve on this run

    backstory=(
        "You are a precise research librarian with deep knowledge of academic "
        "publishing. You retrieve papers efficiently and return clean and complete "
        "data without summarising or editorialising - your job is data retrieval, "
        "not analysis."
    ),
    # Persona detail. This is where you shape how the LLM approaches the task - in this case, "dont summarise, just retrieve data"

    tools=[arxiv_tool], # Tool used from instance created from imported class (from tools.py)
    llm=llm_fetcher, # Connects it to the model we configured above
    verbose=True, # # Prints each step the agent takes to the terminal 
    max_iter=3 # the agent is allowed a maximum of 3 thinking/tool-calling loops before its forced to return an answer.
)



filter_agent = Agent(
    role="Research Relevance Scorer",
    goal=("Score each paper for relevance to the research topic and return "
          "only the highest quality, most relevant papers as a clean JSON list."
    ),
    backstory=("You are a rigorous academic peer reviewer with expertise in machine "
               "learning and AI research. You can quickly assess whether a paper is "
               "genuinely relevant to a topic or merely tangentially related. "
               "You are strict - you would rather return 10 excellent papers than "
               "20 mediocre ones. You always return valid JSON."
    ),
    llm=llm_large,
    verbose=True,
    max_iter=2,
    # No tools parameter - this agent reasons entirely on the context passed to it
    # No external calls are needed. Max iterations = 2 is intentionally low because this agent has a simple
    # well defined job - if it cant do it in 2 steps the prompt is not the problem
)


cluster_agent = Agent(
    role = "Research thematic analyst",
    goal = (
        "Group the provided research papers into clear, meaningful themes"
        "that reflect genuine research directions emerging this week."
    ),
    backstory = (
        "You are a senior AI research analyst who reads hundreds of papers "
        "weekly. You have a talent for spotting when multiple research teams "
        "are independently converging on the same problem from different angles. "
        "You identify themes from evidence in the papers themselves — never from "
        "assumptions or prior knowledge. You always return valid JSON."
    ),
    llm = llm_fetcher,
    verbose = True,
    max_iter = 2
)


writer_agent = Agent(
    role = "Ai Research Newsletter Writer",
    goal = (
        "Transform a structured cluster of research papers into a compelling, "
        "well-written weekly newsletter digest that a working AI researcher "
        "would find genuinely useful."
    ),
    backstory = (
        "You are a senior science communicator with a PhD in machine learning "
        "and 8 years of experience writing for publications like Import AI, "
        "The Batch, and Alpha Signal. You have a talent for spotting what "
        "actually matters in a week's worth of papers and expressing it clearly "
        "without oversimplifying. You write with authority and precision. "
        "You never pad your writing with filler phrases like 'it is worth noting' "
        "or 'this is an exciting development'. Every sentence earns its place. "
        "You always write in clean markdown with no JSON, no code blocks, "
        "and no raw IDs."
    ),
    llm = llm_large,
    verbose = True,
    max_iter = 2
)