"""Registers or updates the Reservation Agent in Google Cloud Agent Registry."""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
import google.auth
import google.auth.transport.requests

try:
    from reservation_agent.a2a_config import agent_card
except ModuleNotFoundError:
    from a2a_config import agent_card

def register_service(project_id: str, location: str, re_resource_name: str, service_id: str):
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    auth_req = google.auth.transport.requests.Request()
    creds.refresh(auth_req)

    headers = {
        "Authorization": f"Bearer {creds.token}",
        "Content-Type": "application/json",
    }

    # Build target A2A URL on the Reasoning Engine
    # re_resource_name format: projects/{project}/locations/{location}/reasoningEngines/{id}
    a2a_url = f"https://{location}-aiplatform.googleapis.com/v1beta1/{re_resource_name}/a2a"

    # Convert agent_card to dict and inject the deployed endpoint URL
    card_dict = agent_card.model_dump(exclude_none=True, by_alias=True)
    card_dict["url"] = a2a_url

    service_body = {
        "displayName": "Reservation Agent",
        "description": "Handles restaurant table reservations — create, check, and cancel bookings for Foodie Finds restaurant.",
        "agentSpec": {
            "type": "A2A_AGENT_CARD",
            "content": card_dict,
        },
    }

    create_url = f"https://agentregistry.googleapis.com/v1/projects/{project_id}/locations/{location}/services?serviceId={service_id}"
    patch_url = f"https://agentregistry.googleapis.com/v1/projects/{project_id}/locations/{location}/services/{service_id}?updateMask=agentSpec,displayName,description"

    req_create = urllib.request.Request(
        create_url,
        data=json.dumps(service_body).encode(),
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(req_create) as resp:
            print(f"Successfully registered A2A service '{service_id}' in Agent Registry!")
            print(resp.read().decode())
            return
    except urllib.error.HTTPError as e:
        if e.code == 409:
            print(f"Service '{service_id}' already exists. Updating via PATCH...")
            req_patch = urllib.request.Request(
                patch_url,
                data=json.dumps(service_body).encode(),
                headers=headers,
                method="PATCH",
            )
            with urllib.request.urlopen(req_patch) as resp:
                print(f"Successfully updated A2A service '{service_id}' in Agent Registry!")
                print(resp.read().decode())
                return
        else:
            err = e.read().decode()
            print(f"Failed to register service '{service_id}' (HTTP {e.code}): {err}", file=sys.stderr)
            sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Register A2A Agent in Google Cloud Agent Registry")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--location", required=True)
    parser.add_argument("--re-name", help="Full reasoning engine resource name")
    parser.add_argument("--re-file", help="Path to file containing reasoning engine resource name")
    parser.add_argument("--service-id", default="reservation-agent")

    args = parser.parse_args()

    re_name = args.re_name
    if not re_name and args.re_file:
        with open(args.re_file) as f:
            re_name = f.read().strip()

    if not re_name:
        print("Error: either --re-name or --re-file must be provided", file=sys.stderr)
        sys.exit(1)

    if not re_name.startswith("projects/"):
        re_name = f"projects/{args.project_id}/locations/{args.location}/reasoningEngines/{re_name}"

    register_service(args.project_id, args.location, re_name, args.service_id)

if __name__ == "__main__":
    main()
