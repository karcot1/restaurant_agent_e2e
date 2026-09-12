import inspect
import json
import logging
import os
import uvicorn
from fastapi import FastAPI, Request, encoders, responses
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

# Sync engine id if provided under REASONING_ENGINE_ID
REASONING_ENGINE_ID = os.environ.get("GOOGLE_CLOUD_AGENT_ENGINE_ID") or os.environ.get("REASONING_ENGINE_ID")
if not os.environ.get("GOOGLE_CLOUD_AGENT_ENGINE_ID") and REASONING_ENGINE_ID:
    os.environ["GOOGLE_CLOUD_AGENT_ENGINE_ID"] = REASONING_ENGINE_ID

if REASONING_ENGINE_ID and PROJECT_ID and LOCATION:
    agent_card.url = f"https://{LOCATION}-aiplatform.googleapis.com/v1beta1/projects/{PROJECT_ID}/locations/{LOCATION}/reasoningEngines/{REASONING_ENGINE_ID}/a2a"

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

# Mount well-known agent card endpoints across all path prefixes
@app.get("/.well-known/agent-card.json")
@app.get("/.well-known/agent.json")
@app.get("/a2a/.well-known/agent-card.json")
@app.get("/a2a/.well-known/agent.json")
@app.get("/api/.well-known/agent-card.json")
@app.get("/api/.well-known/agent.json")
@app.get("/api/a2a/.well-known/agent-card.json")
@app.get("/api/a2a/.well-known/agent.json")
async def well_known_agent_card():
    return agent_card.model_dump(exclude_none=True, by_alias=True)

# Mount standard A2A protocol routes across all path prefixes used by Vertex AI proxies
# Vertex AI Reasoning Engine prefixes incoming requests with /api
for prefix in ["", "/a2a", "/api", "/api/a2a"]:
    for (path, method), handler in a2a_agent.a2a_rest_adapter.routes().items():
        app.add_api_route(f"{prefix}{path}", handler, methods=[method])

def _encode_chunk_to_json(chunk):
    try:
        json_chunk = encoders.jsonable_encoder(chunk)
        return json.dumps(json_chunk) + "\n"
    except Exception:
        logging.exception("Failed to encode chunk")
        return None

async def json_generator(output):
    if hasattr(output, "__aiter__"):
        async for chunk in output:
            encoded_chunk = _encode_chunk_to_json(chunk)
            if encoded_chunk is not None:
                yield encoded_chunk
    else:
        for chunk in output:
            encoded_chunk = _encode_chunk_to_json(chunk)
            if encoded_chunk is not None:
                yield encoded_chunk

@app.post("/api/reasoning_engine")
async def query(request: Request) -> responses.JSONResponse:
    request_json = await request.json()
    class_method = request_json.get("class_method")
    input_val = request_json.get("input") or {}

    if class_method == "handle_authenticated_agent_card":
        card_data = await a2a_agent.handle_authenticated_agent_card(request, None)
        return responses.JSONResponse(content=encoders.jsonable_encoder({"output": card_data}))

    method = getattr(a2a_agent, class_method, None)
    if method:
        try:
            if inspect.iscoroutinefunction(method):
                output = await method(request, None)
            else:
                output = method(request, None)
        except TypeError:
            if inspect.iscoroutinefunction(method):
                output = await method(**input_val)
            else:
                output = method(**input_val)
        return responses.JSONResponse(content=encoders.jsonable_encoder({"output": output}))
    return responses.JSONResponse(status_code=400, content={"error": f"Method {class_method} not found"})

@app.post("/api/stream_reasoning_engine")
async def stream_query(request: Request) -> responses.StreamingResponse:
    request_json = await request.json()
    class_method = request_json.get("class_method")
    method = getattr(a2a_agent, class_method)
    output = method(request, None)
    return responses.StreamingResponse(
        content=json_generator(output),
        media_type="application/json",
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))