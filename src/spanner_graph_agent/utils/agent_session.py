from typing import Optional
from google.adk.agents import BaseAgent
from google.adk.events import Event
from google.adk.runners import Runner
from google.adk.sessions import BaseSessionService, InMemorySessionService
from google.genai import types


class AgentSession(object):

  def __init__(
      self,
      agent: BaseAgent,
      user_id: str,
      session_id: Optional[str] = None,
      session_service: Optional[BaseSessionService] = None,
  ):
    self.agent = agent
    self.session_service = session_service or InMemorySessionService()
    self.runner = Runner(
        agent=self.agent,
        app_name=self.agent.name,
        session_service=self.session_service,
    )
    self.session = None
    self.user_id = user_id
    self.session_id = session_id

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
    async for event in self.runner.run_async(
        user_id=self.session.user_id,
        session_id=self.session.id,
        new_message=types.Content(role='user', parts=[types.Part(text=query)]),
    ):
      if event.is_final_response():
        return event
    return None
