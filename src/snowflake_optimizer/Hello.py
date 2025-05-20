"""Main Streamlit application for Snowflake Query Optimizer."""

import logging
from typing import List, Dict

import streamlit as st
from dotenv import load_dotenv

from snowflake_optimizer.connections import initialize_connections, get_snowflake_query_executor
from snowflake_optimizer.data_collector import SnowflakeQueryExecutor
from snowflake_optimizer.utils import show_performance_difference

# Load environment variables
load_dotenv()


def group_related_queries(queries: List[Dict]) -> List[Dict]:
    """Group related queries based on common tables and patterns.
    
    Args:
        queries: List of query dictionaries with analysis results
        
    Returns:
        List of query groups with optimization suggestions
    """
    groups = []
    processed = set()

    for i, query in enumerate(queries):
        if i in processed:
            continue

        related = {i}
        base_tables = set(query.get('tables', []))

        # Find related queries
        for j, other in enumerate(queries):
            if j != i and j not in processed:
                other_tables = set(other.get('tables', []))
                # If queries share tables or have similar patterns
                if (base_tables & other_tables) or (
                        query['analysis'].category == other['analysis'].category
                ):
                    related.add(j)

        # Create group
        group = {
            'queries': [queries[idx] for idx in related],
            'common_tables': base_tables,
            'category': query['analysis'].category,
            'group_suggestions': []
        }

        # Aggregate group-level suggestions
        all_suggestions = []
        for q in group['queries']:
            if q['analysis'].suggestions:
                all_suggestions.extend(q['analysis'].suggestions)

        # Find common suggestions
        if all_suggestions:
            from collections import Counter
            suggestion_counts = Counter(all_suggestions)
            group['group_suggestions'] = [
                sugg for sugg, count in suggestion_counts.items()
                if count > 1  # Suggestion appears in multiple queries
            ]

        groups.append(group)
        processed.update(related)

    return groups


def get_error_analysis_prompt(query: str) -> str:
    """Generate the prompt for LLM to analyze SQL query errors and anti-patterns.
    
    Args:
        query: SQL query to analyze
        
    Returns:
        Formatted prompt for LLM
    """
    return f"""Analyze the following SQL query for potential errors, anti-patterns, and optimization opportunities. 
Provide a detailed analysis in the following JSON format:

{{
    "error_patterns": [
        {{
            "category": "One of: PERFORMANCE, DATA_QUALITY, COMPLEXITY, BEST_PRACTICE, SECURITY, MAINTAINABILITY",
            "code": "One of: FTS001, IJN001, IDX001, LDT001, NUL001, DTM001, NSQ001, CJN001, WCD001, ALS001, INJ001, PRM001, CMT001, FMT001",
            "pattern": "Name of the anti-pattern",
            "severity": "One of: High, Medium, Low",
            "impact": "Brief impact description",
            "location": "Where in the query this occurs",
            "description": "Detailed explanation of the issue",
            "recommendation": "How to fix or improve"
        }}
    ],
    "query_metrics": {{
        "complexity_score": "Score from 0-1",
        "readability_score": "Score from 0-1",
        "maintainability_score": "Score from 0-1",
        "performance_impact": "Score from 0-1",
        "structural_metrics": {{
            "num_joins": "Number",
            "num_conditions": "Number",
            "nesting_depth": "Number",
            "num_aggregations": "Number"
        }}
    }}
}}

Anti-pattern Categories and Codes:
1. PERFORMANCE:
   - FTS001: Full Table Scan - Query performs a full table scan without appropriate filtering
   - IJN001: Inefficient Join - Join conditions missing or using non-indexed columns
   - IDX001: Missing Index - Frequently filtered or joined columns lack appropriate indexes
   - LDT001: Large Data Transfer - Query retrieves excessive data volume

2. DATA_QUALITY:
   - NUL001: Unsafe Null Handling - Improper handling of NULL values in comparisons
   - DTM001: Data Type Mismatch - Implicit data type conversions in comparisons

3. COMPLEXITY:
   - NSQ001: Nested Subquery - Deeply nested subqueries that could be simplified
   - CJN001: Complex Join Chain - Long chain of joins that could be simplified

4. BEST_PRACTICE:
   - WCD001: Wildcard Column Usage - Using SELECT * instead of specific columns
   - ALS001: Missing Table Alias - Tables or subqueries without clear aliases

5. SECURITY:
   - INJ001: SQL Injection Risk - Potential SQL injection vulnerabilities
   - PRM001: Missing Parameterization - Hard-coded values instead of parameters

6. MAINTAINABILITY:
   - CMT001: Missing Comments - Complex logic without explanatory comments
   - FMT001: Poor Formatting - Inconsistent or poor SQL formatting

Focus on:
1. Performance implications
2. Logical correctness
3. Best practices
4. Maintainability issues
5. Security concerns
6. Complexity assessment

Query to analyze:
{query}

Provide the analysis in the exact JSON format specified above."""


def main():
    """Main function to run the Streamlit application."""
    logging.info("Starting main application")
    st.title("Snowflake Query Optimizer")
    st.write("Analyze and optimize your Snowflake SQL queries")


logging.debug("Main application loop completed")

if __name__ == "__main__":
    main()
