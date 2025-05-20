import pytest
from unittest.mock import Mock, patch, MagicMock
import os
import logging
from datetime import datetime
from openai import AzureOpenAI

from snowflake_optimizer.connections import (
    setup_logging,
    initialize_connections,
    get_snowflake_query_executor,
    get_cache,
)


@pytest.fixture
def mock_streamlit():
    with patch('snowflake_optimizer.connections.st') as mock_st:
        mock_st.secrets = {
            'SNOWFLAKE_ACCOUNT': 'test_account',
            'SNOWFLAKE_USER': 'test_user',
            'SNOWFLAKE_PASSWORD': 'test_pass',
            'SNOWFLAKE_WAREHOUSE': 'test_warehouse',
            'SNOWFLAKE_DATABASE': 'test_db',
            'SNOWFLAKE_SCHEMA': 'test_schema',
            'API_KEY': 'test_api_key',
            'API_VERSION': 'test_version',
            'API_ENDPOINT': 'test_endpoint',
            'DEPLOYMENT_NAME': 'test_model'
        }
        mock_st.session_state = {}
        yield mock_st


@pytest.fixture
def mock_cache():
    return Mock()


def test_setup_logging(tmp_path):
    with patch('snowflake_optimizer.connections.os.path.exists', return_value=False), \
            patch('snowflake_optimizer.connections.os.makedirs') as mock_makedirs, \
            patch('snowflake_optimizer.connections.logging') as mock_logging, \
            patch('snowflake_optimizer.connections.datetime') as mock_datetime:
        mock_datetime.now.return_value = datetime(2024, 1, 1)
        setup_logging()

        mock_makedirs.assert_called_once_with('logs')
        mock_logging.FileHandler.assert_called_once()
        mock_logging.info.assert_called_with("Snowflake Query Optimizer application started")


def test_initialize_connections_success(mock_streamlit, mock_cache):
    with patch('snowflake_optimizer.connections.QueryMetricsCollector') as mock_collector, \
            patch('snowflake_optimizer.connections.QueryAnalyzer') as mock_analyzer, \
            patch('snowflake_optimizer.connections.AzureOpenAI') as mock_azure:
        mock_collector_instance = Mock()
        mock_collector.return_value = mock_collector_instance

        mock_azure_instance = Mock()
        mock_azure.return_value = mock_azure_instance

        collector, analyzer = initialize_connections('test_page', mock_cache)

        assert collector == mock_collector_instance
        assert analyzer is not None
        mock_collector.assert_called_once_with(
            account='test_account',
            user='test_user',
            password='test_pass',
            warehouse='test_warehouse',
            database='test_db',
            schema='test_schema'
        )


def test_initialize_connections_snowflake_failure(mock_streamlit, mock_cache):
    with patch('snowflake_optimizer.connections.QueryMetricsCollector', side_effect=Exception("Snowflake error")), \
            patch('snowflake_optimizer.connections.QueryAnalyzer') as mock_analyzer:
        collector, analyzer = initialize_connections('test_page', mock_cache)

        assert collector is None
        assert mock_streamlit.error.called
        assert "Failed to connect to Snowflake" in mock_streamlit.error.call_args[0][0]


def test_initialize_connections_analyzer_failure(mock_streamlit, mock_cache):
    with patch('snowflake_optimizer.connections.QueryMetricsCollector') as mock_collector, \
            patch('snowflake_optimizer.connections.AzureOpenAI', side_effect=Exception("Azure error")):
        collector, analyzer = initialize_connections('test_page', mock_cache)

        assert collector is not None
        assert analyzer is None
        assert mock_streamlit.error.called
        assert "Failed to initialize Query Analyzer" in mock_streamlit.error.call_args[0][0]


def test_get_snowflake_query_executor_success(mock_streamlit):
    with patch('snowflake_optimizer.connections.SnowflakeQueryExecutor') as mock_executor:
        mock_executor_instance = Mock()
        mock_executor.return_value = mock_executor_instance

        executor = get_snowflake_query_executor()

        assert executor == mock_executor_instance
        mock_executor.assert_called_once_with(
            account='test_account',
            user='test_user',
            password='test_pass',
            warehouse='test_warehouse',
            database='test_db',
            schema='test_schema'
        )


def test_get_snowflake_query_executor_failure(mock_streamlit):
    with patch('snowflake_optimizer.connections.SnowflakeQueryExecutor', side_effect=Exception("Connection error")):
        executor = get_snowflake_query_executor()

        assert executor is None
        assert mock_streamlit.error.called
        assert "Failed to connect to Snowflake" in mock_streamlit.error.call_args[0][0]


def test_get_cache():
    with patch('snowflake_optimizer.connections.SQLiteCache') as mock_cache:
        mock_cache_instance = Mock()
        mock_cache.return_value = mock_cache_instance

        cache = get_cache(seed=42)

        assert cache == mock_cache_instance
        mock_cache.assert_called_once_with("cache.db", seed=42, default_ttl=600)


def test_initialize_connections_reuse_existing_analyzer(mock_streamlit, mock_cache):
    with patch('snowflake_optimizer.connections.QueryMetricsCollector') as mock_collector, \
            patch('snowflake_optimizer.connections.QueryAnalyzer') as mock_analyzer:
        # First initialization
        mock_streamlit.session_state = {}
        initialize_connections('test_page', mock_cache)

        # Second initialization
        collector, analyzer = initialize_connections('test_page', mock_cache)

        # Verify QueryAnalyzer was only instantiated once
        assert mock_analyzer.call_count == 1