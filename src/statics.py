from datetime import datetime, timedelta
from langchain.agents.structured_chat import prompt

today = datetime.today().date()



STATICS = {
"cryptocurrency_historical_quotes":"""
                                **Description:**  
                                This function retrieves historical price quotes for specified cryptocurrencies over a defined time period using the CoinMarketCap API. It fetches the requested attributes (e.g., price, market cap) and stores the data in a pandas DataFrame(historical_quotes_df). 
                                **Limitations:**  
                                - Access to historical data is limited to a specific range, within the last 24 months.  
                                - The `monthly` interval is not supported. Valid intervals include: 'daily', 'hourly', '5m', '10m', '15m', '30m', '45m', '1h', '2h', '3h', '4h', '6h', '12h', '24h', '1d', '2d', '3d', '7d', '14d', '15d', '30d'.  
                                - The start date must be after a specific threshold (e.g., April 21, 2023).
                               **Returns:**  
                                A pandas `DataFrame.describe()` output providing statistical insights into the requested historical data. In case of an error during the API call or data processing, a string in the format `'error:error_message'` is returned.
""",

"portfolio":"""
              Description: Retrieves details of the user's stock portfolio and cryptocurrency portfolio, creates a DataFrame, and returns statistical analysis.
              Returns: A statistical summary of the portfolio.""",

"portfolio_data":"""
              Description: Retrieves detailed information about the user's stock and cryptocurrency portfolio in JSON format.
              Returns: A JSON object containing complete portfolio data including stocks, crypto, and summary statistics with calculated values and percentages.""",

"web_search":"""
                Description: Searches the web for comprehensive financial information using OpenAI's Chat API.
                Parameters:
                - query (string, required): The search query about financial information. Can be about any financial topic.
                Returns: A comprehensive and accurate response based on real-time web search results, including current market data, historical context, key statistics, relevant news, expert insights, and risk factors.
                """,

"get_current_date":"""
                      Description: Gets the current date in ISO 8601 format.
                      Parameters:
                      - utc (boolean, optional): Whether to return UTC time (default: False)
                      Returns: Current date and time in ISO 8601 format.
                      """,

"manipulate_dataset":"""
                    Description: Executes custom Python code to manipulate the cryptocurrency data retrieved by the historical_quotes function.
                    Available variables:
                    - historical_quotes_df: Pandas DataFrame containing the historical cryptocurrency data
                    - pd: Pandas library (import pandas as pd)
                    - np: NumPy library (import numpy as np)
                    RULES:
                    1. NEVER rename the historical_quotes_df variable
                    2. NEVER create any new DataFrame - only use and modify the existing historical_quotes_df
                    3. All manipulations must be performed on the global historical_quotes_df variable
                    4. Return values will be ignored - changes must be made to the historical_quotes_df variable directly
                    Returns: Statistical summary of the modified DataFrame using pandas `describe(include='all')` method. If an error occurs during execution, returns an error message.
                    """,

"plotting_with_generated_code":"""
                               Description: You can use this tool to plot the data available in the historical_quotes_df variable.
                               RULES: Code must be written in Plotly. using following libraries:
                                import time,pandas as pd , numpy as np
                                import plotly.graph_objects as go
                                import plotly.colors as pc
                                from plotly.subplots import make_subplots
                                import pandas as pd
                                Code must not show the fig.show() or fig.write_html() functions.
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

MODEL_NAME="gpt-4o"

prompt.PREFIX=f"""
Today's Date is: {datetime.today().strftime('%Y-%m-%d')}
System: Respond to the human as helpfully and accurately as possible. And your role is a trading assistant.
When creating visualizations using Plotly, you have access to the complete dataset in historical_quotes_df. The statistical summary you see in the logs is just a representation of the data, but your code can work with the full dataset directly.
"""