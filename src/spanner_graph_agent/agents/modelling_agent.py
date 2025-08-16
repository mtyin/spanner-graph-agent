from google.adk.agents import LlmAgent, SequentialAgent

from spanner_graph_agent.utils.prompts import (
  GRAPH_MODELLING_AGENT_DEFAULT_DESCRIPTION,
  GRAPH_MODELLING_AGENT_DEFAULT_INSTRUCTIONS,
  GRAPH_LOGICAL_SCHEMA_MODELLING_AGENT_INSTRUCTIONS,
  SPANNER_GRAPH_SCHEMA_GENERATION_AGENT_INSTRUCTIONS,
)

class GraphLogicalModellingAgent(LlmAgent):

  def __init__(
      self,
      model: str,
  ):
    super().__init__(
        model=model,
        name='GraphLogicalModellingAgent',
        description='GraphLogicalModellingAgent',
        instruction=GRAPH_LOGICAL_SCHEMA_MODELLING_AGENT_INSTRUCTIONS,
        tools=[],
    )

class SpannerGraphSchemaGenerationAgent(LlmAgent):

  def __init__(
      self,
      model: str,
  ):
    super().__init__(
        model=model,
        name='SpannerGraphSchemaGenerationAgent',
        description='SpannerGraphSchemaGenerationAgent',
        instruction=SPANNER_GRAPH_SCHEMA_GENERATION_AGENT_INSTRUCTIONS,
        tools=[],
    )

class GraphModellingAgent(LlmAgent):

  def __init__(
      self,
      model: str,
  ):
    logical_modelling_agent = GraphLogicalModellingAgent(model)
    spanner_graph_schema_agent = SpannerGraphSchemaGenerationAgent(model)   
    super().__init__(
        model=model,
        name='GraphModellingAgent',
        description=GRAPH_MODELLING_AGENT_DEFAULT_DESCRIPTION,
        instruction=GRAPH_MODELLING_AGENT_DEFAULT_INSTRUCTIONS,
        tools=[],
        sub_agents=[logical_modelling_agent, spanner_graph_schema_agent],
    )
