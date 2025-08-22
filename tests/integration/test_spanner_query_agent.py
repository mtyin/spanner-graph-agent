import os
import random
import string
import tempfile
import uuid

import pytest
from dotenv import load_dotenv
from spanner_graphs.graph_server import GraphServer

from graph_agents import QueryAgentConfig, SpannerGraphQueryAgent
from graph_agents.utils.agent_session import AgentSession
from graph_agents.utils.dataset import Dataset

PERSON_CSV = """
id,name
1,Alex C.
2,Dana A.
3,Lee N.
4,Alex D.
"""

PERSON_FOLLOWS_PERSON_CSV = """
id,friend_id
1,2
2,3
3,1
1,3
1,4
"""

PREFIX = "".join(random.choices(string.ascii_letters, k=5))

SCHEMA_DDL = f"""
CREATE TABLE IF NOT EXISTS {PREFIX}_Person (
  id INT64 NOT NULL,
  name STRING(MAX),
  name_token TOKENLIST AS (TOKENIZE_FULLTEXT(name)) HIDDEN,
) PRIMARY KEY (id);

CREATE SEARCH INDEX {PREFIX}_PersonFullNameSearchIndex ON {PREFIX}_Person(name_token);

CREATE TABLE IF NOT EXISTS {PREFIX}_Person_Follows_Person (
  id INT64 NOT NULL,
  friend_id INT64 NOT NULL,
) PRIMARY KEY (id, friend_id), INTERLEAVE IN PARENT {PREFIX}_Person;

CREATE OR REPLACE PROPERTY GRAPH {PREFIX}_SocialGraph
NODE TABLES ( {PREFIX}_Person AS Person )
EDGE TABLES (
  {PREFIX}_Person_Follows_Person AS Follows
  SOURCE KEY (id) REFERENCES Person(id)
  DESTINATION KEY (friend_id) REFERENCES Person(id)
);
"""

CLEANUP_DDL = f"""
DROP PROPERTY GRAPH IF EXISTS {PREFIX}_SocialGraph;
DROP TABLE IF EXISTS {PREFIX}_Person_Follows_Person;
DROP INDEX IF EXISTS {PREFIX}_PersonFullNameSearchIndex;
DROP TABLE IF EXISTS {PREFIX}_Person;
"""

TEST_DATA = {
    "nodes": {
        f"{PREFIX}_Person.csv": PERSON_CSV,
    },
    "edges": {
        f"{PREFIX}_Person_Follows_Person.csv": PERSON_FOLLOWS_PERSON_CSV,
    },
    "schema.ddl": SCHEMA_DDL,
    "cleanup.ddl": CLEANUP_DDL,
}


@pytest.fixture
def use_full_text_search(request):
    return request.param


def _generate_dataset(directory, data):
    for key, value in data.items():
        path = os.path.join(directory, key)
        if isinstance(value, dict):
            os.makedirs(path, exist_ok=True)
            _generate_dataset(path, value)
            continue

        if isinstance(value, str):
            with open(path, "w") as ofile:
                ofile.write(value)
            continue
        raise ValueError(f"Unsupported value type for key={key}")


@pytest.fixture(scope="session")
def dataset():
    load_dotenv()
    instance, database, project = (
        os.environ["GOOGLE_SPANNER_INSTANCE"],
        os.environ["GOOGLE_SPANNER_DATABASE"],
        os.environ.get("GOOGLE_CLOUD_PROJECT", None),
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        _generate_dataset(temp_dir, TEST_DATA)
        dataset = Dataset(temp_dir)
        dataset.load(instance, database, project)
        yield dataset
        dataset.cleanup(instance, database, project)


@pytest.fixture
def session(request, dataset, use_full_text_search):
    instance, database, project = (
        os.environ["GOOGLE_SPANNER_INSTANCE"],
        os.environ["GOOGLE_SPANNER_DATABASE"],
        os.environ.get("GOOGLE_CLOUD_PROJECT", None),
    )
    user_id = str(uuid.uuid4())
    root_agent = SpannerGraphQueryAgent(
        instance_id=instance,
        database_id=database,
        graph_id=f"{PREFIX}_SocialGraph",
        model="gemini-2.5-flash",
        project_id=project,
        agent_config=QueryAgentConfig(
            enabled_index_types=["SEARCH"] if use_full_text_search else [],
            log_level="DEBUG",
        ),
    )
    yield AgentSession(agent=root_agent, user_id=user_id)
    GraphServer.stop_server()


@pytest.mark.parametrize("use_full_text_search", [True], indirect=True)
@pytest.mark.asyncio
async def test_query_entity_resolution(session):
    _ = await session.ainvoke("Which persons does Alex follow?")
    response = await session.ainvoke("Alex C.")
    assert response is not None and len(response.content.parts) > 0
    assert all(
        (
            person.casefold() in response.content.parts[0].text.casefold()
            for person in ["Dana A.", "Lee N.", "Alex D."]
        )
    ), response.content.parts[0].text


@pytest.mark.parametrize("use_full_text_search", [False], indirect=True)
@pytest.mark.asyncio
async def test_query_without_entity_resolution(session):
    response = await session.ainvoke("Which persons does Alex C. follows")
    assert response is not None and len(response.content.parts) > 0
    assert all(
        (
            person.casefold() in response.content.parts[0].text.casefold()
            for person in ["Dana A.", "Lee N.", "Alex D."]
        )
    ), response.content.parts[0].text


@pytest.mark.parametrize("use_full_text_search", [False], indirect=True)
@pytest.mark.asyncio
async def test_schema_inspection(session):
    response = await session.ainvoke("What are the node types?")
    assert response is not None and len(response.content.parts) > 0
    assert (
        "person" in response.content.parts[0].text.casefold()
    ), response.content.parts[0].text
    response = await session.ainvoke("What are the edge types?")
    assert response is not None and len(response.content.parts) > 0
    assert (
        "follows" in response.content.parts[0].text.casefold()
    ), response.content.parts[0].text


@pytest.mark.parametrize("use_full_text_search", [False, True], indirect=True)
@pytest.mark.asyncio
async def test_visualization(session):
    response = await session.ainvoke(
        "what's the canonical id of person whose name is Alex C."
    )
    response = await session.ainvoke("Visualize him.")
    assert response is not None and len(response.content.parts) > 0
    artifact_keys = await session.list_artifact_keys()
    assert len(artifact_keys) == 1, response
    artifact = await session.load_artifact(artifact_keys[0])
    assert artifact.inline_data.mime_type == "text/html"
