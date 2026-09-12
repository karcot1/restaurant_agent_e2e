import os
import json
import logging
import urllib.request
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
import google.auth
import google.auth.transport.requests

# Initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cloud-run-frontend")

# Read environment variables
PROJECT_ID = os.environ.get("PROJECT_ID")
LOCATION = os.environ.get("LOCATION")
ENGINE_ID = os.environ.get("REASONING_ENGINE_ID")

def query_reasoning_engine(message: str, user_id: str = "default_user") -> str:
    """Queries the Vertex AI Reasoning Engine endpoint directly."""
    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    auth_req = google.auth.transport.requests.Request()
    credentials.refresh(auth_req)
    access_token = credentials.token

    url = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}/reasoningEngines/{ENGINE_ID}:query"
    payload = {
        "classMethod": "agent_run",
        "input": {
            "user_id": user_id,
            "message": message
        }
    }
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "x-goog-user-project": PROJECT_ID
    }

    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=60) as response:
        res_body = json.loads(response.read().decode("utf-8"))

    # Extract human-readable text from the ADK output
    output = res_body.get("output", res_body)
    if isinstance(output, list):
        extracted_texts = []
        for item in output:
            if isinstance(item, dict) and "content" in item and "parts" in item["content"]:
                for part in item["content"]["parts"]:
                    if isinstance(part, dict) and "text" in part:
                        extracted_texts.append(part["text"])
        if extracted_texts:
            return "".join(extracted_texts)
    elif isinstance(output, dict) and "text" in output:
        return output["text"]

    return str(output)

app = FastAPI()

# 💡 A clean, modern HTML Template utilizing Tailwind CSS for the Chat UI
CHAT_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>A2A Agent Console</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-100 flex flex-col h-screen font-sans">
    
    <!-- Header -->
    <header class="bg-emerald-800 text-white p-4 shadow-md flex items-center justify-between">
        <h1 class="text-xl font-bold flex items-center gap-2">🤖 A2A Console</h1>
        <span class="text-xs bg-emerald-900 px-3 py-1 rounded-full border border-emerald-700">Engine ID: {engine_id}</span>
    </header>

    <!-- Chat Container -->
    <main class="flex-grow p-4 md:p-8 flex flex-col max-w-4xl w-full mx-auto justify-between h-0">
        
        <!-- Conversation Log -->
        <section id="chat-log" class="bg-white rounded-lg shadow-inner border border-slate-200 flex-grow overflow-y-auto p-4 mb-4 space-y-4">
            <div class="flex justify-start">
                <div class="bg-slate-100 border border-slate-200 text-slate-800 rounded-lg px-4 py-2 max-w-lg shadow-sm">
                    Hello! I am your A2A Orchestrator Agent. Ask me a question, and I will coordinate with downstream agents to assist you.
                </div>
            </div>
            {chat_history}
        </section>

        <!-- Message Input -->
        <form method="POST" action="/" class="flex space-x-2">
            <input 
                type="text" 
                name="user_message" 
                placeholder="Ask your agent a question..." 
                required 
                class="flex-grow border border-slate-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-600 bg-white"
            />
            <button 
                type="submit" 
                class="bg-emerald-700 hover:bg-emerald-800 text-white font-bold px-6 py-2 rounded-lg transition duration-200 shadow"
            >
                Send
            </button>
        </form>
    </main>
</body>
</html>
"""

# Store simple in-memory session chat logs (for demonstration purposes)
chat_history_store = []

@app.get("/", response_class=HTMLResponse)
async def home_page():
    return build_chat_ui()

@app.post("/", response_class=HTMLResponse)
async def query_agent(user_message: str = Form(...)):
    try:
        logger.info(f"Querying reasoning engine with message: {user_message}")
        agent_response = query_reasoning_engine(message=user_message)
        
        # Append message exchanges
        chat_history_store.append(("user", user_message))
        chat_history_store.append(("agent", agent_response))
        
    except Exception as e:
        logger.error(f"Error querying agent runtime: {e}")
        chat_history_store.append(("user", user_message))
        chat_history_store.append(("agent", f"Error occurred: {str(e)}"))

    return build_chat_ui()

def build_chat_ui():
    history_html = ""
    for speaker, text in chat_history_store:
        if speaker == "user":
            history_html += f"""
            <div class="flex justify-end">
                <div class="bg-emerald-700 text-white rounded-lg px-4 py-2 max-w-lg shadow-sm">
                    {text}
                </div>
            </div>
            """
        else:
            history_html += f"""
            <div class="flex justify-start">
                <div class="bg-slate-100 text-slate-800 border border-slate-200 rounded-lg px-4 py-2 max-w-lg shadow-sm">
                    {text}
                </div>
            </div>
            """
    return CHAT_HTML.format(engine_id=ENGINE_ID, chat_history=history_html)