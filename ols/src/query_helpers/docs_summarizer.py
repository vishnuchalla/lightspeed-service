"""A class for summarizing documentation context."""

import logging
import pyroscope
from typing import Any, Optional

from langchain.chains import LLMChain
from llama_index.core import VectorStoreIndex

from ols import config
from ols.app.metrics import TokenMetricUpdater
from ols.app.models.config import ProviderConfig
from ols.app.models.models import SummarizerResponse
from ols.constants import RAG_CONTENT_LIMIT, GenericLLMParameters
from ols.src.prompts.prompt_generator import generate_prompt
from ols.src.query_helpers.query_helper import QueryHelper
from ols.utils.token_handler import TokenHandler

logger = logging.getLogger(__name__)


class DocsSummarizer(QueryHelper):
    """A class for summarizing documentation context."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the QuestionValidator."""
        super().__init__(*args, **kwargs)
        provider_config = config.llm_config.providers.get(self.provider)
        model_config = provider_config.models.get(self.model)
        self.generic_llm_params = {
            GenericLLMParameters.MAX_TOKENS_FOR_RESPONSE: model_config.parameters.max_tokens_for_response  # noqa: E501
        }

    def _get_model_options(
        self, provider_config: ProviderConfig
    ) -> Optional[dict[str, Any]]:
        if provider_config is not None:
            model_config = provider_config.models.get(self.model)
            return model_config.options
        return None

    def summarize(
        self,
        conversation_id: str,
        query: str,
        vector_index: Optional[VectorStoreIndex] = None,
        history: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> SummarizerResponse:
        """Summarize the given query based on the provided conversation context.

        Args:
            conversation_id: The unique identifier for the conversation.
            query: The query to be summarized.
            vector_index: Vector index to get rag data/context.
            history: The history of the conversation (if available).
            kwargs: Additional keyword arguments for customization (model, verbose, etc.).

        Returns:
            A `SummarizerResponse` object.
        """
        with pyroscope.tag_wrapper({ "docs_summarizer": "summarize" }):
            # if history is not provided, initialize to empty history
            if history is None:
                history = []

            verbose = kwargs.get("verbose", "").lower() == "true"
            settings_string = (
                f"conversation_id: {conversation_id}, "
                f"query: {query}, "
                f"provider: {self.provider}, "
                f"model: {self.model}, "
                f"verbose: {verbose}"
            )
            logger.debug(f"{conversation_id} call settings: {settings_string}")

            token_handler = TokenHandler()
            bare_llm = self.llm_loader(self.provider, self.model, self.generic_llm_params)
            provider_config = config.llm_config.providers.get(self.provider)
            model_config = provider_config.models.get(self.model)
            model_options = self._get_model_options(provider_config)

            # Use sample text for context/history to get complete prompt instruction.
            # This is used to calculate available tokens.
            temp_prompt, temp_prompt_input = generate_prompt(
                self.provider,
                self.model,
                model_options,
                query,
                ["sample"],
                "sample",
            )
            available_tokens = token_handler.calculate_and_check_available_tokens(
                temp_prompt.format(**temp_prompt_input),
                model_config.context_window_size,
                model_config.parameters.max_tokens_for_response,
            )

            if vector_index is not None:
                retriever = vector_index.as_retriever(similarity_top_k=RAG_CONTENT_LIMIT)
                rag_chunks, available_tokens = token_handler.truncate_rag_context(
                    retriever.retrieve(query), available_tokens
                )
            else:
                logger.warning("Proceeding without RAG content. Check start up messages.")
                rag_chunks = []

            rag_context = "\n\n".join([rag_chunk.text for rag_chunk in rag_chunks])

            # Truncate history, if applicable
            history, truncated = token_handler.limit_conversation_history(
                history, available_tokens
            )

            final_prompt, llm_input_values = generate_prompt(
                self.provider,
                self.model,
                model_options,
                query,
                history,
                rag_context,
            )

            # Tokens-check: We trigger the computation of the token count
            # without care about the return value. This is to ensure that
            # the query is within the token limit.
            token_handler.calculate_and_check_available_tokens(
                final_prompt.format(**llm_input_values),
                model_config.context_window_size,
                model_config.parameters.max_tokens_for_response,
            )

            chat_engine = LLMChain(
                llm=bare_llm,
                prompt=final_prompt,
                verbose=verbose,
            )

            with TokenMetricUpdater(
                llm=bare_llm,
                provider=provider_config.type,
                model=self.model,
            ) as token_counter:
                summary = chat_engine.invoke(
                    input=llm_input_values,
                    config={"callbacks": [token_counter]},
                )

            # retrieve text response returned from LLM, strip whitespace characters from beginning/end
            response = summary["text"].strip()

            if len(rag_context) == 0:
                logger.debug("Using llm to answer the query without reference content")
            logger.debug(f"{conversation_id} Summary response: {response}")

            return SummarizerResponse(response, rag_chunks, truncated)
