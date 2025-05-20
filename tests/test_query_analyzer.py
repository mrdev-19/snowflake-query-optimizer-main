import pytest
from unittest.mock import Mock, patch
from openai import OpenAI
from sqlglot import exp

from snowflake_optimizer.models import SchemaInfo, QueryCategory, QueryAnalysis, InputAnalysisModel, \
    OutputAnalysisModel, ColumnInfo
from snowflake_optimizer.query_analyzer import QueryAnalyzer


@pytest.fixture
def mock_openai_client():
    client = Mock(spec=OpenAI)
    client.chat = Mock()
    client.chat.completions = Mock()

    def mock_completion(*args, **kwargs):
        user_msg = kwargs.get("messages", [{}])[-1].get("content", "")
        mock_resp = Mock()

        if "The following query is invalid" in user_msg:
            mock_resp.content = "```sql\nSELECT id FROM users WHERE status = 'active'\n```"
        elif "antipatterns" in user_msg:
            mock_resp.content = '{"antipatterns": [{"code": "FTS001", "name": "Full Table Scan"}], "suggestions": ["Add index"], "complexity_score": 0.5}'
        elif "optimization" in user_msg:
            mock_resp.content = "- Add index on frequently filtered columns\n- Use specific column names"
        else:
            mock_resp.content = "- Suggestion 1\n- Suggestion 2"

        return Mock(choices=[Mock(message=mock_resp)])

    client.chat.completions.create = Mock(side_effect=mock_completion)
    return client


@pytest.fixture
def query_analyzer(mock_openai_client):
    return QueryAnalyzer(
        openai_client=mock_openai_client,
        openai_model="gpt-4",
        cache=None
    )


@pytest.fixture
def sample_schema_info():
    return SchemaInfo(
        table_name="users",
        columns=[
            ColumnInfo(column_name="id", column_type="INTEGER"),
            ColumnInfo(column_name="name", column_type="VARCHAR"),
            ColumnInfo(column_name="created_at", column_type="TIMESTAMP")
        ]
    )


def test_repair_query(query_analyzer):
    """Test repair_query successfully fixes SQL syntax errors."""
    invalid_query = "SELECT id FORM users WEHRE status = 'active'"
    repaired = query_analyzer.repair_query(invalid_query, "Syntax error")
    assert repaired == "SELECT id FROM users WHERE status = 'active'"


def test_suggest_indexes(query_analyzer, sample_schema_info):
    """Test index suggestions are generated."""
    query = "SELECT * FROM db.schema.users WHERE created_at > '2024-01-01'"
    mock_completion = Mock()
    mock_completion.choices = [Mock(message=Mock(content="Consider adding indexes on filter columns: created_at"))]
    query_analyzer.client.chat.completions.create.return_value = mock_completion

    suggestions = query_analyzer._suggest_indexes(query, sample_schema_info)
    assert len(suggestions) == 0


def test_analyze_query_structure(query_analyzer):
    """Test query structure analysis."""
    query = """
        SELECT e.*, d.name
        FROM employees e
        LEFT JOIN departments d ON e.dept_id = d.id
        WHERE e.salary > 50000
    """
    suggestions = query_analyzer._analyze_query_structure(query)
    assert len(suggestions) > 0
    assert isinstance(suggestions[0], str)


def test_error_handling(query_analyzer):
    """Test error handling in query analysis."""
    invalid_query = "SELECT * FORM users WEHRE id = 1"
    mock_completion = Mock()
    mock_completion.choices = [Mock(message=Mock(
        content='{"antipatterns": [{"code": "FTS001", "name": "Full Table Scan"}], "suggestions": ["Fix syntax errors"], "complexity_score": 0.5}'))]
    query_analyzer.client.chat.completions.create.return_value = mock_completion

    analysis = query_analyzer._analyze_query(invalid_query)
    assert isinstance(analysis, QueryAnalysis)
    assert len(analysis.antipatterns) == 0
    assert len(analysis.suggestions) > 0


def test_analyze_query_batch(query_analyzer):
    """Test batch query analysis."""
    queries = [
        InputAnalysisModel(
            file_name_or_query_id="query1.sql",
            query="SELECT * FROM users"
        ),
        InputAnalysisModel(
            file_name_or_query_id="query2.sql",
            query="SELECT id, name FROM users WHERE active = true"
        )
    ]

    results = query_analyzer.analyze_query(queries)
    assert len(results) == 2
    assert all(isinstance(result, OutputAnalysisModel) for result in results)
