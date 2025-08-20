# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import List, Optional

from google.adk.agents import BaseAgent
from google.adk.artifacts import BaseArtifactService, InMemoryArtifactService
from google.adk.events import Event
from google.adk.runners import Runner
from google.adk.session import Session
from google.adk.sessions import BaseSessionService, InMemorySessionService
from google.genai import types


class AgentSession(object):

    def __init__(
        self,
        agent: BaseAgent,
        user_id: str,
        session_id: Optional[str] = None,
        session_service: Optional[BaseSessionService] = None,
        artifact_service: Optional[BaseArtifactService] = None,
        **kwargs,
    ):
        self.agent: BaseAgent = agent
        self.session_service: BaseSessionService = (
            session_service or InMemorySessionService()
        )
        self.artifact_service: BaseArtifactService = (
            artifact_service or InMemoryArtifactService()
        )
        self.runner = Runner(
            agent=self.agent,
            app_name=self.agent.name,
            session_service=self.session_service,
            artifact_service=self.artifact_service,
            **kwargs,
        )
        self.session: Optional[Session] = None
        self.user_id = user_id
        self.session_id: Optional[str] = session_id

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    async def ainvoke(self, query: str) -> Optional[Event]:
        self.session = self.session or await self.session_service.create_session(
            app_name=self.runner.app_name,
            user_id=self.user_id,
            session_id=self.session_id,
        )
        assert self.session is not None
        async for event in self.runner.run_async(
            user_id=self.session.user_id,
            session_id=self.session.id,
            new_message=types.Content(role="user", parts=[types.Part(text=query)]),
        ):
            if event.is_final_response():
                return event
        return None

    async def list_artifact_keys(self) -> List[str]:
        if self.session is None:
            return []
        return await self.artifact_service.list_artifact_keys(
            app_name=self.runner.app_name,
            user_id=self.user_id,
            session_id=self.session.id,
        )

    async def load_artifact(self, filename) -> Optional[types.Part]:
        if self.session is None:
            return None
        return await self.artifact_service.load_artifact(
            app_name=self.runner.app_name,
            user_id=self.user_id,
            session_id=self.session.id,
            filename=filename,
        )
