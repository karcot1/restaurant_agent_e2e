# scripts/test_a2a_agent_local.py
import asyncio
import json
import os
from pprint import pprint

from dotenv import load_dotenv
from starlette.requests import Request
from vertexai.preview.reasoning_engines import A2aAgent

from reservation_agent.a2a_config import agent_card
from reservation_agent.executor import ReservationAgentExecutor

load_dotenv()


# --- Helper functions for building mock requests ---

def receive_wrapper(data: dict):
    async def receive():
        byte_data = json.dumps(data).encode("utf-8")
        return {"type": "http.request", "body": byte_data, "more_body": False}
    return receive

def build_post_request(data: dict = None, path_params: dict = None) -> Request:
    scope = {"type": "http", "http_version": "1.1", "headers": [(b"content-type", b"application/json")], "app": None}
    if path_params:
        scope["path_params"] = path_params
    return Request(scope, receive_wrapper(data))

def build_get_request(path_params: dict) -> Request:
    scope = {"type": "http", "http_version": "1.1", "query_string": b"", "app": None}
    if path_params:
        scope["path_params"] = path_params
    async def receive():
        return {"type": "http.disconnect"}
    return Request(scope, receive)


# --- Helper: poll for task completion ---

async def wait_for_task(a2a_agent, task_id, max_retries=30):
    """Poll on_get_task until the task reaches a terminal state."""
    for _ in range(max_retries):
        request = build_get_request({"id": task_id})
        result = await a2a_agent.on_get_task(request=request, context=None)
        state = result.get("status", {}).get("state", "")
        if state in ["completed", "failed"]:
            return result
        await asyncio.sleep(1)
    return result


def print_task_answer(result):
    """Extract and print the answer from task artifacts."""
    print(f"Status: {result.get('status', {}).get('state')}")
    for artifact in result.get("artifacts", []):
        if artifact.get("parts") and "text" in artifact["parts"][0]:
            print(f"Answer: {artifact['parts'][0]['text']}")


# --- Local test ---

async def main():
    # Create and set up the A2A agent locally

    a2a_agent = A2aAgent(agent_card=agent_card, agent_executor_builder=ReservationAgentExecutor)
    a2a_agent.set_up()

    # 1. Get agent card
    print("=" * 50)
    print("1. Retrieving agent card...")
    print("=" * 50)
    request = build_get_request(None)
    card_response = await a2a_agent.handle_authenticated_agent_card(request=request, context=None)
    print(f"Agent: {card_response.get('name')}")
    print(f"Skills: {[s.get('name') for s in card_response.get('skills', [])]}")

    # 2. Create a reservation
    print("\n" + "=" * 50)
    print("2. Creating a reservation...")
    print("=" * 50)
    message_data = {
        "message": {
            "messageId": f"msg-{os.urandom(4).hex()}",
            "content": [{"text": "Book a table for 2 on Saturday at 6pm. Name: Bob, Phone: 555-0202"}],
            "role": "ROLE_USER",
        },
    }
    request = build_post_request(message_data)
    response = await a2a_agent.on_message_send(request=request, context=None)
    task_id = response["task"]["id"]
    context_id = response["task"].get("contextId")
    print(f"Task ID: {task_id}")

    # 3. Wait for result
    print("\n" + "=" * 50)
    print("3. Waiting for task result...")
    print("=" * 50)
    result = await wait_for_task(a2a_agent, task_id)
    print_task_answer(result)

    # 4. Check the reservation (same context for session continuity)
    print("\n" + "=" * 50)
    print("4. Checking the reservation...")
    print("=" * 50)
    check_data = {
        "message": {
            "messageId": f"msg-{os.urandom(4).hex()}",
            "content": [{"text": "Check the reservation for 555-0202"}],
            "role": "ROLE_USER",
            "contextId": context_id,
        },
    }
    request = build_post_request(check_data)
    check_response = await a2a_agent.on_message_send(request=request, context=None)
    check_result = await wait_for_task(a2a_agent, check_response["task"]["id"])
    print_task_answer(check_result)

    # 5. Cancel the reservation
    print("\n" + "=" * 50)
    print("5. Cancelling the reservation...")
    print("=" * 50)
    cancel_data = {
        "message": {
            "messageId": f"msg-{os.urandom(4).hex()}",
            "content": [{"text": "Cancel the reservation for 555-0202"}],
            "role": "ROLE_USER",
            "contextId": context_id,
        },
    }
    request = build_post_request(cancel_data)
    cancel_response = await a2a_agent.on_message_send(request=request, context=None)
    cancel_result = await wait_for_task(a2a_agent, cancel_response["task"]["id"])
    print_task_answer(cancel_result)

    print("\n" + "=" * 50)
    print("All tests passed!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())