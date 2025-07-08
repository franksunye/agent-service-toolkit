from functools import cache
from typing import TypeAlias

# Core imports for simplified setup
from langchain_community.chat_models import FakeListChatModel
from langchain_openai import ChatOpenAI

# Import our simplified DeepSeek client
from core.deepseek_client import DeepSeekChatModel, get_deepseek_model
from core.settings import settings
from schema.models import (
    AllModelEnum,
    DeepseekModelName,
    FakeModelName,
    OpenAIModelName,
    OpenAICompatibleName,
)

# Note: Optional model providers removed for simplification
# They can be re-added to optional-models dependency group if needed

# Simplified model table focusing on core models
_MODEL_TABLE = (
    {m: m.value for m in DeepseekModelName}  # Primary focus
    | {m: m.value for m in OpenAIModelName}  # Backup compatibility
    | {m: m.value for m in OpenAICompatibleName}  # Generic compatibility
    | {m: m.value for m in FakeModelName}  # Testing
)


class FakeToolModel(FakeListChatModel):
    def __init__(self, responses: list[str] = None):
        if responses is None:
            # Default responses that include tool calls for SQL Agent testing
            responses = [
                "I'll help you with your database query. Let me check the database schema first."
            ]
        super().__init__(responses=responses)
        self._tools = []

    def bind_tools(self, tools):
        """Bind tools and return a new instance that can generate tool calls"""
        new_model = FakeToolModel(self.responses)
        new_model._tools = tools
        return new_model

    async def ainvoke(self, messages, config=None, **kwargs):
        """Override to generate tool calls for SQL-related queries"""
        from langchain_core.messages import AIMessage

        # Get the last human message
        last_message = None
        for msg in reversed(messages):
            if hasattr(msg, 'content') and msg.content:
                last_message = msg.content.lower()
                break

        # If this looks like a database query and we have tools, generate tool calls
        if (last_message and
            any(keyword in last_message for keyword in ['table', 'database', 'schema', 'query', 'sql']) and
            self._tools):

            # Generate appropriate tool call based on the query
            tool_call = None
            if 'table' in last_message or 'schema' in last_message:
                # Use get_database_schema tool
                for tool in self._tools:
                    if hasattr(tool, 'name') and tool.name == 'get_database_schema':
                        tool_call = {
                            "name": "get_database_schema",
                            "args": {},
                            "id": "call_get_schema_001"
                        }
                        break

            if tool_call:
                return AIMessage(
                    content="I'll check the database schema for you.",
                    tool_calls=[tool_call]
                )

        # Fall back to default behavior
        return await super().ainvoke(messages, config, **kwargs)


# Simplified model type alias for core models
ModelT: TypeAlias = (
    DeepSeekChatModel
    | ChatOpenAI
    | FakeToolModel
)


@cache
def get_model(model_name: AllModelEnum, /) -> ModelT:
    """
    Simplified model factory focusing on DeepSeek as primary model
    with fallback support for OpenAI and testing models
    """
    api_model_name = _MODEL_TABLE.get(model_name)
    if not api_model_name:
        raise ValueError(f"Unsupported model: {model_name}")

    # Handle string model names by converting to enum
    if isinstance(model_name, str):
        # Try to find the enum value
        for enum_class in [DeepseekModelName, OpenAIModelName, OpenAICompatibleName, FakeModelName]:
            try:
                model_name = enum_class(model_name)
                break
            except ValueError:
                continue
        else:
            # If not found in any enum, try to match by value
            for enum_class in [DeepseekModelName, OpenAIModelName, OpenAICompatibleName, FakeModelName]:
                for enum_val in enum_class:
                    if enum_val.value == model_name:
                        model_name = enum_val
                        break
                if not isinstance(model_name, str):
                    break

    # Primary: DeepSeek models (recommended for SQL Agent)
    if isinstance(model_name, DeepseekModelName):
        return get_deepseek_model()

    # Fallback: OpenAI models for compatibility
    if isinstance(model_name, OpenAIModelName):
        if not settings.OPENAI_API_KEY:
            raise ValueError("OpenAI API key must be configured")
        return ChatOpenAI(model=api_model_name, temperature=0.5, streaming=True)

    # Generic OpenAI-compatible models
    if isinstance(model_name, OpenAICompatibleName):
        if not settings.COMPATIBLE_BASE_URL or not settings.COMPATIBLE_MODEL:
            raise ValueError("Compatible model base URL and model name must be configured")
        return ChatOpenAI(
            model=settings.COMPATIBLE_MODEL,
            temperature=0.5,
            streaming=True,
            base_url=settings.COMPATIBLE_BASE_URL,
            api_key=settings.COMPATIBLE_API_KEY.get_secret_value() if settings.COMPATIBLE_API_KEY else None,
        )

    # Testing: Fake model for development
    if isinstance(model_name, FakeModelName) or model_name == "fake":
        return FakeToolModel(responses=["This is a test response from the fake model."])

    raise ValueError(f"Unsupported model: {model_name}")


def get_default_model() -> ModelT:
    """Get the default model (DeepSeek preferred)"""
    if settings.DEEPSEEK_API_KEY:
        return get_deepseek_model()
    elif settings.OPENAI_API_KEY:
        return get_model(OpenAIModelName.GPT_4O_MINI)
    else:
        return get_model(FakeModelName.FAKE)
