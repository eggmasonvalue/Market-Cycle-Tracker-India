# Project Conventions

## General Standards
- Use Streamlit for all UI elements.
- Keep UI logic in `src/ui/` and business logic in `src/processing/`.
- Use `requests` for data fetching; avoid complex async logic unless necessary.
- Follow PEP 8 for Python code style.

## Data Handling
- Use `pandas.DataFrame` as the primary data exchange format between modules.
- Ensure date columns are always converted to `datetime` objects for consistent plotting.
- Handle missing data gracefully, especially when merging price and ratio datasets.

## Naming Conventions
- Functions: `snake_case` (e.g., `get_index_data`)
- Variables: `snake_case` (e.g., `df_ratios`)
- Constants: `SCREAMING_SNAKE_CASE` (e.g., `DATE_FMT_API`)

## Visualization
- Use Plotly for interactive charts.
- Maintain a consistent color scheme for metrics across different views.
