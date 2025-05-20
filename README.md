# Snowflake Query Optimizer

An intelligent SQL query optimization tool powered by Azure OpenAI, designed to analyze and optimize Snowflake queries for better performance.

## Features

### Query Analysis Modes

1. **Query History Analysis**
   - Analyze historical queries from your Snowflake instance
   - Filter by execution time, data scanned, and date range
   - View detailed performance metrics
   - Get intelligent optimization suggestions

2. **Manual Query Analysis**
   - Input queries directly with syntax highlighting
   - Upload SQL files for analysis
   - Batch process multiple queries
   - Add schema information for better optimization
   - Real-time query formatting

3. **Advanced Snowflake Optimization**
   - Specialized optimizations for Snowflake
   - Clustering key analysis
   - Materialized view suggestions
   - Search optimization recommendations
   - Caching strategy optimization
   - Partitioning analysis

### Core Features

- **Intelligent Analysis**
  - SQL syntax validation and formatting
  - Query complexity scoring
  - Antipattern detection
  - Performance impact assessment
  - LLM-powered optimization suggestions

- **Visual Comparison**
  - Side-by-side query comparison
  - Detailed diff highlighting
  - Color-coded changes
  - Easy copy-to-clipboard functionality

- **Schema Analysis**
  - Table statistics integration
  - Column-level optimization
  - Index recommendations
  - Partitioning strategies
  - Storage optimization

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/nareshshah139/snowflake-query-optimizer.git
   cd snowflake-query-optimizer
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   uv pip install -r requirements.txt
   ```

4. Set up credentials:
   Create `.streamlit/secrets.toml` with your credentials:
   ```toml
   # Snowflake credentials
   SNOWFLAKE_ACCOUNT = "your-account"
   SNOWFLAKE_USER = "your-username"
   SNOWFLAKE_PASSWORD = "your-password"
   SNOWFLAKE_WAREHOUSE = "your-warehouse"
   SNOWFLAKE_DATABASE = "your-database"  # Optional
   SNOWFLAKE_SCHEMA = "your-schema"      # Optional

   # Anthropic API key
   ANTHROPIC_API_KEY = "your-claude-api-key"
   ```

## Usage

Run the Streamlit application:
```bash
streamlit run src/snowflake_optimizer/app.py
```

### Query History Analysis
1. Select "Query History Analysis" mode
2. Configure the time range and filters
3. Click "Fetch Queries" to load historical queries
4. Select a query to analyze
5. View performance metrics and optimization suggestions

### Manual Query Analysis
1. Select "Manual Analysis" mode
2. Choose input method (Direct Input/File Upload/Batch)
3. Enter or upload your SQL query
4. Add optional schema information
5. Click "Analyze" to get optimization suggestions

### Advanced Optimization
1. Select "Advanced Optimization" mode
2. Enter your SQL query
3. Configure optimization settings
4. Add detailed schema information
5. Click "Analyze with Advanced Optimizations"
6. View categorized optimization suggestions

## Development

### Running Tests
```bash
pytest tests/ -v
```

### Code Quality
```bash
ruff check .
ruff format .
```

### Project Structure
```
snowflake-optimizer/
├── src/
│   └── snowflake_optimizer/
│       ├── app.py              # Streamlit application
│       ├── data_collector.py   # Snowflake data collection
│       └── query_analyzer.py   # Query analysis logic
├── tests/                      # Test files
├── requirements.txt            # Dependencies
├── README.md                   # Documentation
└── .streamlit/                 # Streamlit configuration
```

## Logging

The application maintains detailed logs in the `logs` directory:
- Daily rotating log files
- Different log levels (DEBUG, INFO, ERROR)
- Performance monitoring
- Error tracking
- User actions

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [Streamlit](https://streamlit.io/)
- Powered by [Claude 3.5 Sonnet](https://www.anthropic.com/) 