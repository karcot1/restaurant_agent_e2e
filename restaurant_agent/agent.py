# restaurant_agent/agent.py
import asyncio
import json
import random
import os
from functools import cached_property
from google.cloud import secretmanager
from google.auth import default
from google.auth.transport.requests import Request as AuthRequest
from google.genai import Client
from google.adk.agents import LlmAgent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from google.adk.models.google_llm import Gemini
from toolbox_adk import ToolboxToolset, CredentialStrategy
import httpx
from a2a.client.client import ClientConfig as A2AClientConfig
from a2a.client.client_factory import ClientFactory as A2AClientFactory
from a2a.types import TransportProtocol as A2ATransport

# Load config (support both local repo root and container /app)
config_path = "restaurant_agent/config.json" if os.path.exists("restaurant_agent/config.json") else "config.json"
with open(config_path) as f:
    llm_config = json.load(f)

PROJECT_ID = llm_config["PROJECT_ID"]
MODEL = llm_config["MODEL"]
MODEL_REGION = llm_config["MODEL_REGION"]
TOOLBOX_URL = llm_config["TOOLBOX_URL"]

# Vertex AI Reasoning Engine A2A Agent Card endpoint
RESERVATION_AGENT_CARD_URL = "https://us-central1-aiplatform.googleapis.com/v1beta1/projects/gapinc-sandbox/locations/us-central1/reasoningEngines/2160440842777526272/a2a/v1/card"

toolbox = ToolboxToolset(
    server_url=TOOLBOX_URL,
    credentials=CredentialStrategy.workload_identity(
        target_audience=TOOLBOX_URL,
    ),
)

# Override Gemini class for global endpoint compatibility
class GlobalGemini(Gemini):
    @cached_property
    def api_client(self) -> Client:
        return Client(vertexai=True, location="global")

# Initialize LLM
llm_model = GlobalGemini(model=MODEL) if MODEL_REGION == "global" else Gemini(model=MODEL)

class GoogleCloudAuth(httpx.Auth):
    """Auto-refreshing Google Cloud authentication for httpx.

    Refreshes the access token before each request if expired,
    so long-running agents never hit 401 errors.
    """

    def __init__(self):
        self.credentials, _ = default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )

    def auth_flow(self, request):
        # Refresh the token if it is expired or missing
        if not self.credentials.valid:
            self.credentials.refresh(AuthRequest())
            
        request.headers["Authorization"] = f"Bearer {self.credentials.token}"
        yield request


class AuthRemoteA2aAgent(RemoteA2aAgent):
    """RemoteA2aAgent with per-event-loop httpx.AsyncClient and Google Cloud Auth."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._bound_loop = None

    async def _ensure_httpx_client(self, *args, **kwargs) -> httpx.AsyncClient:
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        if not self._httpx_client or self._httpx_client.is_closed or self._bound_loop != current_loop:
            self._httpx_client = httpx.AsyncClient(
                auth=GoogleCloudAuth(),
                timeout=httpx.Timeout(timeout=self._timeout),
            )
            self._bound_loop = current_loop
            self._httpx_client_needs_cleanup = True
            client_config = A2AClientConfig(
                httpx_client=self._httpx_client,
                streaming=False,
                polling=False,
                supported_transports=[A2ATransport.jsonrpc, A2ATransport.http_json],
            )
            self._a2a_client_factory = A2AClientFactory(config=client_config)
            if self._agent_card:
                self._a2a_client = self._a2a_client_factory.create(self._agent_card)
        return self._httpx_client

    async def _ensure_resolved(self, *args, **kwargs):
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        if self._bound_loop != current_loop:
            self._is_resolved = False
            self._a2a_client = None

        return await super()._ensure_resolved(*args, **kwargs)


reservation_remote_agent = AuthRemoteA2aAgent(
    name="reservation_agent",
    description="Handles restaurant table reservations — create, check, and cancel bookings. Delegate to this agent when the user wants to book a table, check a reservation, or cancel a reservation.",
    agent_card=RESERVATION_AGENT_CARD_URL,
)

root_agent = LlmAgent(
    name="restaurant_agent",
    model=llm_model,
    instruction="""You are a friendly and knowledgeable concierge at "Foodie Finds," a restaurant. Your job:
- Help diners browse the menu by category or cuisine type.
- Provide full details about specific dishes, including ingredients, price, and dietary information.
- Recommend dishes based on natural language descriptions of what the diner is craving.
- Add new menu items when asked.
- For reservation requests (booking, checking, or cancelling tables), delegate to the reservation_agent.

When a diner asks about a specific dish by name or cuisine, use the get-item-details tool.
When a diner asks for a specific category or cuisine type, use the search-menu tool.
When a diner describes what kind of food they want — by flavor, texture, dietary needs, or cravings — use the search-menu-by-description tool for semantic search.

When in doubt between search-menu and search-menu-by-description, prefer search-menu-by-description — it searches dish descriptions and finds more relevant matches.
If a dish is not available (available is false), let the diner know and suggest similar alternatives from the search results.
Be conversational, knowledgeable, and concise.""",
    tools=[toolbox],
    sub_agents=[reservation_remote_agent],
)