from google.adk.agents import LlmAgent

from spanner_graph_agent.utils.prompts import (
  GRAPH_MODELLING_AGENT_DEFAULT_DESCRIPTION,
  GRAPH_MODELLING_AGENT_DEFAULT_INSTRUCTIONS,
)

class GraphModellingAgent(LlmAgent):

  def __init__(
      self,
      model: str,
  ):
    super().__init__(
        model=model,
        name='GraphModellingAgent',
        description=GRAPH_MODELLING_AGENT_DEFAULT_DESCRIPTION,
        instruction=GRAPH_MODELLING_AGENT_DEFAULT_INSTRUCTIONS,
        tools=[],
    )
