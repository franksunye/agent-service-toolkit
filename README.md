# 🧰 AI Agent Service Toolkit

[![build status](https://github.com/JoshuaC215/agent-service-toolkit/actions/workflows/test.yml/badge.svg)](https://github.com/JoshuaC215/agent-service-toolkit/actions/workflows/test.yml) [![codecov](https://codecov.io/github/JoshuaC215/agent-service-toolkit/graph/badge.svg?token=5MTJSYWD05)](https://codecov.io/github/JoshuaC215/agent-service-toolkit) [![Python Version](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2FJoshuaC215%2Fagent-service-toolkit%2Frefs%2Fheads%2Fmain%2Fpyproject.toml)](https://github.com/JoshuaC215/agent-service-toolkit/blob/main/pyproject.toml)
[![GitHub License](https://img.shields.io/github/license/JoshuaC215/agent-service-toolkit)](https://github.com/JoshuaC215/agent-service-toolkit/blob/main/LICENSE) [![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_red.svg)](https://agent-service-toolkit.streamlit.app/)

A full toolkit for running an AI agent service built with LangGraph, FastAPI and Streamlit.

It includes a [LangGraph](https://langchain-ai.github.io/langgraph/) agent, a [FastAPI](https://fastapi.tiangolo.com/) service to serve it, a client to interact with the service, and a [Streamlit](https://streamlit.io/) app that uses the client to provide a chat interface. Data structures and settings are built with [Pydantic](https://github.com/pydantic/pydantic).

This project offers a template for you to easily build and run your own agents using the LangGraph framework. It demonstrates a complete setup from agent definition to user interface, making it easier to get started with LangGraph-based projects by providing a full, robust toolkit.

**[🎥 Watch a video walkthrough of the repo and app](https://www.youtube.com/watch?v=pdYVHw_YCNY)**

## Overview

### [Try the app!](https://agent-service-toolkit.streamlit.app/)

<a href="https://agent-service-toolkit.streamlit.app/"><img src="media/app_screenshot.png" width="600"></a>

### Quickstart

**Simplified Setup for Global Python Environment**

```sh
# At least one LLM API key is required (DeepSeek recommended)
echo 'DEEPSEEK_API_KEY=your_deepseek_api_key' >> .env
echo 'DEEPSEEK_BASE_URL=https://api.deepseek.com' >> .env

# Install dependencies globally (no virtual environment needed)
pip install -r requirements.txt

# Run the service
python src/run_service.py

# In another terminal, run the Streamlit app
streamlit run src/streamlit_app.py
```

### Architecture Diagram

<img src="media/agent_architecture.png" width="600">

### Key Features

1. **LangGraph Agent and latest features**: A customizable agent built using the LangGraph framework. Implements the latest LangGraph v0.3 features including human in the loop with `interrupt()`, flow control with `Command`, long-term memory with `Store`, and `langgraph-supervisor`.
1. **FastAPI Service**: Serves the agent with both streaming and non-streaming endpoints.
1. **Advanced Streaming**: A novel approach to support both token-based and message-based streaming.
1. **Streamlit Interface**: Provides a user-friendly chat interface for interacting with the agent.
1. **Multiple Agent Support**: Run multiple agents in the service and call by URL path. Available agents and models are described in `/info`
1. **Asynchronous Design**: Utilizes async/await for efficient handling of concurrent requests.
1. **Content Moderation**: Implements LlamaGuard for content moderation (requires Groq API key).
1. **RAG Agent**: A basic RAG agent implementation using ChromaDB - see [docs](docs/RAG_Assistant.md).
1. **Feedback Mechanism**: Includes a star-based feedback system integrated with LangSmith.
1. **Docker Support**: Includes Dockerfiles and a docker compose file for easy development and deployment.
1. **Testing**: Includes robust unit and integration tests for the full repo.

### Key Files

The repository is structured as follows:

- `src/agents/`: Defines several agents with different capabilities
- `src/schema/`: Defines the protocol schema
- `src/core/`: Core modules including LLM definition and settings
- `src/service/service.py`: FastAPI service to serve the agents
- `src/client/client.py`: Client to interact with the agent service
- `src/streamlit_app.py`: Streamlit app providing a chat interface
- `tests/`: Unit and integration tests

## Setup and Usage

1. Clone the repository:

   ```sh
   git clone https://github.com/JoshuaC215/agent-service-toolkit.git
   cd agent-service-toolkit
   ```

2. Set up environment variables:
   Create a `.env` file in the root directory. DeepSeek API key is recommended for optimal SQL Agent performance. See the [`.env.example` file](./.env.example) for a full list of available environment variables.

3. Install dependencies and run the services using Python directly (no Docker or virtual environment needed).

### Additional setup for specific AI providers

- [Setting up Ollama](docs/Ollama.md)
- [Setting up VertexAI](docs/VertexAI.md)
- [Setting up RAG with ChromaDB](docs/RAG_Assistant.md)

### Building or customizing your own agent

To customize the agent for your own use case:

1. Add your new agent to the `src/agents` directory. You can copy `research_assistant.py` or `chatbot.py` and modify it to change the agent's behavior and tools.
1. Import and add your new agent to the `agents` dictionary in `src/agents/agents.py`. Your agent can be called by `/<your_agent_name>/invoke` or `/<your_agent_name>/stream`.
1. Adjust the Streamlit interface in `src/streamlit_app.py` to match your agent's capabilities.


### Handling Private Credential files

If your agents or chosen LLM require file-based credential files or certificates, the `privatecredentials/` has been provided for your development convenience. All contents, excluding the `.gitkeep` files, are ignored by git and docker's build process. See [Working with File-based Credentials](docs/File_Based_Credentials.md) for suggested use.


### Simplified Local Development

This project now uses a simplified setup without Docker or virtual environments for easier local development.

1. Install Python dependencies globally:
   ```sh
   pip install -r requirements.txt
   ```

2. Create a `.env` file from the `.env.example`. DeepSeek API key is recommended:
   ```sh
   cp .env.example .env
   # Edit .env to add your DeepSeek API key
   ```

3. Start the agent service:
   ```sh
   python src/run_service.py
   ```

4. In another terminal, start the Streamlit app:
   ```sh
   streamlit run src/streamlit_app.py
   ```

5. Access the Streamlit app by navigating to `http://localhost:8501` in your web browser.

6. The agent service API will be available at `http://localhost:8080`. You can also use the OpenAPI docs at `http://localhost:8080/redoc`.

### Building other apps on the AgentClient

The repo includes a generic `src/client/client.AgentClient` that can be used to interact with the agent service. This client is designed to be flexible and can be used to build other apps on top of the agent. It supports both synchronous and asynchronous invocations, and streaming and non-streaming requests.

See the `src/run_client.py` file for full examples of how to use the `AgentClient`. A quick example:

```python
from client import AgentClient
client = AgentClient()

response = client.invoke("Tell me a brief joke?")
response.pretty_print()
# ================================== Ai Message ==================================
#
# A man walked into a library and asked the librarian, "Do you have any books on Pavlov's dogs and Schrödinger's cat?"
# The librarian replied, "It rings a bell, but I'm not sure if it's here or not."

```

### Development with LangGraph Studio

The agent supports [LangGraph Studio](https://langchain-ai.github.io/langgraph/concepts/langgraph_studio/), the IDE for developing agents in LangGraph.

`langgraph-cli[inmem]` is installed with `uv sync`. You can simply add your `.env` file to the root directory as described above, and then launch LangGraph Studio with `langgraph dev`. Customize `langgraph.json` as needed. See the [local quickstart](https://langchain-ai.github.io/langgraph/cloud/how-tos/studio/quick_start/#local-development-server) to learn more.

### Alternative Setup with UV Package Manager

If you prefer using the UV package manager:

1. Install UV and dependencies:
   ```sh
   pip install uv
   uv sync --frozen
   ```

2. Run the FastAPI server:
   ```sh
   python src/run_service.py
   ```

3. In a separate terminal, run the Streamlit app:
   ```sh
   streamlit run src/streamlit_app.py
   ```

4. Open your browser and navigate to `http://localhost:8501`.

## Projects built with or inspired by agent-service-toolkit

The following are a few of the public projects that drew code or inspiration from this repo.

- **[PolyRAG](https://github.com/QuentinFuxa/PolyRAG)** - Extends agent-service-toolkit with RAG capabilities over both PostgreSQL databases and PDF documents.
- **[alexrisch/agent-web-kit](https://github.com/alexrisch/agent-web-kit)** - A Next.JS frontend for agent-service-toolkit
- **[raushan-in/dapa](https://github.com/raushan-in/dapa)** - Digital Arrest Protection App (DAPA) enables users to report financial scams and frauds efficiently via a user-friendly platform.

**Please create a pull request editing the README or open a discussion with any new ones to be added!** Would love to include more projects.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. Currently the tests need to be run using the local development without Docker setup. To run the tests for the agent service:

1. Ensure you're in the project root directory and have activated your virtual environment.

2. Install the development dependencies and pre-commit hooks:

   ```sh
   pip install -r requirements.txt
   pip install pytest pytest-cov pytest-env pytest-asyncio ruff mypy pre-commit
   pre-commit install
   ```

3. Run the tests using pytest:

   ```sh
   pytest
   ```

## 📚 Documentation

### Core Design Documents
- [System Architecture](docs/01_ARCHITECTURE.md) - Overall system architecture
- [Backend Design](docs/03_BACKEND_DESIGN.md) - FastAPI service design
- [Frontend Design](docs/04_FRONTEND_DESIGN.md) - Streamlit interface design
- [Agent Mechanisms](docs/04_AGENT_MECHANISMS.md) - Agent implementation patterns
- [LLM Integration](docs/05_LLM_INTEGRATION.md) - Model integration technology
- [Database & Storage](docs/06_DATABASE_STORAGE.md) - Storage system design

### Detailed Design Documents
- [SQL Agent Design](docs/08_SQL_AGENT_DESIGN.md) - Complete SQL Agent implementation
- [Observability & Traceability](docs/09_OBSERVABILITY_TRACEABILITY_DESIGN.md) - AI Native observability design
- [Streamlit Cloud Deployment](docs/10_STREAMLIT_CLOUD_DEPLOYMENT.md) - Production deployment guide
- [Streamlit Standalone Feasibility](docs/11_STREAMLIT_STANDALONE_FEASIBILITY.md) - Standalone deployment analysis
- [Human-in-the-Loop Analysis](docs/12_HUMAN_IN_THE_LOOP_ANALYSIS.md) - HITL functionality and demo guide

### Development Records
- [SQL Agent Development](docs/02_SQL_AGENT_DEVELOPMENT_BACKLOG.md) - Development process records

## License

This project is licensed under the MIT License - see the LICENSE file for details.
