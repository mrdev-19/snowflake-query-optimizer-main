from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field


class QueryCategory(str, Enum):
    """Enumeration of query categories."""

    DATA_MANIPULATION = "Data Manipulation"
    REPORTING = "Reporting"
    ETL = "ETL"
    ANALYTICS = "Analytics"
    UNKNOWN = "Unknown"


@dataclass
class ColumnInfo:
    column_name: str
    column_type: str


@dataclass
class SchemaInfo:
    """Contains table schema and statistics information."""

    table_name: str
    columns: List[ColumnInfo]
    row_count: Optional[int] = None
    size_bytes: Optional[int] = None
    indexes: Optional[List[str]] = None
    partitioning: Optional[Dict[str, str]] = None


@dataclass
class QueryAnalysis:
    """Contains the analysis results for a query."""

    original_query: str
    optimized_query: Optional[str]
    antipatterns: List[str]
    suggestions: List[str]
    confidence_score: float
    category: QueryCategory = QueryCategory.UNKNOWN
    complexity_score: float = 0.0
    estimated_cost: Optional[float] = None
    materialization_suggestions: List[str] = None
    index_suggestions: List[str] = None


class InputAnalysisModel(BaseModel):
    file_name_or_query_id: str
    query: str
    schema_info: Optional[List[SchemaInfo]] = Field(default=None, description="List of schema info")


class OutputAnalysisModel(BaseModel):
    filename: str
    original_query: str
    schema_info: Optional[List[SchemaInfo]] = Field(default=None, description="List of schema info")
    analysis: QueryAnalysis

    def __getitem__(self, item):
        return getattr(self, item)

    def __setitem__(self, key, value):
        setattr(self, key, value)


class AntiPattern(BaseModel):
    """Represents a SQL antipattern with its details."""
    code: str = Field(..., description="Antipattern code (e.g., FTS001)")
    name: str = Field(..., description="Name of the antipattern")
    category: str = Field(...,
                          description="Category (PERFORMANCE, DATA_QUALITY, COMPLEXITY, BEST_PRACTICE, SECURITY, MAINTAINABILITY)")
    description: str = Field(..., description="Detailed description of the antipattern")
    impact: str = Field(..., description="Impact level (High, Medium, Low)")
    location: str = Field(..., description="Location in the query where antipattern occurs")
    suggestion: str = Field(..., description="Suggestion to fix the antipattern")


class QueryAnalysisResponse(BaseModel):
    """Structured response for query analysis."""
    antipatterns: List[AntiPattern] = Field(default_factory=list, description="List of antipatterns found in the query")
    suggestions: List[str] = Field(default_factory=list, description="List of optimization suggestions")
    complexity_score: float = Field(..., ge=0, le=1, description="Query complexity score between 0 and 1")


class QueryCategoryResponse(BaseModel):
    """Structured response for query categorization."""
    category: str = Field(..., description="Query category name")
    explanation: str = Field(..., description="Explanation for the categorization")
