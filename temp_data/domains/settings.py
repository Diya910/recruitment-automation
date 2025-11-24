import os

from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import ClassVar, Dict
from enum import Enum


class LLMService(str, Enum):
    """
    Supported LLM service providers
    """
    OPENAI = "openai"
    OLLAMA = "ollama"
    GEMINI = "gemini"
    GROQ = "groq"
    AWS = "aws-bedrock"


class Settings(BaseSettings):
    OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")
    GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")
    OLLAMA_API_KEY: str = os.environ.get("OLLAMA_API_KEY", "")
    GROQ_API_KEY: str = os.environ.get("GROQ_API_KEY", "")

    AWS_ACCESS_KEY_ID: str = os.environ.get(
        "AWS_ACCESS_KEY_ID", ""
    )
    AWS_SECRET_ACCESS_KEY: str = os.environ.get(
        "AWS_SECRET_ACCESS_KEY", ""
    )
    AWS_REGION_NAME: str = os.environ.get(
        "AWS_REGION", "us-east-1"
    )

    OUTPUT_GENERATION_TAG: str = os.environ.get("OUTPUT_GENERATION_TAG", "true or false")
    OUTPUT_REASON_GUIDELINE: str = os.environ.get(
        "OUTPUT_REASON_GUIDELINE",
        "Detailed explanation with direct evidence from the transcript that justifies the compliance determination."
    )

    # Semaphore Settings
    CONCURRENCY_LIMIT: int = int(os.environ.get("CONCURRENCY_LIMIT", 10))

    # Document Processing Settings
    CHUNK_SIZE: int = int(os.environ.get("CHUNK_SIZE", 500))
    CHUNK_OVERLAP: int = int(os.environ.get("CHUNK_OVERLAP", 100))

    SUMMARIZATION_CHUNK_SIZE: int = int(os.environ.get("SUMMARIZATION_CHUNK_SIZE", 1000))

    # DATABASE NAME
    SQL_DATABASE_HOST: str = os.environ.get(
        "SQL_DATABASE_HOST",
        "localhost"
    )
    SQL_DATABASE_PORT: str = os.environ.get(
        "SQL_DATABASE_PORT",
        "3306"
    )
    SQL_DATABASE_NAME: str = os.environ.get(
        "SQL_DATABASE_NAME",
        "basic_accounts"
    )
    SQL_DATABASE_USER: str = os.environ.get(
        "SQL_DATABASE_USER",
        "accounts_app"
    )
    SQL_DATABASE_PASS: str = os.environ.get(
        "SQL_DATABASE_PASS",
        "accountskovonic123"
    )

    # LLM Service Configuration
    LLM_SERVICE_TYPE: str = os.environ.get(
        "LLM_SERVICE_TYPE",
        LLMService.AWS.value
    )

    # LLM Model Configurations
    LLMS: ClassVar[Dict[str, str]] = {
        "CHAT_MODEL_NAME": os.environ.get("CHAT_MODEL_NAME", "gpt-4o-mini"),
        "EMBEDDING_MODEL_NAME": os.environ.get(
            "EMBEDDING_MODEL_NAME",
            "text-embedding-3-small"
        ),
        "CHAT_MODEL_STREAMING_NAME": os.environ.get(
            "CHAT_MODEL_STREAMING_NAME",
            "gpt-4o-mini"
        ),
        "SUMMARIZE_MODEL_NAME": os.environ.get("SUMMARIZE_MODEL_NAME", "gpt-4o-mini"),
        "TRANSFORM_QUERY_MODEL_NAME": os.environ.get(
            "TRANSFORM_QUERY_MODEL_NAME",
            "gpt-4o-mini"
        )
    }

    OLLAMA_MODEL_SETTINGS: ClassVar[Dict[str, str]] = {
        "CHAT_MODEL_NAME": os.environ.get("CHAT_MODEL_NAME", "qwen2.5:14b"),
        "EMBEDDING_MODEL_NAME": os.environ.get(
            "EMBEDDING_MODEL_NAME",
            "nomic-embed-text:latest"
        ),
        "CHAT_MODEL_STREAMING_NAME": os.environ.get(
            "CHAT_MODEL_STREAMING_NAME",
            "qwen2.5:14b"
        ),
        "SUMMARIZE_MODEL_NAME": os.environ.get("SUMMARIZE_MODEL_NAME", "qwen2.5:14b"),
        "TRANSFORM_QUERY_MODEL_NAME": os.environ.get(
            "TRANSFORM_QUERY_MODEL_NAME",
            "qwen2.5:14b"
        )
    }

    GEMINI_MODEL_SETTINGS: ClassVar[Dict[str, str]] = {
        "CHAT_MODEL_NAME": os.environ.get("CHAT_MODEL_NAME", "gemini-1.5-pro"),
        "EMBEDDING_MODEL_NAME": os.environ.get(
            "EMBEDDING_MODEL_NAME",
            "models/embedding-001"
        ),
        "CHAT_MODEL_STREAMING_NAME": os.environ.get(
            "CHAT_MODEL_STREAMING_NAME",
            "gemini-1.5-pro"
        ),
        "SUMMARIZE_MODEL_NAME": os.environ.get("SUMMARIZE_MODEL_NAME", "gemini-1.5-pro"),
        "TRANSFORM_QUERY_MODEL_NAME": os.environ.get(
            "TRANSFORM_QUERY_MODEL_NAME",
            "gemini-1.5-pro"
        )
    }

    GROQ_SETTINGS: ClassVar[Dict[str, str]] = {
        "CHAT_MODEL_NAME": os.environ.get("CHAT_MODEL_NAME", "llama3-70b-8192"),
        "EMBEDDING_MODEL_NAME": os.environ.get(
            "EMBEDDING_MODEL_NAME",
            "llama3-embedding-v1"
        ),
        "CHAT_MODEL_STREAMING_NAME": os.environ.get(
            "CHAT_MODEL_STREAMING_NAME",
            "llama3-70b-8192"
        ),
        "SUMMARIZE_MODEL_NAME": os.environ.get("SUMMARIZE_MODEL_NAME", "llama3-70b-8192"),
        "TRANSFORM_QUERY_MODEL_NAME": os.environ.get(
            "TRANSFORM_QUERY_MODEL_NAME",
            "llama3-70b-8192"
        )
    }

    AWS_BEDROCK_MODEL_PROVIDERS: ClassVar[dict] = {
        "CHAT_MODEL_NAME": os.environ.get("CHAT_MODEL_PROVIDER", "meta"),
        "EMBEDDING_MODEL_NAME": os.environ.get("EMBEDDING_MODEL_PROVIDER", "amazon"),
        "LLM_MODEL_NAME": os.environ.get("LLM_MODEL_PROVIDER", "meta"),
        "CLASSIFICATION_MODEL_NAME": os.environ.get("CLASSIFICATION_MODEL_PROVIDER", "meta"),
        "TABLE_SUMMARIZER_MODEL": os.environ.get("TABLE_SUMMARIZER_PROVIDER", "meta"),
        "VISION_MODEL": os.environ.get("VISION_MODEL_PROVIDER", "meta"),
        "OPTIMIZED_QUESTION_MODEL": os.environ.get("OPTIMIZED_QUESTION_PROVIDER", "meta"),
        "LANGUAGE_DETECTION_MODEL": os.environ.get("LANGUAGE_DETECTION_PROVIDER", "meta"),
        "CHAT_STREAMING_MODEL": os.environ.get("CHAT_STREAMING_PROVIDER", "meta"),
        "TRANSFORM_QUERY_MODEL_NAME": os.environ.get("TRANSFORM_QUERY_MODEL_NAME", "meta")
    }

    AWS_BEDROCK_MODEL_SETTINGS: ClassVar[dict] = {
        "CHAT_MODEL_NAME": os.environ.get(
            "CHAT_MODEL_NAME",
            "arn:aws:bedrock:us-east-1:688427729924:inference-profile/us.meta.llama3-3-70b-instruct-v1:0"
        ),
        "EMBEDDING_MODEL_NAME": os.environ.get(
            "EMBEDDING_MODEL_NAME", "amazon.titan-embed-text-v2:0"
        ),
        "LLM_MODEL_NAME": os.environ.get(
            "LLM_MODEL_NAME",
            "arn:aws:bedrock:us-east-1:688427729924:inference-profile/us.meta.llama3-3-70b-instruct-v1:0"
        ),
        "CLASSIFICATION_MODEL_NAME": os.environ.get(
            "CLASSIFICATION_MODEL_NAME",
            "arn:aws:bedrock:us-east-1:688427729924:inference-profile/us.meta.llama3-3-70b-instruct-v1:0"
        ),
        "TABLE_SUMMARIZER_MODEL": os.environ.get(
            "TABLE_SUMMARIZER_MODEL",
            "arn:aws:bedrock:us-east-1:688427729924:inference-profile/us.meta.llama3-3-70b-instruct-v1:0"
        ),
        "VISION_MODEL": os.environ.get(
            "VISION_MODEL",
            "arn:aws:bedrock:us-east-1:688427729924:inference-profile/us.meta.llama3-3-70b-instruct-v1:0"
        ),
        "OPTIMIZED_QUESTION_MODEL": os.environ.get(
            "OPTIMIZED_QUESTION_MODEL",
            "arn:aws:bedrock:us-east-1:688427729924:inference-profile/us.meta.llama3-3-70b-instruct-v1:0"
        ),
        "LANGUAGE_DETECTION_MODEL": os.environ.get(
            "LANGUAGE_DETECTION_MODEL",
            "arn:aws:bedrock:us-east-1:688427729924:inference-profile/us.meta.llama3-3-70b-instruct-v1:0"
        ),
        "CHAT_STREAMING_MODEL": os.environ.get(
            "CHAT_STREAMING_MODEL",
            "arn:aws:bedrock:us-east-1:688427729924:inference-profile/us.meta.llama3-3-70b-instruct-v1:0"
        ),
        "TRANSFORM_QUERY_MODEL_NAME": os.environ.get(
            "TRANSFORM_QUERY_MODEL_NAME",
            "arn:aws:bedrock:us-east-1:688427729924:inference-profile/us.meta.llama3-3-70b-instruct-v1:0"
        )
    }

    def validate_api_keys(self) -> None:
        """Validate required API keys are present"""
        if self.LLM_SERVICE_TYPE == LLMService.OPENAI.value and not self.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required when using OpenAI service")

        elif self.LLM_SERVICE_TYPE == LLMService.GEMINI.value and not self.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is required when using Gemini service")

        elif self.LLM_SERVICE_TYPE == LLMService.GROQ.value and not self.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is required when using Groq service")

    def validate_vector_db_config(self) -> None:
        """Validate vector database configuration"""
        if self.VECTOR_DATABASE_TO_USE not in [e.value for e in VectorDBType]:
            raise ValueError(f"Unsupported vector database: {self.VECTOR_DATABASE_TO_USE}")

        if (self.WEAVIATE_VECTOR_DATABASE_SERVICE_TYPE == WeaviateServiceType.CLOUD.value and
                not self.WEAVIATE_AUTH_CREDENTIALS):
            raise ValueError("WEAVIATE_AUTH_CREDENTIALS required for cloud service")

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        validate_assignment=True,
        customise_sources=lambda init_s, env_s, file_s: (
            init_s,
            env_s,
            file_s,
        )
    )


try:
    config_settings = Settings()
    config_settings.validate_vector_db_config()
except Exception as e:
    raise RuntimeError(f"Failed to initialize application settings: {str(e)}")
