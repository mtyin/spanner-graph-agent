from google.adk.agents import LlmAgent
from spanner_graph_agent.agents.modelling_agent import GraphModellingAgent

from spanner_graph_agent.utils.prompts import (
  GRAPH_AGENT_DESCRIPTION,
  GRAPH_AGENT_INSTRUCTIONS,
)

class GraphAgent(LlmAgent):

  def __init__(
      self,
      model: str,
  ):
    super().__init__(
        model=model,
        name='GraphAgent',
        description=GRAPH_AGENT_DESCRIPTION,
        instruction=GRAPH_AGENT_INSTRUCTIONS,
        tools=[],
        sub_agents=[GraphModellingAgent(model)],
    )
