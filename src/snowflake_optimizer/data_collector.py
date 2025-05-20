import collections
import time
from typing import Dict, Any, Optional, Literal, Callable, List

import pandas as pd
import streamlit
from snowflake.snowpark import Session, DataFrame
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError, ProgrammingError

from snowflake_optimizer.models import SchemaInfo, ColumnInfo


class SnowflakeDataCollector:
    def __init__(
            self,
            account: str,
            user: str,
            warehouse: str,
            database: Optional[str] = None,
            schema: Optional[str] = None,
    ):
        """Initialize the collector with Snowflake credentials using externalbrowser authentication."""

        self.__connection_params = {
            "account": account,
            "user": user,
            "authenticator": "externalbrowser",  # Use browser-based SSO
            "warehouse": warehouse,
            "database": database,
            "schema": schema,
        }

        # Construct the SQLAlchemy connection URL
        conn_url = (
            f"snowflake://{user}@{account}/"
            f"?authenticator=externalbrowser"
        )
        self._engine = create_engine(conn_url)

        # Create Snowpark session generator
        self._snowpark_session_generator: Callable[[], Session] = lambda: Session.builder.configs(
            self.__connection_params).create()


class QueryMetricsCollector(SnowflakeDataCollector):
    """Collects query performance metrics from Snowflake."""

    def get_databases(self):
        query = """
        SELECT DATABASE_NAME 
        FROM INFORMATION_SCHEMA.DATABASES 
        WHERE IS_TRANSIENT = 'NO'
        ORDER BY DATABASE_NAME;
        """.lstrip()

        with self._engine.connect() as conn:
            df = pd.read_sql(
                query,
                conn
            )
            return df.to_dict(orient='records')

    def get_expensive_queries_paginated(self, days: int = 7,
                                      min_execution_time: float = 60.0,
                                      limit: int = 100,
                                      page=0, page_size=20,
                                      db_schema_filter=''):
        df = self.get_expensive_queries(days, min_execution_time, limit, db_schema_filter)
        start_idx = page * page_size
        end_idx = start_idx + page_size

        total_pages = (len(df) - 1) // page_size + 1
        return df.iloc[start_idx:end_idx], total_pages

    @streamlit.cache_data(show_spinner="Fetching Query History")
    def get_expensive_queries(
            _self,
            days: int = 7,
            min_execution_time: float = 60.0,
            limit: int = 100,
            db_schema_filter=''
    ) -> pd.DataFrame:
        """Fetch expensive queries from Snowflake query history.

        Args:
            days: Number of days to look back
            min_execution_time: Minimum execution time in seconds
            limit: Maximum number of queries to return
            db_schema_filter: Filter by database and schema name

        Returns:
            DataFrame containing query metrics
        """
        if db_schema_filter != '':
            db_schemas_filter_condition = f"AND (DATABASE_NAME || '.' || SCHEMA_NAME) LIKE '{db_schema_filter}%'"
        else:
            db_schemas_filter_condition = ''
            
        query = f"""WITH RankedQueries AS (
            SELECT 
                QUERY_ID,
                QUERY_TEXT,
                '' AS QUERY_HASH,  -- INFORMATION_SCHEMA doesn't provide query hash
                USER_NAME,
                DATABASE_NAME,
                SCHEMA_NAME,
                WAREHOUSE_NAME,
                TOTAL_ELAPSED_TIME / 1000 AS EXECUTION_TIME_SECONDS,
                BYTES_SCANNED / 1024 / 1024 AS MB_SCANNED,
                ROWS_PRODUCED,
                COMPILATION_TIME / 1000 AS COMPILATION_TIME_SECONDS,
                EXECUTION_STATUS,
                ERROR_MESSAGE,
                START_TIME,
                END_TIME,
                PARTITIONS_SCANNED,
                PARTITIONS_TOTAL,
                BYTES_SPILLED_TO_LOCAL_STORAGE / 1024 / 1024 AS MB_SPILLED_TO_LOCAL,
                BYTES_SPILLED_TO_REMOTE_STORAGE / 1024 / 1024 AS MB_SPILLED_TO_REMOTE,
                ROW_NUMBER() OVER (PARTITION BY QUERY_TEXT ORDER BY START_TIME DESC) AS RN
            FROM INFORMATION_SCHEMA.QUERY_HISTORY
            WHERE 
                TOTAL_ELAPSED_TIME >= {min_execution_time * 1000}
                AND START_TIME >= DATEADD('days', -{days}, CURRENT_TIMESTAMP())
                AND EXECUTION_STATUS = 'SUCCESS'
                AND QUERY_TYPE = 'SELECT'
                {db_schemas_filter_condition}
        )
        SELECT rq.*
        FROM RankedQueries rq
        WHERE RN = 1
        ORDER BY EXECUTION_TIME_SECONDS DESC
        LIMIT {limit};"""

        with _self._engine.connect() as conn:
            df = pd.read_sql(
                query,
                conn
            )
        return df

    @streamlit.cache_data(show_spinner=False)
    def get_impacted_objects(_self, query_id: str) -> pd.DataFrame:
        """
        Fetch impacted objects metadata by query_id

        Args:
            query_id: The Snowflake query ID

        Returns:
            DataFrame containing the objects metadata
        """
        query = f"""
            SELECT DISTINCT OBJECT_NAME AS table_name
            FROM INFORMATION_SCHEMA.OBJECT_DEPENDENCIES
            WHERE REFERENCED_OBJECT_ID IN (
                SELECT OBJECT_ID 
                FROM INFORMATION_SCHEMA.QUERY_HISTORY 
                WHERE QUERY_ID = '{query_id}'
            )
            AND OBJECT_TYPE = 'TABLE';
        """
        with _self._engine.connect() as conn:
            df = pd.read_sql(query, conn)
        return df

    @streamlit.cache_data(show_spinner=False)
    def get_impacted_objects_metadata(_self, impacted_objects: pd.DataFrame) -> List[SchemaInfo]:
        """
        Fetch impacted objects metadata by query_id

        Args:
            impacted_objects: The Snowflake impacted objects

        Returns:
            List of SchemaInfo containing the objects metadata
        """
        metadata = []
        for _, row in impacted_objects.iterrows():
            object_name = row['table_name']
            try:
                table_catalog, table_schema, table_name = object_name.split('.')
            except ValueError:
                print(f"Invalid object name format: {object_name}")
                continue
                
            desc_query = f"""
                SELECT COLUMN_NAME, DATA_TYPE
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE 
                    TABLE_CATALOG = '{table_catalog}' 
                    AND TABLE_SCHEMA = '{table_schema}' 
                    AND TABLE_NAME = '{table_name}';
            """
            try:
                with _self._engine.connect() as conn:
                    columns_dict = pd.read_sql(desc_query, conn).to_dict(orient="records")
                    columns_dict = [ColumnInfo(column_name=column['COLUMN_NAME'], column_type=column['DATA_TYPE']) for
                                  column in columns_dict]
            except Exception as e:
                print(f"No metadata for object: {object_name} in INFORMATION_SCHEMA.COLUMNS: {str(e)}")
                columns_dict = []

            try:
                query = f"""
                    SELECT ROW_COUNT, BYTES
                    FROM INFORMATION_SCHEMA.TABLES 
                    WHERE
                        TABLE_CATALOG = '{table_catalog}' 
                        AND TABLE_SCHEMA = '{table_schema}' 
                        AND TABLE_NAME = '{table_name}';
                """
                with _self._engine.connect() as conn:
                    metadata_dict = pd.read_sql(query, conn).to_dict(orient="records")
                    metadata_dict = metadata_dict[0] if metadata_dict else {}
            except Exception as e:
                print(f"No metadata for object: {object_name} in INFORMATION_SCHEMA.TABLES: {str(e)}")
                metadata_dict = {}

            metadata ACO.append(SchemaInfo(
                table_name=object_name,
                columns=columns_dict,
                row_count=metadata_dict.get("ROW_COUNT", 0),
                size_bytes=metadata_dict.get("BYTES", 0)
            ))
        return metadata

    def get_query_plan(self, query_id: str) -> Dict[str, Any]:
        """Fetch the query execution plan for a specific query.

        Args:
            query_id: The Snowflake query ID

        Returns:
            Dictionary containing the query plan details
        """
        query = "SELECT * FROM TABLE(GET_QUERY_OPERATOR_STATS(:1))"

        with self._engine.connect() as conn:
            df = pd.read_sql(query, conn, params=[query_id])
        return df.to_dict(orient="records")


class SnowflakeQueryExecutor(SnowflakeDataCollector):
    def execute_query_in_transaction(self, query: str = None,
                                   snowpark_job: Callable[[Session], Any] = None,
                                   action_on_complete: Literal["commit", "rollback"] = 'rollback') -> DataFrame:
        with SnowflakeSessionTransaction(session_gen=self._snowpark_session_generator,
                                       action_on_complete=action_on_complete) as session:
            if query:
                return session.sql(query)
            elif snowpark_job:
                return snowpark_job(session)
            else:
                raise ValueError('No query or snowpark_job specified')

    def compare_optimized_query_with_original(self, optimized_query, original_query, waiting_timeout_in_secs=None) -> (
            pd.DataFrame, pd.DataFrame, pd.DataFrame):

        def gather_query_data(query: str, session: Session):
            async_job = session.sql(query).collect(block=False)
            start_time = time.time()
            query_id = async_job.query_id
            async_def_job = pd.DataFrame()
            retry_seconds = 5
            while async_def_job.empty:
                query_df_qh = session.sql(
                    f""" select  
                                        QUERY_ID,
                                        QUERY_TEXT,
                                        TOTAL_ELAPSED_TIME / 1000 AS EXECUTION_TIME_SECONDS,
                                        BYTES_SCANNED / 1024 / 1024 AS MB_SCANNED,
                                        ROWS_PRODUCED,
                                        COMPILATION_TIME / 1000 AS COMPILATION_TIME_SECONDS,
                                        CREDITS_USED_CLOUD_SERVICES,
                                        EXECUTION_STATUS,
                                        ERROR_MESSAGE
                                from table(INFORMATION_SCHEMA.QUERY_HISTORY_BY_SESSION({session.session_id})) 
                                where query_id = '{query_id}' 
                                and EXECUTION_STATUS IN ('SUCCESS', 'FAILED_WITH_ERROR')
                                """.lstrip()
                ).to_pandas()
                print(query_df_qh)
                if query_df_qh.shape[0] > 0:
                    failure_df = query_df_qh[query_df_qh['EXECUTION_STATUS'] == 'FAILED_WITH_ERROR']
                    if failure_df.shape[0] > 0:
                        raise Exception(str(failure_df['ERROR_MESSAGE'].iloc[0]))
                    async_def_job = query_df_qh
                else:
                    end_time = time.time()
                    if waiting_timeout_in_secs is not None and end_time - start_time > waiting_timeout_in_secs:
                        raise TimeoutError(f'Evaluation ran for more than {waiting_timeout_in_secs}')
                    time.sleep(retry_seconds)
                    retry_seconds *= 2
            return async_def_job

        original_query_df = self.execute_query_in_transaction(
            snowpark_job=lambda session: gather_query_data(original_query, session))
        num_columns = original_query_df.select_dtypes(include=['number']).columns
        original_query_df = original_query_df[num_columns]
        optimized_query_df = self.execute_query_in_transaction(
            snowpark_job=lambda session: gather_query_data(optimized_query, session))
        optimized_query_df = optimized_query_df[num_columns]
        # Compute the differences
        diff_values = optimized_query_df[num_columns].iloc[0] - original_query_df[num_columns].iloc[0]
        return original_query_df, optimized_query_df, diff_values.to_frame().transpose()

    def compile_query(self, query) -> Optional[str]:
        try:
            with self._engine.connect() as conn:
                conn.execute(text(f'EXPLAIN {query}')).fetchone()
                return None
        except ProgrammingError as e:
            return ''.join(e.orig.args)


class SnowflakeSessionTransaction:
    def __init__(
            self,
            session_gen: Callable[[], Session],
            action_on_complete: Literal["commit", "rollback"],
            action_on_error: Literal["commit", "rollback"] = 'rollback',
    ):
        self.session = session_gen()
        self.actioned = False
        self.action_on_complete = action_on_complete
        if action_on_complete not in ["commit", "rollback"]:
            raise ValueError(f"Invalid action_on_complete action {action_on_complete}")
        self.action_on_error = action_on_error
        if action_on_error not in ["commit", "rollback"]:
            raise ValueError(f"Invalid action_on_error action {action_on_error}")

    def __enter__(self):
        self.session.sql("begin transaction").collect()
        return self.session

    def commit(self):
        self.session.sql("commit").collect()
        self.actioned = True

    def rollback(self):
        self.session.sql("rollback").collect()
        self.actioned = True

    def __exit__(self, exc_type, exc_val, exc_tb):
        # if we already actioned, don't do anything
        if not self.actioned:
            # if an error was thrown, rollback
            if exc_type is not None:
                self.session.sql(self.action_on_error).collect()
                self.session.close()
            else:
                self.session.sql(self.action_on_complete).collect()
                self.session.close()