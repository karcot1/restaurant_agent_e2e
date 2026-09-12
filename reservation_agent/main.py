# reservation_agent/main.py
import os
import uvicorn
from fastapi import FastAPI
import vertexai
from vertexai.preview.reasoning_engines import A2aAgent

# Support both container root (/app/...) and local package imports
try:
    from reservation_agent.a2a_config import agent_card
    from reservation_agent.executor import ReservationAgentExecutor
except ModuleNotFoundError:
    from a2a_config import agent_card
    from executor import ReservationAgentExecutor

app = FastAPI(title="Reservation Agent (A2A)")

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION") or os.environ.get("LOCATION")

vertexai.init(project=PROJECT_ID, location=LOCATION)

# Initialize and set up A2A agent
a2a_agent = A2aAgent(
    agent_card=agent_card,
    agent_executor_builder=ReservationAgentExecutor,
)
a2a_agent.set_up()

# Health check endpoints for Vertex AI Reasoning Engine probes
@app.get("/")
@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

# Mount standard A2A protocol routes from RESTAdapter
for (path, method), handler in a2a_agent.a2a_rest_adapter.routes().items():
    app.add_api_route(path, handler, methods=[method])
    # Also mount with /a2a prefix as used by Vertex AI A2A routing
    app.add_api_route(f"/a2a{path}", handler, methods=[method])

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))