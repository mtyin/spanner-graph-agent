### Run the agent with ADK

1) Initialize the environment

   Create a `.env` file in the examples directory:

   ```
   GOOGLE_GENAI_USE_VERTEXAI=TRUE
   GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
   GOOGLE_CLOUD_LOCATION=LOCATION
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
