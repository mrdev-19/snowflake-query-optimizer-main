import pytest
import pandas as pd
from unittest.mock import Mock, patch
from snowflake_optimizer.utils import (format_sql, split_sql_queries, show_performance_difference,
                                       create_excel_report, evaluate_or_repair_query)


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        'EXECUTION_TIME_SECONDS': [100],
        'MB_SCANNED': [50],
        'ROWS_PRODUCED': [1000],
        'COMPILATION_TIME_SECONDS': [10],
        'CREDITS_USED_CLOUD_SERVICES': [5]
    })


def test_format_sql():
    query = "SELECT col1, col2 FROM table WHERE col1 = 1"
    formatted = format_sql(query)
    assert "SELECT" in formatted
    assert formatted.count('\n') >= 2


def test_split_sql_queries():
    content = """
    SELECT * FROM table1;
    -- Comment
    SELECT col1 FROM table2;
    /* Multi-line
    comment */
    SELECT col2 FROM table3;
    """
    queries = split_sql_queries(content)
    assert len(queries) == 3
    assert all(q.strip().endswith(';') for q in queries)


@patch('streamlit.markdown')
@patch('streamlit.dataframe')
@patch('streamlit.success')
@patch('streamlit.error')
@patch('streamlit.warning')
def test_show_performance_difference(mock_warning, mock_error, mock_success, mock_dataframe, mock_markdown, sample_df):
    difference_df = pd.DataFrame({
        'EXECUTION_TIME_SECONDS': [-10],
        'MB_SCANNED': [-5],
        'ROWS_PRODUCED': [0],
        'COMPILATION_TIME_SECONDS': [-2],
        'CREDITS_USED_CLOUD_SERVICES': [-1]
    })
    show_performance_difference(sample_df, sample_df, difference_df)
    assert mock_success.called
    assert mock_warning.called


def test_create_excel_report():
    batch_results = [{
        'filename': 'test.sql',
        'original_query': 'SELECT * FROM table',
        'analysis': Mock(
            antipatterns=['FTS001'],
            category='PERFORMANCE',
            complexity_score=0.5,
            confidence_score=0.8,
            optimized_query='SELECT col1 FROM table',
            suggestions=['Use specific columns']
        )
    }]
    excel_data = create_excel_report(batch_results)
    assert isinstance(excel_data, bytes)


def test_evaluate_or_repair_query():
    output_analysis = Mock()
    output_analysis.analysis.optimized_query = "SELECT * FROM table"

    analyzer = Mock()
    analyzer.repair_query.return_value = "SELECT col1 FROM table"

    executor = Mock()
    executor.compile_query.return_value = "Error message"

    result = evaluate_or_repair_query(output_analysis, analyzer, executor)
    assert result.analysis.optimized_query == "SELECT col1 FROM table"


def test_show_performance_difference_missing_columns():
    with pytest.raises(ValueError):
        show_performance_difference(
            pd.DataFrame({'col1': [1]}),
            pd.DataFrame({'col1': [1]}),
            pd.DataFrame({'col1': [0]})
        )


def test_create_excel_report_empty():
    with pytest.raises(ValueError):
        create_excel_report([])


def test_format_sql_error():
    with patch('sqlparse.format', side_effect=Exception('Format error')):
        query = "SELECT * FROM table"
        result = format_sql(query)
        assert result == query
