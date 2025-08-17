import os
from typing import Optional
from pydantic import BaseSettings

class Config(BaseSettings):
    anthropic_api_key: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY") 
    google_api_key: Optional[str] = os.getenv("GOOGLE_API_KEY")
    sec_api_key: Optional[str] = os.getenv("SEC_API_KEY")
    
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    financial_llm_model: str = "AdaptLLM/finance-LLM"
    financial_sentiment_model: str = "ProsusAI/finbert"
    
    chroma_persist_directory: str = "./data/chroma_db"
    sec_user_agent: str = "NeMo Financial Research Assistant admin@example.com"
    
    max_chunk_size: int = 1000
    chunk_overlap: int = 200
    max_tokens: int = 4096
    temperature: float = 0.1
    
    class Config:
        env_file = ".env"

config = Config()
