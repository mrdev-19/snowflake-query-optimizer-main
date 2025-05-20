import streamlit as st

from snowflake_optimizer.connections import initialize_connections, setup_logging, get_snowflake_query_executor, \
    get_cache
from snowflake_optimizer.data_collector import SnowflakeQueryExecutor
from snowflake_optimizer.models import InputAnalysisModel
from snowflake_optimizer.query_analyzer import QueryAnalyzer
from snowflake_optimizer.utils import init_common_states, create_results_expanders, \
    create_export_excel_from_results, evaluate_or_repair_query


def render_advanced_optimization_view(page_id,
                                      analyzer: QueryAnalyzer,
                                      executor: SnowflakeQueryExecutor):
    """Render the advanced optimization view."""
    st.markdown("## Advanced Optimization Mode")
    setup_logging()
    init_common_states(page_id)
    # Input section
    st.markdown("### Query Input")
    query = st.text_area("Enter your SQL query", height=200, key="advanced_sql_input")

    col1, col2 = st.columns(2)
    with col1:
        schema_info = st.text_area("Table Schema Information (Optional)",
                                   placeholder="Enter table definitions, indexes, etc.",
                                   height=150)
    with col2:
        partition_info = st.text_area("Partitioning Details (Optional)",
                                      placeholder="Enter partitioning strategy details",
                                      height=150)

    # Analysis options
    st.markdown("### Optimization Options")
    col1, col2, col3 = st.columns(3)
    with col1:
        analyze_clustering = st.checkbox("Analyze Clustering Keys", value=True)
        suggest_materialization = st.checkbox("Suggest Materialization", value=True)
    with col2:
        analyze_search = st.checkbox("Analyze Search Optimization", value=True)
        suggest_caching = st.checkbox("Suggest Caching Strategy", value=True)
    with col3:
        analyze_partitioning = st.checkbox("Analyze Partitioning", value=True)

    if st.button("Analyze Query"):
        if query:
            try:
                with st.spinner("Analyzing query..."):
                    result = analyzer.analyze_query(
                        [InputAnalysisModel(
                            query=query,
                            file_name_or_query_id='UI QUERY',
                            schema_info=schema_info if schema_info else None
                        )],
                        # partition_info=partition_info if partition_info else None,
                        # analyze_clustering=analyze_clustering,
                        # suggest_materialization=suggest_materialization,
                        # analyze_search=analyze_search,
                        # suggest_caching=suggest_caching,
                        # analyze_partitioning=analyze_partitioning
                    )
                    st.session_state[f"{page_id}_analysis_results"] = result
            except Exception as e:
                st.error(f"Analysis failed: {str(e)}")
        else:
            st.warning("Please enter a SQL query to analyze.")
    if st.session_state.get(f"{page_id}_analysis_results"):
        results = st.session_state[f"{page_id}_analysis_results"]
        results = [evaluate_or_repair_query(output_analysis=result,
                                            executor=executor,
                                            analyzer=analyzer) for result in results]
        st.session_state[f"{page_id}_analysis_results"] = results

        create_results_expanders(executor, results)
        create_export_excel_from_results(results)
    else:
        st.error("Failed to analyze query. Please try again.")


def main():
    st.set_page_config(page_title="Advanced Optimization")
    page_id = 'advanced_optimization'
    # Initialize connections
    _collector, _analyzer = initialize_connections(page_id, get_cache(1))
    executor = get_snowflake_query_executor()
    render_advanced_optimization_view(page_id, _analyzer, executor)


main()
