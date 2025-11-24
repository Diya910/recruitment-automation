import re
from loguru import logger

from domains.settings import config_settings, LLMService

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_aws.chat_models import ChatBedrock
from langchain_aws import BedrockEmbeddings
from langchain_ollama import OllamaEmbeddings, ChatOllama


def get_chat_llm(
        model_key: str = "CHAT_MODEL_NAME",
        temperature: float = config_settings.TEMPERATURE,
):
    try:
        if config_settings.LLM_SERVICE_TYPE == LLMService.OPENAI.value:
            return ChatOpenAI(
                model=config_settings.OLLAMA_MODEL_SETTINGS.get(
                    model_key, None
                ),
                temperature=temperature,
            )

        elif config_settings.LLM_SERVICE_TYPE == LLMService.OLLAMA.value:
            return ChatOllama(
                model=config_settings.OLLAMA_MODEL_SETTINGS.get(
                    model_key, None
                ),
                temperature=config_settings.TEMPERATURE,
        )

        elif config_settings.LLM_SERVICE_TYPE == LLMService.AWS.value:
            model_id = config_settings.AWS_BEDROCK_MODEL_SETTINGS.get(model_key, None)
            is_arn = model_id.startswith("arn:")

            provider = None
            if is_arn:
                provider = config_settings.AWS_BEDROCK_MODEL_PROVIDERS.get(model_key, None)
                logger.info(f"Using ARN model ID for {model_key}: {model_id} with provider: {provider}")
            else:
                logger.info(f"Using regular model ID for {model_key}: {model_id}")
                return ChatBedrock(
                    model=model_id,
                    temperature=temperature,
                    aws_access_key_id=config_settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=config_settings.AWS_SECRET_ACCESS_KEY,
                    region=config_settings.AWS_REGION_NAME,
                )

            return ChatBedrock(
                model_id=model_id,
                provider=provider,
                temperature=temperature,
                aws_access_key_id=config_settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=config_settings.AWS_SECRET_ACCESS_KEY,
                region=config_settings.AWS_REGION_NAME,
            )

    except Exception as e:
        logger.error(f"Error {e}")
        return None