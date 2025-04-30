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
                                **Description:**  
                                This function retrieves historical price quotes for specified cryptocurrencies over a defined time period using the CoinMarketCap API. It fetches the requested attributes (e.g., price, market cap) and stores the data in a pandas DataFrame. After successful retrieval, the function returns a statistical summary (`DataFrame.describe()`) that includes information about the columns and a statistical overview of the data.
                                **Functionality:**  
                                - Fetches historical cryptocurrency data for specified coins and time ranges.  
                                - Supports customizable intervals and attribute selection.  
                                - Saves the retrieved data into a structured pandas DataFrame.  
                                - Returns a summary of the dataset using `DataFrame.describe()`, which includes count, mean, standard deviation, min, max, and percentiles of numeric columns.
                                **Limitations:**  
                                - Access to historical data is limited to a specific range, within the last 24 months.  
                                - The `monthly` interval is not supported. Valid intervals include: 'daily', 'hourly', '5m', '10m', '15m', '30m', '45m', '1h', '2h', '3h', '4h', '6h', '12h', '24h', '1d', '2d', '3d', '7d', '14d', '15d', '30d'.  
                                - The start date must be after a specific threshold (e.g., April 21, 2023).
                                **Parameters:**  
                                - **id** (string, required): Comma-separated list of CoinMarketCap cryptocurrency IDs (e.g., `'1,1765'` for Bitcoin and EOS).  
                                - **time_start** (string, required): Start time in ISO 8601 format (e.g., `'2025-04-01'`).  
                                - **time_end** (string, required): End time in ISO 8601 format (e.g., `'2025-04-03'`).  
                                - **count** (integer, optional): Number of data points to return. Default is 1.  
                                - **interval** (string, optional): Time interval for data granularity.  
                                - **attributes** (array, optional): List of attributes to retrieve (e.g., `['price', 'market_cap']`). Allowed values include: `'price'`, `'market_cap'`, `'volume_24h'`, `'percent_change_1h'`, `'percent_change_24h'`, `'percent_change_7d'`, `'percent_change_30d'`, `'total_supply'`, `'circulating_supply'`. Default is `['price', 'market_cap']`.  
                                - **convert** (string, optional): Currency for conversion (e.g., `'USD'`). Default is `'USD'`.
                                **Returns:**  
                                A pandas `DataFrame.describe()` output providing statistical insights into the requested historical data. In case of an error during the API call or data processing, a string in the format `'error:error_message'` is returned.
""",

"portfolio":"""
              Description: Retrieves details of the user's stock portfolio and cryptocurrency portfolio, creates a DataFrame, and returns statistical analysis.
              Parameters: None
              Returns: A statistical summary of the portfolio DataFrame including stocks and cryptocurrencies with metrics such as quantity, average cost, current price, value, and profit/loss information. The summary shows count, mean, standard deviation, min, max and percentiles of numeric columns as well as information about categorical columns. The data is stored in the global historical_quotes_df for potential further analysis using the manipulate_dataset function.
                                      """,


"web_search":"""
                Description: Searches the web for real-time information using OpenAI's Chat API.
                Parameters:
                - query (string, required): The search query for information. Should be specific and targeted to retrieve the most relevant results.
                Returns: A string containing the search results and information from the web, formatted as a concise and accurate response based on the search results.
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
                    """,

"manipulate_dataset":"""
                    Description: Executes custom Python code to manipulate the cryptocurrency data retrieved by the historical_quotes function.
                    Parameters:
                    - code_string (string, required): Python code to execute on the historical_quotes_df DataFrame. Must modify or analyze the global 'historical_quotes_df' variable.
                    Available variables:
                    - historical_quotes_df: Pandas DataFrame containing the historical cryptocurrency data
                    - pd: Pandas library (import pandas as pd)
                    - np: NumPy library (import numpy as np)
                    Example code:
                    ```python
                    # Filter data for a specific crypto ID
                    historical_quotes_df = historical_quotes_df[historical_quotes_df['crypto_id'] == '1']
                    
                    # Calculate moving averages
                    historical_quotes_df['7day_ma'] = historical_quotes_df['price'].rolling(7).mean()
                    
                    # Create new columns
                    historical_quotes_df['price_normalized'] = historical_quotes_df['price'] / historical_quotes_df['price'].iloc[0]
                    ```
                    RULES:
                    1. NEVER rename the historical_quotes_df variable
                    2. NEVER create any new DataFrame - only use and modify the existing historical_quotes_df
                    3. All manipulations must be performed on the global historical_quotes_df variable
                    4. Return values will be ignored - changes must be made to the historical_quotes_df variable directly
                    
                    Returns: Statistical summary of the modified DataFrame using pandas `describe(include='all')` method. If an error occurs during execution, returns an error message.
                    """,

"plotting_with_generated_code":"""
                               Description: Generates a plot from cryptocurrency data using custom Plotly code.

                               Parameters:
                               - code_string (string, required): Plotly Python code to create a visualization. Must create a figure named 'fig'.

                               Available variables:
                               - historical_quotes_df: Pandas DataFrame containing the required data
                               - pd: Pandas library
                               - go: Plotly's graph_objects module
                               - pc: Plotly's colors module
                               - make_subplots:  make_subplots for comparitive analysis.
                               Best practice:
                               - Plot size must be minimum 1024x1024.
                               - Make sure to use the full width and height of the plot.
                               - Use the make_subplots function to create a subplot for comparitive analysis.
                        
                              """

}

CRYPTO_LIST = []
EXCHANGE_LIST = []
LAST_REFRESH = 0
CACHE_DURATION = 24 * 60 * 60  # 24 hours in seconds

COIN_MARKET_CAP_API_BASE_URL = "pro-api.coinmarketcap.com"

INVESTMENT_MARKET_API_BASE_URL = "api-stg-invmkt.agentmarket.ae"


plot = None
historical_quotes_df = None

WEBSEARCH_MODEL="gpt-4o-search-preview-2025-03-11"

MODEL_NAME="gpt-4o-2024-11-20"
