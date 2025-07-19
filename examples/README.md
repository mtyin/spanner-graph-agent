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

4) Deploy to cloud run or agent engine

   ```
   # See: https://google.github.io/adk-docs/deploy/cloud-run/
   # Make sure the compute engine service account have the right permissions
   # (Spanner, GCS bucket etc): https://cloud.google.com/compute/docs/access/service-accounts#default_service_account
   # PROJECT_NUMBER-compute@developer.gserviceaccount.com
   adk deploy cloud_run --project mtyin-demo --region us-central1 --with_ui .

   ```

   ```
   # See: https://google.github.io/adk-docs/deploy/agent-engine/
   # Make sure the agent engine service account have the right permissions
   # (Spanner, GCS bucket etc): https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/set-up
   # service-PROJECT_NUMBER@gcp-sa-aiplatform-re.iam.gserviceaccount.com
   adk deploy agent_engine . --project GOOGLE_CLOUD_PROJECT --env_file .env --requirements_file requirements.txt --staging_bucket STAGING_BUCKET
   ```
