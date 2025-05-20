import logging, os
from typing import Optional

import streamlit as st
from dotenv import load_dotenv

from snowflake_optimizer.connections import setup_logging, initialize_connections, get_cache, \
    get_snowflake_query_executor
from snowflake_optimizer.data_collector import QueryMetricsCollector, SnowflakeQueryExecutor
from snowflake_optimizer.models import InputAnalysisModel
from snowflake_optimizer.query_analyzer import QueryAnalyzer
from snowflake_optimizer.utils import format_sql, init_common_states, \
    create_results_expanders, create_export_excel_from_results, evaluate_or_repair_query


def render_query_history_view(page_id: str,
                              collector: Optional[QueryMetricsCollector],
                              analyzer: Optional[QueryAnalyzer],
                              executor: Optional[SnowflakeQueryExecutor]):
    """Render the query history analysis view.

    Args:
        page_id (str): The ID of the page to render.
        collector: QueryMetricsCollector instance
        analyzer: QueryAnalyzer instance
        executor: SnowflakeQueryExecutor instance
    """

    # Set up logging
    setup_logging()

    # Load environment variables
    load_dotenv()

    init_common_states(page_id)

    if f"{page_id}_selected_query_id" not in st.session_state:
        st.session_state[f"{page_id}_selected_query_id"] = None

    logging.info("Rendering query history view")
    st.header("Query History Analysis")

    # Sidebar configuration
    with st.spinner('Loading Page'):
        with st.expander("History Configuration", expanded=False):

            days = st.slider(
                "Days to analyze",
                min_value=1,
                max_value=30,
                value=1,
                help="Number of days to look back in query history"
            )
            min_execution_time = st.number_input(
                "Minimum execution time (seconds)",
                min_value=1,
                value=60,
                help="Minimum query execution time to consider"
            )
            limit = st.number_input(
                "Number of queries",
                min_value=1,
                max_value=1000,
                value=50,
                help="Maximum number of queries to analyze"
            )

            page_size = st.number_input(
                "Page Size",
                min_value=1,
                max_value=1000,
                value=10,
                help="Page Size for Pagination."
            )

            database_schemas_filter = st.selectbox(label="Filter by DATABASE",
                                                   options=_get_databases(collector),
                                                   index=0)

            logging.debug(
                f"Query history parameters - days: {days}, min_execution_time: {min_execution_time}, limit: {limit}")

            fetch_query_btn = st.button("Fetch Queries")

            if fetch_query_btn:
                if collector:
                    logging.info("Fetching query history from Snowflake")
                    with st.spinner("Fetching query history..."):
                        try:
                            if f"{page_id}_current_page" not in st.session_state:
                                st.session_state[f"{page_id}_current_page"] = 0
                        except Exception as e:
                            logging.error(f"Failed to fetch query history: {str(e)}")
                            st.error(f"Failed to fetch queries: {str(e)}")
                else:
                    logging.error("Cannot fetch queries - Snowflake connection not available")
                    st.error("Snowflake connection not available")

    with st.container():
        if f"{page_id}_current_page" in st.session_state:
            query_history, total_pages = collector.get_expensive_queries_paginated(
                days=days,
                min_execution_time=min_execution_time,
                limit=limit,
                page_size=page_size,
                page=st.session_state[f"{page_id}_current_page"],
                db_schema_filter=database_schemas_filter
            )
            st.info("Select queries from the dataframe below clicking on the left of the table")
            row = st.dataframe(
                query_history[[
                    "query_id",
                    "execution_time_seconds",
                    "mb_scanned",
                    "rows_produced"
                ]],
                hide_index=True,
                on_select="rerun",
                selection_mode="multi-row",
            )
            prev_col, space_col, next_col = st.columns([1, 3, 1])
            if prev_col.button("Previous") and st.session_state[f"{page_id}_current_page"] > 0:
                st.session_state[f"{page_id}_current_page"] -= 1
            if next_col.button("Next") and st.session_state[f"{page_id}_current_page"] < total_pages - 1:
                st.session_state[f"{page_id}_current_page"] += 1
            if len(row['selection']['rows']) > 0:
                selected_item = row['selection']['rows'][0]
                selected_query = query_history.iloc[selected_item]
                st.session_state[f"{page_id}_selected_query_id"] = selected_query['query_id']
                st.session_state[f"{page_id}_selected_query"] = format_sql(selected_query['query_text'])
                st.session_state[f"{page_id}_formatted_query"] = st.session_state[f"{page_id}_selected_query"]

    with st.container():
        if st.session_state[f"{page_id}_selected_query"]:
            st.markdown("### Selected Queries")
            if len(row['selection']['rows']) > 0:
                for i in row['selection']['rows']:
                    selected_row = query_history.iloc[i]

                    with st.expander(f"Query_id: {selected_row['query_id']}"):
                        st.code(format_sql(selected_row['query_text']), language="sql")

                if st.button("Analyze Query"):
                    if analyzer:
                        logging.info("Starting query analysis")
                        with st.spinner("Analyzing queries..."):
                            status_text = st.empty()
                            all_queries = []
                            for i in row['selection']['rows']:
                                selected_row = query_history.iloc[i]
                                impacted_objects = collector.get_impacted_objects(
                                    selected_row['query_id']
                                )
                                objects_metadata = collector.get_impacted_objects_metadata(
                                    impacted_objects
                                )
                                all_queries.append(InputAnalysisModel(
                                    file_name_or_query_id=selected_row['query_id'],
                                    query=format_sql(selected_row['query_text']),
                                    schema_info=objects_metadata
                                ))

                            max_parallel_call = os.cpu_count()
                            batch_results = []
                            for query_index in range(0, len(all_queries), max_parallel_call):
                                query_batches = all_queries[query_index:query_index + max_parallel_call]
                                try:
                                    batch_results.extend(analyzer.analyze_query(query_batches))
                                except Exception as e:
                                    st.error(f"Failed to analyze the Batch: {e}")

                            batch_results = sorted(batch_results, key=lambda res: res['filename'])
                            batch_results = [evaluate_or_repair_query(output_analysis=result,
                                                                      executor=executor,
                                                                      analyzer=analyzer) for result in batch_results]

                            st.session_state[f"{page_id}_analysis_results"] = batch_results
                            status_text.text("Analysis completed!")

        if st.session_state[f"{page_id}_analysis_results"]:
            st.markdown("### Analysis Results")
            # create_results_expanders(st.session_state[f"{page_id}_analysis_results"])
            create_results_expanders(executor, st.session_state[f"{page_id}_analysis_results"])
            create_export_excel_from_results(st.session_state[f"{page_id}_analysis_results"])


@st.cache_data(show_spinner="Loading Databases")
def _get_databases(_collector):
    db_schemas = _collector.get_databases()
    return [''] + [elem['database_name'] for elem in db_schemas]


def main():
    st.set_page_config(page_title="Query History")
    page_id = 'query_history'
    # Initialize connections
    _collector, _analyzer = initialize_connections(page_id, get_cache(1))
    executor = get_snowflake_query_executor()
    render_query_history_view(page_id, _collector, _analyzer, executor)


main()
