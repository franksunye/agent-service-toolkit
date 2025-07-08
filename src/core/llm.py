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
    def __init__(self, responses: list[str]):
        super().__init__(responses=responses)

    def bind_tools(self, tools):
        return self


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

    # Primary: DeepSeek models (recommended for SQL Agent)
    if model_name in DeepseekModelName:
        return get_deepseek_model()

    # Fallback: OpenAI models for compatibility
    if model_name in OpenAIModelName:
        if not settings.OPENAI_API_KEY:
            raise ValueError("OpenAI API key must be configured")
        return ChatOpenAI(model=api_model_name, temperature=0.5, streaming=True)

    # Generic OpenAI-compatible models
    if model_name in OpenAICompatibleName:
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
    if model_name in FakeModelName:
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
