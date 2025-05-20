import logging
import os
from datetime import datetime
from typing import Optional

import streamlit as st
from dotenv import load_dotenv
import snowflake.connector
import litellm

from snowflake_optimizer.cache import SQLiteCache, BaseCache
from snowflake_optimizer.query_analyzer import QueryAnalyzer

load_dotenv()


# Configure logging
def setup_logging():
    """Configure logging with custom format and handlers."""
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file = os.path.join(log_dir, f"snowflake_optimizer_{datetime.now().strftime('%Y%m%d')}.log")

    file_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(funcName)s | %(message)s'
    )
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)

    logging.info("Snowflake Query Optimizer application started")
    logging.debug(f"Log file created at: {log_file}")


def initialize_connections(page_id, cache: BaseCache = None) -> tuple[Optional[snowflake.connector.SnowflakeConnection], Optional[QueryAnalyzer]]:
    """Initialize connections to Snowflake and LLM services."""
    logging.info("Initializing service connections")

    # Snowflake Connection
    try:
        logging.debug("Connecting to Snowflake using snowflake.connector")
        conn = snowflake.connector.connect(
            user=st.secrets["SNOWFLAKE_USER"],
            account=st.secrets["SNOWFLAKE_ACCOUNT"],
            warehouse=st.secrets["SNOWFLAKE_WAREHOUSE"],
            database=st.secrets.get("SNOWFLAKE_DATABASE"),
            schema=st.secrets.get("SNOWFLAKE_SCHEMA"),
            authenticator='externalbrowser' 
        )
        logging.info("Successfully connected to Snowflake")
    except Exception as e:
        logging.error(f"Failed to connect to Snowflake: {str(e)}")
        st.error(f"Failed to connect to Snowflake: {str(e)}")
        conn = None

    # LLM Initialization using LiteLLM
    try:
        logging.debug("Initializing LLM via LiteLLM")
        litellm.api_key = st.secrets["LITELLM_API_KEY"]
        model_name = st.secrets["LITELLM_MODEL"]

        if f'{page_id}_analyzer' not in st.session_state:
            analyzer = QueryAnalyzer(
                openai_model=model_name,
                cache=cache,
                litellm_client=litellm  
            )
            st.session_state[f'{page_id}_analyzer'] = analyzer
        else:
            analyzer = st.session_state[f'{page_id}_analyzer']

        logging.info("Successfully initialized Query Analyzer with LiteLLM")
    except Exception as e:
        logging.error(f"Failed to initialize LLM: {str(e)}")
        st.error(f"Failed to initialize LLM: {str(e)}")
        analyzer = None

    return conn, analyzer


def get_snowflake_query_executor() -> Optional[snowflake.connector.SnowflakeConnection]:
    try:
        conn = snowflake.connector.connect(
            user=st.secrets["SNOWFLAKE_USER"],
            account=st.secrets["SNOWFLAKE_ACCOUNT"],
            warehouse=st.secrets["SNOWFLAKE_WAREHOUSE"],
            database=st.secrets.get("SNOWFLAKE_DATABASE"),
            schema=st.secrets.get("SNOWFLAKE_SCHEMA"),
            authenticator='externalbrowser'  # <-- this line enables SSO login
        )
        return conn
    except Exception as e:
        logging.error(f"Failed to connect to Snowflake: {str(e)}")
        st.error(f"Failed to connect to Snowflake: {str(e)}")
        return None


def get_cache(seed=1):
    return SQLiteCache("cache.db", seed=seed, default_ttl=600)
