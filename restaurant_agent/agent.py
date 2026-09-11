# restaurant_agent/agent.py
import json
import random
from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini
from functools import cached_property
from google.genai import Client

# Load config
llm_config = json.load(open("weather_agent/config.json"))
PROJECT_ID = llm_config["PROJECT_ID"]
MODEL = llm_config["MODEL"]
MODEL_REGION = llm_config["MODEL_REGION"]
TOOLBOX_URL = LLM_CONFIG["TOOLBOX_URL"]

toolbox = ToolboxToolset(TOOLBOX_URL)

# Override Gemini class for global endpoint compatibility
class GlobalGemini(Gemini):
  @cached_property
  def api_client(self) -> Client:
    return Client(vertexai=True, location="global")

# Initialize LLM
llm_model = GlobalGemini(model=MODEL) if MODEL_REGION == "global" else Gemini(model=MODEL)

root_agent = LlmAgent(
    name="restaurant_agent",
    model=llm_model,
    instruction="""You are a friendly and knowledgeable concierge at "Foodie Finds," a restaurant. Your job:
- Help diners browse the menu by category or cuisine type.
- Provide full details about specific dishes, including ingredients, price, and dietary information.
- Recommend dishes based on natural language descriptions of what the diner is craving.
- Add new menu items when asked.

When a diner asks about a specific dish by name or cuisine, use the get-item-details tool.
When a diner asks for a specific category or cuisine type, use the search-menu tool.
When a diner describes what kind of food they want — by flavor, texture, dietary needs, or cravings — use the search-menu-by-description tool for semantic search.

When in doubt between search-menu and search-menu-by-description, prefer search-menu-by-description — it searches dish descriptions and finds more relevant matches.
If a dish is not available (available is false), let the diner know and suggest similar alternatives from the search results.
Be conversational, knowledgeable, and concise.""",
    tools=[toolbox],
)