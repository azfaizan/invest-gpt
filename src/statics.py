from datetime import datetime, timedelta
today = datetime.today().date()

STATICS = {
"cryptocurrency_meta_info":"""
                          Description: Retrieves detailed information about specific cryptocurrencies.
                          Parameters:
                          slug (string, required): A comma-separated list of cryptocurrency slugs to fetch information for (e.g., 'bitcoin,ethereum,solana').

                          Returns: A string containing detailed information about the specified cryptocurrencies, including id, name, symbol, category, description, slug, logo, subreddit, notice, tags, tag-names, tag-groups, urls, and more, formatted as a text string.
                          """,


"cryptocurrency_price_performance_stats":"""
                                          Description: Retrieves the latest price performance statistics for specific cryptocurrencies.

                                          Parameters:
                                          - id (integer or string, required): A comma-separated list of cryptocurrency IDs to fetch performance statistics for (e.g., '1,1027,5426' for Bitcoin, Ethereum, and Solana).

                                          Returns: A string containing price performance statistics for the specified cryptocurrencies, including data for different time periods, formatted as a text string.
                                          """,


"cryptocurrency_historical_quotes":"""
                                      Description: Retrieves historical price quotes for specified cryptocurrencies over a given time period from the CoinMarketCap API, returning selected attributes as a formatted string.
                                      Limitations: Historical data access is restricted to a specific time range (e.g., 24 months from the current date, with start dates typically required to be newer than a specific threshold, such as April 21, 2023). The 'monthly' interval is not supported; valid intervals include 'daily', 'hourly'.
                                      Parameters:

                                      - id (string, required): A comma-separated list of cryptocurrency IDs from CoinMarketCap (e.g., '1,1765' for Bitcoin and EOS).
                                      - time_start (string, required): Start time in ISO 8601 format (e.g., '2025-04-01').
                                      - time_end (string, required): End time in ISO 8601 format (e.g., '2025-04-03').
                                      - count (integer, optional): Number of data points to return. Defaults to 1.
                                      - interval (string, optional): Time interval must be one of: weekly, daily, hourly, 5m, 10m, 15m, 30m, 45m, 1h, 2h, 3h, 4h, 6h, 12h, 24h, 1d, 2d, 3d, 7d, 14d, 15d, 30d
                                      - attributes (array, optional): List of attributes to extract (e.g., \['price', 'market_cap'\]). Allowed values: 'price', 'market_cap', 'volume_24h', 'percent_change_1h', 'percent_change_24h', 'percent_change_7d', 'percent_change_30d', 'total_supply', 'circulating_supply'. Defaults to \['price', 'market_cap'\].
                                      - convert (string, optional): Currency for price conversion (e.g., 'USD'). Defaults to 'USD'.

                                      Returns: A formatted string of historical quotes in the format 'timestamp,attribute:value', concatenated for each attribute, timestamp, and cryptocurrency. In case of an error, returns a string in the format 'error:error_message'.""",

"portfolio":"""
              Description: Retrieves details of the user's stock portfolio and cryptocurrency portfolio/profile information.
              Parameters: None
              Returns: A string containing stock portfolio data, including holdings, pending orders, and total portfolio value, as well as cryptocurrency portfolio data, formatted as a text string.
                                      """,


"web_search":"""
                Description: Searches the web for real-time cryptocurrency information using the Tavily API. Acts as a critical fallback when other API data is insufficient, providing access to the most current market information, news, and trends not captured in structured API responses.

                Parameters:

                - query (string, required): The search query for cryptocurrency information. Should be specific and targeted to retrieve the most relevant results.
                - days (integer, optional): Number of days to look back. Use smaller values for recent information, larger values for historical context. Defaults to 7.
                - include_domains (array, optional): List of domains to include in the search. Defaults to \['https://coinmarketcap.com/currencies/\*/historical-data/'\]. Target authoritative sources based on the specific information needed.
                - exclude_domains (array, optional): List of domains to exclude from the search. Use to filter out potentially misleading or low-quality sources.

                Returns: A string containing search results and information from the web, including content, images, and summaries that can supplement or replace data from other functions when necessary, formatted as a text string.
                """,


"create_plot":"""
                  Description: Creates a single visualization (pie, bar, scatter, line, or histogram) with customizable options.

                  Parameters:

                  - data (array, required): List of data points, each containing:
                    - name (string, required): Name or label of the data point.
                    - value (number, required): Numerical value of the data point.
                    - category (string, optional): Category for grouping and color coding.
                    - x (number, optional): X-axis value for scatter, line, and bar plots.
                    - y (number, optional): Y-axis value for scatter, line, and bar plots.
                    - size (number, optional): Size value for scatter plot markers.
                  - plot_type (string, optional): Type of plot to create ('pie', 'bar', 'scatter', 'line', 'histogram'). Defaults to 'pie'.
                  - title (string, optional): Title to display on the chart. Defaults to 'Data Visualization'.
                  - x_column (string, optional): Column name for x-axis (for bar, scatter, line, histogram).
                  - y_column (string, optional): Column name for y-axis (for bar, scatter, line).
                  - color_column (string, optional): Column name for color grouping.
                  - size_column (string, optional): Column name for marker size (for scatter).
                  - text_column (string, optional): Column name for hover text.
                  - color_map (object, optional): Mapping of categories to specific colors.
                  - width (integer, optional): Width of the chart in pixels. Defaults to 800.
                  - height (integer, optional): Height of the chart in pixels. Defaults to 600.
                  - hole_size (number, optional): Size of the donut hole (0 for pie chart, 0-1 for donut chart). Defaults to 0.5.
                  - show_percentage (boolean, optional): Whether to show percentage labels on the chart. Defaults to true.
                  - show_total_value (boolean, optional): Whether to show the total value in the center of the chart. Defaults to true.
                  - show_values (boolean, optional): Whether to show values on bar charts. Defaults to true.
                  - show_legend (boolean, optional): Whether to show the legend. Defaults to true.
                  - mode (string, optional): Mode for scatter/line plots ('markers', 'lines', 'lines+markers'). Defaults to 'markers'.
                  - nbinsx (integer, optional): Number of bins for histogram. Defaults to 30.

                  Returns: A visualization (pie, bar, scatter, line, or histogram) based on the provided data and customization options, formatted as a text string describing the chart.
                  """,

"create_subplots":"""
                    Description: Creates multiple visualizations in a single figure for comparison or multi-view analysis.

                    Parameters:

                    - data (object, required): Dictionary with subplot indices as keys, containing data for each subplot. Each subplot data is an object with trace names as keys.
                    - plot_types (array, required): List of plot types for each subplot ('pie', 'bar', 'scatter', 'line', 'histogram').
                    - title (string, optional): Main title for the entire figure. Defaults to 'Multi-View Analysis'.
                    - subplot_titles (array, optional): List of titles for each subplot.
                    - rows (integer, optional): Number of rows in the subplot grid. Defaults to 1.
                    - cols (integer, optional): Number of columns in the subplot grid. Defaults to 2.
                    - width (integer, optional): Width of the entire figure in pixels. Defaults to 1000.
                    - height (integer, optional): Height of the entire figure in pixels. Defaults to 600.
                    - column_widths (array, optional): List of relative widths for subplot columns.
                    - barmode (string, optional): Mode for bar plots ('group', 'stack', 'relative'). Defaults to 'group'.
                    - colors (array, optional): List of colors for traces.
                    - show_legend (boolean, optional): Whether to show the legend. Defaults to true.

                    Returns: A single figure containing multiple visualizations (pie, bar, scatter, line, or histogram) arranged in a grid for comparison or multi-view analysis, formatted as a text string describing the figure.
                    """,

"get_current_date":"""
                      Description: Gets the current date in ISO 8601 format.

                      Parameters:
                      - utc (boolean, optional): Whether to return UTC time (default: False)

                      Returns: Current date and time in ISO 8601 format.
                      """,

"crypto_search":"""
                    Description: Searches for cryptocurrencies and stocks by name, symbol, or partial match.

                    Parameters:
                    - query (string, required): The name or symbol of the cryptocurrency or stock to search for (e.g., 'bitcoin', 'ethereum', 'btc', 'apple', 'msft', 'tesla')
                    - threshold (integer, optional): The minimum match score (0-100) required to include a result. Higher values require closer matches. Default: 70
                    - limit (integer, optional): Maximum number of results to return. Default: 10

                    Returns: A list of matching assets with their rank/ID, name, and slug/ticker sorted by relevance. Use this tool to find IDs when you only know the name or symbol.
                    """

}

CRYPTO_LIST = []
EXCHANGE_LIST = []
LAST_REFRESH = 0
CACHE_DURATION = 24 * 60 * 60  # 24 hours in seconds

COIN_MARKET_CAP_API_BASE_URL = "pro-api.coinmarketcap.com"

INVESTMENT_MARKET_API_BASE_URL = "api-stg-invmkt.agentmarket.ae"


