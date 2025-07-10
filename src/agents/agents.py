from dataclasses import dataclass

from langgraph.pregel import Pregel

from agents.chatbot import chatbot
from agents.research_assistant import research_assistant
from agents.sql_agent import sql_agent
# Re-enabled agents that work in standalone mode
from agents.bg_task_agent.bg_task_agent import bg_task_agent
from agents.command_agent import command_agent
from agents.interrupt_agent import interrupt_agent
# Disabled agents due to missing dependencies
# from agents.knowledge_base_agent import kb_agent  # Requires langchain_aws
# from agents.langgraph_supervisor_agent import langgraph_supervisor_agent  # Requires langgraph_supervisor
# from agents.rag_assistant import rag_assistant  # Requires database_search tool
from schema import AgentInfo

DEFAULT_AGENT = "sql-agent"


@dataclass
class Agent:
    description: str
    graph: Pregel


agents: dict[str, Agent] = {
    "sql-agent": Agent(
        description="An intelligent SQL database assistant with 4-phase workflow for database operations and analysis.",
        graph=sql_agent
    ),
    "chatbot": Agent(description="A simple chatbot.", graph=chatbot),
    "research-assistant": Agent(
        description="A research assistant with web search and calculator.", graph=research_assistant
    ),
    # Re-enabled agents that work in standalone mode
    "command-agent": Agent(
        description="An agent that can execute shell commands.",
        graph=command_agent,
    ),
    "bg-task-agent": Agent(
        description="An agent that can run background tasks.",
        graph=bg_task_agent,
    ),
    "interrupt-agent": Agent(
        description="An agent that uses interrupts for user interaction.",
        graph=interrupt_agent,
    ),
    # Disabled agents due to missing dependencies
    # "knowledge-base-agent": Agent(
    #     description="A retrieval-augmented generation agent using Amazon Bedrock Knowledge Base",
    #     graph=kb_agent,
    # ),  # Requires langchain_aws
    # "langgraph-supervisor-agent": Agent(
    #     description="A langgraph supervisor agent",
    #     graph=langgraph_supervisor_agent
    # ),  # Requires langgraph_supervisor
    # "rag-assistant": Agent(
    #     description="A RAG assistant with access to information in a database.",
    #     graph=rag_assistant
    # ),  # Requires database_search tool
}


def get_agent(agent_id: str) -> Pregel:
    return agents[agent_id].graph


def get_all_agent_info() -> list[AgentInfo]:
    return [
        AgentInfo(key=agent_id, description=agent.description) for agent_id, agent in agents.items()
    ]
