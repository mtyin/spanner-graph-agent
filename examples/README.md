### Run the agent with ADK

1) Initialize the environment

   Create a `.env` file in the examples directory:

   ```
   GOOGLE_CLOUD_PROJECT=<your-project-id>
   GOOGLE_SPANNER_INSTANCE=<your-instance>
   GOOGLE_SPANNER_DATABASE=<your-database>
   GOOGLE_SPANNER_GRAPH=<your-graph>
   GOOGLE_GENAI_USE_VERTEXAI=TRUE
   GOOGLE_CLOUD_LOCATION=<your-location>
   ```

2) Install the library

   ```
   python3 -m venv .venv
   source .venv/bin/activate
   pip install ..
   ```

3) Run the agent or bring a web server with the agent:

   ```
   adk run .

   python agent.py

   adk web ..
   ```

4) Deploy to agent engine

   ```
   # Make sure the agent engine service account have the right permissions
   # (Spanner, GCS bucket etc): https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/set-up
   adk deploy agent_engine . --project GOOGLE_CLOUD_PROJECT --env_file .env --requirements_file requirements.txt --staging_bucket STAGING_BUCKET
   ```
