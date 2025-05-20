import pytest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from snowflake.snowpark import Session
from sqlalchemy.exc import ProgrammingError
from snowflake_optimizer.data_collector import SnowflakeDataCollector, QueryMetricsCollector, SnowflakeQueryExecutor, \
    SnowflakeSessionTransaction


@pytest.fixture
def snowflake_credentials():
    return {
        "account": "test_account",
        "user": "test_user",
        "password": "test_password",
        "warehouse": "test_warehouse",
        "database": "test_db",
        "schema": "test_schema"
    }


@pytest.fixture
def mock_engine():
    with patch('snowflake_optimizer.data_collector.create_engine') as mock:
        yield mock


@pytest.fixture
def mock_session():
    mock = Mock(spec=Session)
    mock.session_id = "test_session_id"
    return mock


class TestQueryMetricsCollector:
    @pytest.fixture
    def collector(self, snowflake_credentials, mock_engine):
        return QueryMetricsCollector(**snowflake_credentials)

    def test_get_databases(self, collector):
        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_df = pd.DataFrame({'database_name': ['db1', 'db2']})
        with patch('pandas.read_sql', return_value=mock_df):
            with patch.object(collector._engine, 'connect', return_value=mock_conn):
                result = collector.get_databases()
                assert len(result) == 2
                assert result[0]['database_name'] == 'db1'

    def test_get_expensive_queries(self, collector):
        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_df = pd.DataFrame({
            'QUERY_ID': ['1', '2'],
            'EXECUTION_TIME_SECONDS': [100, 200]
        })
        with patch('pandas.read_sql', return_value=mock_df):
            with patch.object(collector._engine, 'connect', return_value=mock_conn):
                result = collector.get_expensive_queries(days=7, min_execution_time=60)
                assert len(result) == 2
                assert result['EXECUTION_TIME_SECONDS'].tolist() == [100, 200]

    def test_get_expensive_queries_paginated(self, collector):
        mock_df = pd.DataFrame({
            'QUERY_ID': range(25),
            'EXECUTION_TIME_SECONDS': range(25)
        })
        with patch.object(collector, 'get_expensive_queries', return_value=mock_df):
            result_df, total_pages = collector.get_expensive_queries_paginated(
                page=0, page_size=10
            )
            assert len(result_df) == 10
            assert total_pages == 3


class TestSnowflakeQueryExecutor:
    @pytest.fixture
    def executor(self, snowflake_credentials, mock_engine):
        return SnowflakeQueryExecutor(**snowflake_credentials)

    def test_execute_query_in_transaction(self, executor, mock_session):
        mock_result = Mock()
        mock_session.sql.return_value = mock_result

        with patch.object(executor, '_snowpark_session_generator', return_value=mock_session):
            result = executor.execute_query_in_transaction(query="SELECT 1")
            assert result == mock_result
            mock_session.sql.assert_any_call("begin transaction")
            mock_session.sql.assert_any_call("SELECT 1")

    def test_compile_query_success(self, executor):
        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.execute().fetchone.return_value = None

        with patch.object(executor._engine, 'connect', return_value=mock_conn):
            result = executor.compile_query("SELECT 1")
            assert result is None

    def test_compile_query_failure(self, executor):
        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        error_message = "Syntax error"
        mock_conn.execute.side_effect = ProgrammingError(statement="", params={}, orig=Exception(error_message))

        with patch.object(executor._engine, 'connect', return_value=mock_conn):
            result = executor.compile_query("SELECT 1")
            assert result == error_message


class TestSnowflakeSessionTransaction:
    def test_successful_transaction(self, mock_session):
        def session_gen():
            return mock_session

        with SnowflakeSessionTransaction(session_gen, "commit") as session:
            assert session == mock_session
            mock_session.sql.assert_called_with("begin transaction")

        mock_session.sql.assert_called_with("commit")
        assert mock_session.close.called

    def test_transaction_with_error(self, mock_session):
        def session_gen():
            return mock_session

        with pytest.raises(ValueError):
            with SnowflakeSessionTransaction(session_gen, "rollback") as session:
                raise ValueError("Test error")

        mock_session.sql.assert_called_with("rollback")
        assert mock_session.close.called

    def test_invalid_action(self):
        with pytest.raises(ValueError):
            SnowflakeSessionTransaction(lambda: None, "invalid_action")
