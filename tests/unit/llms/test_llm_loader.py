"""Unit tests for LLMLoader class."""

from unittest.mock import patch

import pytest

from ols import constants
from ols.app.models.config import LLMConfig, ProviderConfig
from ols.src.llms.llm_loader import (
    LLMLoader,
    MissingModel,
    MissingProvider,
    ModelConfigMissingException,
    UnsupportedProvider,
)
from ols.utils import config


def test_constructor_no_provider():
    """Test that constructor checks for provider."""
    with pytest.raises(MissingProvider, match="Missing provider"):
        LLMLoader(provider=None)


def test_constructor_no_model():
    """Test that constructor checks for model."""
    with pytest.raises(MissingModel, match="Missing model"):
        LLMLoader(provider=constants.PROVIDER_BAM, model=None)


def test_constructor_wrong_provider():
    """Test how wrong provider is checked."""
    with pytest.raises(UnsupportedProvider):
        LLMLoader(provider="invalid-provider", model=constants.GRANITE_13B_CHAT_V1)


llm_cfgs = [
    [constants.PROVIDER_OPENAI, constants.GRANITE_13B_CHAT_V1],
    # following providers has no checks for params provided
    # TODO: update the code itself
    # [constants.PROVIDER_OLLAMA, constants.GRANITE_13B_CHAT_V1],
    # [constants.PROVIDER_WATSONX, constants.GRANITE_13B_CHAT_V1],
    # [constants.PROVIDER_TGI, constants.GRANITE_13B_CHAT_V1],
    # [constants.PROVIDER_BAM, constants.GRANITE_13B_CHAT_V1],
]


@pytest.mark.parametrize("provider, model", llm_cfgs)
def test_constructor_correct_provider_no_models(provider, model):
    """Test if model setup is check for given provider."""
    config.load_empty_config()
    config.llm_config = LLMConfig()
    providerConfig = ProviderConfig()
    providerConfig.models = {model: None}
    config.llm_config.providers = {provider: providerConfig}
    message = (
        f"No configuration provided for model {model} under LLM provider {provider}"
    )
    with pytest.raises(ModelConfigMissingException, match=message):
        LLMLoader(provider=provider, model=model)


# all LLM providers that can be initialized
llm_providers = [
    constants.PROVIDER_OPENAI,
    constants.PROVIDER_OLLAMA,
    constants.PROVIDER_WATSONX,
    constants.PROVIDER_TGI,
    constants.PROVIDER_BAM,
]


@pytest.mark.parametrize("provider", llm_providers)
def test_constructor_unsatisfied_requirements(provider):
    """Test how unsatisfied requirements are handled by LLM loader."""
    config.load_empty_config()
    config.llm_config = LLMConfig()
    providerConfig = ProviderConfig()
    providerConfig.models = {constants.GRANITE_13B_CHAT_V1: None}
    config.llm_config.providers = {provider: providerConfig}

    def mock_import(module, *args, **kwargs):
        """Mock the import and from x import statements."""
        pass

    # check what happens if LLM libraries can not be loaded
    with patch("builtins.__import__", side_effect=mock_import):
        with pytest.raises(Exception):
            LLMLoader(provider=provider, model=constants.GRANITE_13B_CHAT_V1)