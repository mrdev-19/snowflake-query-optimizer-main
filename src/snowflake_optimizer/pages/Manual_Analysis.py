import json
import os
from typing import Optional

import streamlit as st

from snowflake_optimizer.connections import initialize_connections, setup_logging, get_snowflake_query_executor, \
    get_cache
from snowflake_optimizer.data_collector import SnowflakeQueryExecutor
from snowflake_optimizer.models import SchemaInfo, InputAnalysisModel, ColumnInfo
from snowflake_optimizer.query_analyzer import QueryAnalyzer
from snowflake_optimizer.utils import format_sql, split_sql_queries, \
    init_common_states, create_results_expanders, create_export_excel_from_results, evaluate_or_repair_query


def render_manual_analysis_view(page_id: str,
                                analyzer: Optional[QueryAnalyzer],
                                executor: Optional[SnowflakeQueryExecutor]):
    """Render the manual query analysis view."""
    print("\n=== Starting Manual Analysis View ===")
    st.header("Manual Query Analysis")
    setup_logging()

    if not analyzer:
        st.error("Query analyzer is not initialized. Please check your configuration.")
        return

    init_common_states(page_id)
    if f"{page_id}_file_name" not in st.session_state:
        st.session_state[f"{page_id}_file_name"] = None

    # Query input methods
    input_method = st.radio(
        "Choose input method",
        ["Direct Input", "File Upload", "Batch Analysis"]
    )

    # Store current batch results
    current_batch_results = st.session_state[f"{page_id}_batch_results"].copy() if hasattr(st.session_state,
                                                                                           'batch_results') else []

    if input_method == "Direct Input":
        st.markdown("### Enter SQL Query")

        # Format button before text area
        if st.button("Format Query"):
            if st.session_state[f"{page_id}_formatted_query"]:
                st.session_state[f"{page_id}_formatted_query"] = format_sql(
                    st.session_state[f"{page_id}_formatted_query"])

        # Text area for SQL input
        query = st.text_area(
            "SQL Query",
            value=st.session_state[f"{page_id}_formatted_query"],
            height=200,
            help="Paste your SQL query here for analysis",
            key="sql_input"
        )

        # Update formatted_query only if query has changed
        if query != st.session_state[f"{page_id}_formatted_query"]:
            query = format_sql(query)
            st.session_state[f"{page_id}_formatted_query"] = query

        if query:
            st.markdown("### Preview")
            st.code(query, language="sql")

        # Optional schema information
        if st.checkbox("Add table schema information"):
            schema_col1, schema_col2 = st.columns([1, 1])

            with schema_col1:
                table_name = st.text_input("Table name")
                row_count = st.number_input("Approximate row count", min_value=0)

            with schema_col2:
                columns_json = st.text_area(
                    "Columns (JSON format)",
                    help='Example: [{"column_name": "id", "column_type": "INTEGER"}]'
                )

            try:
                columns = json.loads(columns_json) if columns_json else []
                columns = [ColumnInfo(column_name=column['column_name'], column_type=column['data_type']) for
                           column in columns]
                st.session_state[f"{page_id}_schema_info"] = SchemaInfo(
                    table_name=table_name,
                    columns=columns,
                    row_count=row_count
                )
            except json.JSONDecodeError:
                st.error("Invalid JSON format for columns")
                st.session_state[f"{page_id}_schema_info"] = None

        analyze_button = st.button("Analyze", on_click=lambda: __analyze_query_callback(page_id, analyzer))

    elif input_method == "File Upload":
        st.markdown("### Upload SQL File")
        uploaded_file = st.file_uploader("Choose a SQL file", type=["sql"])

        if uploaded_file:
            query = uploaded_file.getvalue().decode()
            queries = split_sql_queries(query)
            if len(queries) > 1:
                st.error(f"You uploaded a file with {len(queries)} queries. Please use Batch load instead")
            else:
                st.session_state[f"{page_id}_formatted_query"] = format_sql(queries[0])
                st.session_state[f"{page_id}_file_name"] = uploaded_file.name
                st.markdown("### Preview")
                st.code(st.session_state[f"{page_id}_formatted_query"], language="sql")

            analyze_button = st.button("Analyze", on_click=lambda: __analyze_query_callback(page_id, analyzer))
        else:
            # Clean results
            st.session_state[f"{page_id}_analysis_results"] = None

    elif input_method == "Batch Analysis":
        st.markdown("### Upload SQL Files")
        uploaded_files = st.file_uploader("Choose SQL files", type=["sql"], accept_multiple_files=True)

        if uploaded_files:
            # Initialize progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()

            # Process uploaded files
            all_queries = []
            for sql_file in uploaded_files:
                content = sql_file.getvalue().decode()
                queries = split_sql_queries(content)
                print(f"\n=== Splitting SQL Queries ===")
                print(f"Found {len(queries)} queries in {sql_file.name}")
                for i, query in enumerate(queries):
                    print(f"Found valid query of length: {len(query)}")
                    all_queries.append(InputAnalysisModel(
                        file_name_or_query_id=f"{sql_file.name} (Query {i + 1})",
                        query=format_sql(query),
                    ))
            print(f"Total queries found: {len(all_queries)}")

            analyze_button = st.button("Analyze All", key="batch_analyze")
            if analyze_button:
                max_parallel_call = os.cpu_count()
                batch_results = []
                for query_index in range(0, len(all_queries), max_parallel_call):
                    query_batches = all_queries[query_index:query_index + max_parallel_call]
                    progress = query_index / len(all_queries)
                    progress_bar.progress(progress)
                    status_text.markdown(
                        "Analyzing:\n * " + '\n* '.join([q.file_name_or_query_id for q in query_batches]))
                    try:
                        batch_results.extend(analyzer.analyze_query(query_batches))
                    except Exception as e:
                        st.error(f"Failed to analyze the Batch: {e}")

                batch_results = sorted(batch_results, key=lambda res: res['filename'])
                batch_results = [evaluate_or_repair_query(output_analysis=result,
                                                          executor=executor,
                                                          analyzer=analyzer) for result in batch_results]

                st.session_state[f"{page_id}_batch_results"] = batch_results
                status_text.text("Analysis complete!")

            # Display results if available
            if st.session_state.get(f"{page_id}_batch_results"):
                st.markdown("### Analysis Results")
                create_results_expanders(executor, st.session_state[f"{page_id}_batch_results"])
                create_export_excel_from_results(st.session_state[f"{page_id}_batch_results"])

    # Display analysis results if available
    if st.session_state.get(f"{page_id}_analysis_results"):
        results = st.session_state[f"{page_id}_analysis_results"]
        results = [evaluate_or_repair_query(output_analysis=result,
                                            executor=executor,
                                            analyzer=analyzer) for result in results]
        st.session_state[f"{page_id}_analysis_results"] = results

        create_results_expanders(executor, results)
        create_export_excel_from_results(results)


def __analyze_query_callback(page_id, analyzer: Optional[QueryAnalyzer]):
    """Callback function for analyzing queries in the manual analysis view.

    Args:
        analyzer: QueryAnalyzer instance to use for analysis
    """
    print("\n=== Starting Query Analysis Callback ===")

    if not analyzer:
        print("No analyzer available")
        st.error("Query analyzer is not initialized")
        return

    if not st.session_state[f"{page_id}_formatted_query"]:
        print("No query to analyze")
        return

    try:
        print(f'Analyzing query of length: {len(st.session_state[f"{page_id}_formatted_query"])}')
        file_name = st.session_state.get(f"{page_id}_file_name", 'UI QUERY')
        result = analyzer.analyze_query(
            [InputAnalysisModel(
                file_name_or_query_id=file_name,
                query=st.session_state[f"{page_id}_formatted_query"],
                schema_info=st.session_state[f"{page_id}_schema_info"] if hasattr(st.session_state, 'schema_info') else None
            )]
        )
        st.session_state[f"{page_id}_analysis_results"] = result
        print("Analysis completed successfully")

        # Store the analyzed query for comparison
        st.session_state[f"{page_id}_selected_query"] = st.session_state[f"{page_id}_formatted_query"]

    except Exception as e:
        print(f"Analysis failed: {str(e)}")
        st.error(f"Analysis failed: {str(e)}")
        st.session_state[f"{page_id}_analysis_results"] = None


def main():
    st.set_page_config(page_title="Manual Analysis")
    page_id = 'manual_analysis'
    # Initialize connections
    _collector, _analyzer = initialize_connections(page_id, get_cache(1))
    executor = get_snowflake_query_executor()
    render_manual_analysis_view(page_id, _analyzer, executor)


main()
