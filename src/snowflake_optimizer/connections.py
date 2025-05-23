import logging
import os
from datetime import datetime
from typing import Optional

import streamlit as st
from dotenv import load_dotenv
from openai import AzureOpenAI

from snowflake_optimizer.cache import SQLiteCache, BaseCache
from snowflake_optimizer.data_collector import QueryMetricsCollector, SnowflakeQueryExecutor
from snowflake_optimizer.query_analyzer import QueryAnalyzer

load_dotenv()


# Configure logging
def setup_logging():
    """Configure logging with custom format and handlers."""
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file = os.path.join(log_dir, f"snowflake_optimizer_{datetime.now().strftime('%Y%m%d')}.log")

    # Create formatters and handlers
    file_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(funcName)s | %(message)s'
    )

    # File handler for detailed logging
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)

    # Log initial application startup
    logging.info("Snowflake Query Optimizer application started")
    logging.debug(f"Log file created at: {log_file}")


def initialize_connections(page_id, cache: BaseCache = None) -> tuple[
    Optional[QueryMetricsCollector], Optional[QueryAnalyzer]]:
    """Initialize connections to Snowflake and LLM services.

    Returns:
        Tuple of QueryMetricsCollector and QueryAnalyzer instances
    """
    logging.info("Initializing service connections")

    try:
        logging.debug("Attempting to connect to Snowflake")
        collector = QueryMetricsCollector(
            account=st.secrets["SNOWFLAKE_ACCOUNT"],
            user=st.secrets["SNOWFLAKE_USER"],
            password=st.secrets["SNOWFLAKE_PASSWORD"],
            warehouse=st.secrets["SNOWFLAKE_WAREHOUSE"],
            database=st.secrets.get("SNOWFLAKE_DATABASE"),
            schema=st.secrets.get("SNOWFLAKE_SCHEMA"),
        )
        logging.info("Successfully connected to Snowflake")
    except Exception as e:
        logging.error(f"Failed to connect to Snowflake: {str(e)}")
        st.error(f"Failed to connect to Snowflake: {str(e)}")
        collector = None

    try:
        # Extract secrets for Lit LLM Proxy
        litlm_api_url = st.secrets['LITLM_API_URL']
        litlm_api_key = st.secrets['LITLM_API_KEY']
        model_name = st.secrets['LITLM_MODEL_NAME']
        
        # Import your Lit LLM client (adjust import as needed)
        from lit_llm_client import LitLLMClient
        
        # Initialize Lit LLM Proxy client
        litllm_client = LitLLMClient(
            api_url=litlm_api_url,
            api_key=litlm_api_key,
            model=model_name
        )
        
        logging.debug("Initializing Query Analyzer with Lit LLM Proxy")
        logging.debug(f"Lit LLM Proxy API URL: {litlm_api_url}")
        
        if f'{page_id}_analyzer' not in st.session_state:
            analyzer = QueryAnalyzer(
                openai_client=litllm_client,
                openai_model=model_name,
                cache=cache
            )
            st.session_state[f'{page_id}_analyzer'] = analyzer
        else:
            analyzer = st.session_state[f'{page_id}_analyzer']
        
        logging.info("Successfully initialized Query Analyzer with Lit LLM Proxy")
    except Exception as e:
        logging.error(f"Failed to initialize Query Analyzer with Lit LLM Proxy: {str(e)}")
        st.error(f"Failed to initialize Query Analyzer with Lit LLM Proxy: {str(e)}")
        analyzer = None

    return collector, analyzer



def get_snowflake_query_executor():
    try:
        snowflake_executor = SnowflakeQueryExecutor(
            account=st.secrets["SNOWFLAKE_ACCOUNT"],
            user=st.secrets["SNOWFLAKE_USER"],
            password=st.secrets["SNOWFLAKE_PASSWORD"],
            warehouse=st.secrets["SNOWFLAKE_WAREHOUSE"],
            database=st.secrets.get("SNOWFLAKE_DATABASE"),
            schema=st.secrets.get("SNOWFLAKE_SCHEMA"),
        )
    except Exception as e:
        logging.error(f"Failed to connect to Snowflake: {str(e)}")
        st.error(f"Failed to connect to Snowflake: {str(e)}")
        snowflake_executor = None
    return snowflake_executor


def get_cache(seed=1):
    return SQLiteCache("cache.db", seed=seed, default_ttl=600)
