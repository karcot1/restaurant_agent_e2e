# reservation_agent/executor.py
import os
from typing import NoReturn

import vertexai
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import TaskState, TextPart, UnsupportedOperationError
from a2a.utils import new_agent_text_message
from a2a.utils.errors import ServerError
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService, VertexAiSessionService
from google.genai import types

from reservation_agent.agent import root_agent as reservation_agent


class ReservationAgentExecutor(AgentExecutor):
    """Bridge between the A2A protocol and the ADK reservation agent.

    Uses InMemorySessionService for local testing, VertexAiSessionService
    when deployed to Agent Runtime (detected via GOOGLE_CLOUD_AGENT_ENGINE_ID).
    """

    def __init__(self) -> None:
        self.agent = None
        self.runner = None

    def _init_agent(self) -> None:
        if self.agent is not None:
            return

        self.agent = reservation_agent
        engine_id = os.environ.get("GOOGLE_CLOUD_AGENT_ENGINE_ID")

        if engine_id:
            project = os.environ.get("GOOGLE_CLOUD_PROJECT")
            location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
            vertexai.init(project=project, location=location)
            session_service = VertexAiSessionService(
                project=project, location=location, agent_engine_id=engine_id,
            )
            app_name = engine_id
        else:
            session_service = InMemorySessionService()
            app_name = self.agent.name

        self.runner = Runner(
            app_name=app_name,
            agent=self.agent,
            artifact_service=InMemoryArtifactService(),
            session_service=session_service,
            memory_service=InMemoryMemoryService(),
        )

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        if self.agent is None:
            self._init_agent()

        query = context.get_user_input()
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        user_id = context.message.metadata.get("user_id", "a2a-user") if context.message.metadata else "a2a-user"

        if not context.current_task:
            await updater.submit()
        await updater.start_work()

        try:
            session = await self._get_or_create_session(context.context_id, user_id)
            content = types.Content(role="user", parts=[types.Part(text=query)])

            async for event in self.runner.run_async(
                session_id=session.id, user_id=user_id, new_message=content,
            ):
                if event.is_final_response():
                    parts = event.content.parts
                    answer = " ".join(p.text for p in parts if p.text) or "No response."
                    await updater.add_artifact([TextPart(text=answer)], name="answer")
                    await updater.complete()
                    break
        except Exception as e:
            await updater.update_status(
                TaskState.failed, message=new_agent_text_message(f"Error: {e!s}"),
            )
            raise

    async def _get_or_create_session(self, context_id: str, user_id: str):
        app_name = self.runner.app_name
        if context_id:
            session = await self.runner.session_service.get_session(
                app_name=app_name, session_id=context_id, user_id=user_id,
            )
            if session:
                return session
        session = await self.runner.session_service.create_session(
            app_name=app_name, user_id=user_id, session_id=context_id,
        )
        return session

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> NoReturn:
        raise ServerError(error=UnsupportedOperationError())