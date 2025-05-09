import http.client,os,json,http,logging
from dotenv import load_dotenv
from src.statics import WEBSEARCH_MODEL, MODEL_NAME,CRYPTO_LIST, EXCHANGE_LIST, LAST_REFRESH, CACHE_DURATION, COIN_MARKET_CAP_API_BASE_URL ,INVESTMENT_MARKET_API_BASE_URL,historical_quotes_df
import time,sys,pandas as pd , numpy as np, plotly.graph_objects as go, plotly.colors as pc
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime
from src.utils.logger_factory import LoggerFactory

plot, historical_quotes_df = None, None


# Load environment variables
load_dotenv()
logger = LoggerFactory.create_logger(service_name="invest-gpt")
logger.notice("Application starting up, Logger initialized")


def get_new_token(): 
    conn = http.client.HTTPConnection(INVESTMENT_MARKET_API_BASE_URL)
    payload = json.dumps({
        "refreshToken": os.getenv("REFRESH_TOKEN"),
        "userName": os.getenv("USER_NAME")
    })
    headers = {
        'Content-Type': 'application/json',
    }
    conn.request("POST", "/auth/refresh-token", payload, headers)
    res = conn.getresponse()
    data = res.read()
    data_r = json.loads(data.decode("utf-8"))
    
    # Check if the 'data' key exists in the response
    if 'data' not in data_r:
        logger.error(f"Invalid token response: {json.dumps(data_r)}")
        raise KeyError(f"Expected 'data' key in token response, got: {list(data_r.keys())}")
    
    # Check if the 'accessToken' key exists in the data
    if 'accessToken' not in data_r['data']:
        logger.error(f"No accessToken in response data: {json.dumps(data_r['data'])}")
        raise KeyError(f"Expected 'accessToken' key in data, got: {list(data_r['data'].keys())}")
    
    return data_r['data']['accessToken']

try:
    if not os.getenv("REFRESH_TOKEN") or not os.getenv("USER_NAME"):
        logger.warning("REFRESH_TOKEN or USER_NAME environment variables not set, authentication will fail")
        barear = None
    else:
        barear = f"Bearer {get_new_token()}"
        logger.info("Successfully obtained authentication token")
except Exception as e:
    logger.error(f"Failed to set bearer token: {str(e)}")
    barear = None

payload = ''

def portfolio():
    """
    Get user's portfolio information for both stocks and crypto,
    creates a DataFrame and returns its description.
    
    Returns:
        str: String representation of the portfolio DataFrame's describe() statistics
    """
    global historical_quotes_df
    
    # Get stocks data
    try:
        stocks_data = portfolio_stocks()
        stocks_info = stocks_data.get('data', {}).get('holdings', [])
    except Exception as e:
        stocks_info = []
    
    # Get crypto data
    try:
        crypto_data = portfolio_crypto()
        crypto_info = crypto_data.get('data', {}).get('holdings', [])
    except Exception as e:
        
        crypto_info = []
    
    # Prepare data for DataFrame
    portfolio_records = []
    
    # Process stocks data
    for stock in stocks_info:
        record = {
            'asset_type': 'stock',
            'id': stock.get('id', ''),
            'symbol': stock.get('symbol', ''),
            'name': stock.get('name', ''),
            'quantity': float(stock.get('qty', 0)),
            'average_cost': float(stock.get('averagePrice', 0)),
            'current_price': float(stock.get('price', 0)),
            'value': float(stock.get('value', 0)),
            'invested': float(stock.get('invested', 0)),
            'current_value': float(stock.get('currentValue', 0)),
            'profit_loss': float(stock.get('pl', 0)),
            'profit_loss_percent': float(stock.get('plpc', 0)),
            'holding_percent_change': float(stock.get('holdingPercentChange', 0)),
            'logo': stock.get('logo', '')
        }
        portfolio_records.append(record)
    
    # Process crypto data
    for crypto in crypto_info:
        record = {
            'asset_type': 'crypto',
            'id': crypto.get('id', ''),
            'symbol': crypto.get('symbol', ''),
            'name': crypto.get('name', ''),
            'quantity': float(crypto.get('qty', 0)),
            'average_cost': float(crypto.get('averagePrice', 0)),
            'current_price': float(crypto.get('price', 0)),
            'value': float(crypto.get('value', 0)),
            'invested': float(crypto.get('invested', 0)),
            'current_value': float(crypto.get('currentValue', 0)),
            'profit_loss': float(crypto.get('pl', 0)),
            'profit_loss_percent': float(crypto.get('plpc', 0)),
            'holding_percent_change': float(crypto.get('holdingPercentChange', 0)),
            'logo': crypto.get('logo', '')
        }
        portfolio_records.append(record)
    
    # Create DataFrame
    if not portfolio_records:
        return "{error:No portfolio data available}"
    
    portfolio_df = pd.DataFrame(portfolio_records)
    
    # Store in global variable for potential further manipulation
    historical_quotes_df = portfolio_df
    
    # Return describe() as string
    return portfolio_df.describe(include='all').to_string()

def portfolio_stocks():
    """
    Get user's stock portfolio information
    
    Returns:
        dict: Stock portfolio data
    """
    if not barear:
        return {"error": "Authentication token is not available"}
        
    conn = http.client.HTTPConnection("api-stg-invmkt.agentmarket.ae")
    headers = {
        'Authorization': barear,
    }
    conn.request("GET", "/api-gateway/portfolio/stocks", payload, headers)
    res = conn.getresponse()
    data = res.read()
    return json.loads(data.decode("utf-8"))

def portfolio_crypto():
    """
    Get user's cryptocurrency portfolio information
    
    Returns:
        dict: Cryptocurrency portfolio data
    """
    if not barear:
        return {"error": "Authentication token is not available"}
        
    conn = http.client.HTTPConnection(INVESTMENT_MARKET_API_BASE_URL)
    headers = {
        'Authorization': barear,
    }
    conn.request("GET", "/api-gateway/portfolio/crypto", payload, headers)
    res = conn.getresponse()
    data = res.read()
    return json.loads(data.decode("utf-8"))

def cryptocurrency_historical_quotes(id_list, time_start, time_end, count=1, interval="daily", attributes=["price", "market_cap"], convert="USD"):
    """
    Get historical price quotes for one or more cryptocurrencies over a specified time period,
    storing data in a global DataFrame and returning summarized statistics as a string.
    
    Args:
        id_list (str): Comma-separated list of cryptocurrency IDs from CoinMarketCap
        time_start (str): Start time in ISO 8601 format (e.g., '2024-04-01')
        time_end (str): End time in ISO 8601 format (e.g., '2024-04-01')
        count (int, optional): Number of data points to return. Defaults to 1.
        interval (str, optional): Time interval between data points ('daily', 'hourly', etc). Defaults to 'daily'.
        attributes (list, optional): List of attributes to extract (e.g., ['price', 'market_cap']). Defaults to ['price', 'market_cap'].
        convert (str, optional): Currency to convert quotes to. Defaults to 'USD'.
        
    Returns:
        str: String representation of the DataFrame's describe() statistics
    """
    global historical_quotes_df
    print(f"DEBUG - cryptocurrency_historical_quotes called with: id_list={id_list}, time_start={time_start}, time_end={time_end}, count={count}, interval={interval}, attributes={attributes}, convert={convert}")
    
    if not id_list:
        return "{error:No cryptocurrency IDs provided}"
        
    CMC_API_KEY = os.getenv("CMC_PRO_API_KEY")
    if not CMC_API_KEY:
        return "{error:CMC API key not found}"
    
    conn = http.client.HTTPSConnection("pro-api.coinmarketcap.com")
    headers = {
        'X-CMC_PRO_API_KEY': CMC_API_KEY,
        'Accept': '*/*'
    }
    
    # Build the API endpoint with query parameters
    endpoint = f"/v1/cryptocurrency/quotes/historical?id={id_list}&time_start={time_start}&time_end={time_end}&count={count}&interval={interval}&convert={convert}"
    print(f"DEBUG - API endpoint: {endpoint}")
    
    try:
        conn.request("GET", endpoint, "", headers)
        res = conn.getresponse()
        data = res.read()
        raw_response = data.decode("utf-8")
        
        result = json.loads(raw_response)
        
        if "data" not in result:
            return f"Errot"
        
        # Initialize lists to store DataFrame data
        records = []
        data = result["data"]
        
        # Handle response1 (multiple IDs) or response2 (single ID)
        if isinstance(data, dict) and all(k.isdigit() for k in data.keys()):  # response1: {"1": {"quotes": [...]}, ...}
            for crypto_id, crypto_info in data.items():
                for crypto_data in crypto_info.get("quotes", []):
                    timestamp = crypto_data["timestamp"]
                    currency_data = crypto_data["quote"].get(convert, {})
                    record = {"timestamp": timestamp, "crypto_id": crypto_id}
                    for attr in attributes:
                        if attr in currency_data:
                            record[attr] = currency_data[attr]
                    records.append(record)
        else:  # response2: {"quotes": [...]}
            single_id = id_list.split(",")[0] if "," in id_list else id_list
            for crypto_data in data.get("quotes", []):
                timestamp = crypto_data["timestamp"]
                currency_data = crypto_data["quote"].get(convert, {})
                record = {"timestamp": timestamp, "crypto_id": single_id}
                for attr in attributes:
                    if attr in currency_data:
                        record[attr] = currency_data[attr]
                records.append(record)
        
        if not records:
            logger.error("No valid data found")
            return "{error:No valid data found}"
        
        # Create DataFrame and assign to global variable
        historical_quotes_df = pd.DataFrame(records)
        
        # Convert timestamp to datetime if present
        if "timestamp" in historical_quotes_df.columns:
            historical_quotes_df["timestamp"] = pd.to_datetime(historical_quotes_df["timestamp"])
        
        # Return describe() as string
        return historical_quotes_df.describe(include='all').to_string()
        
    except Exception as e:
        return f"{{error:Error in cryptocurrency_historical_quotes: {str(e)}}}"
    finally:
        conn.close()

def create_pie_chart(labels_col, values_col, title="Portfolio Distribution", df=None):
    """
    Create a pie chart from DataFrame columns.
    
    Args:
        labels_col: Column name for labels
        values_col: Column name for values
        title: Chart title
        df: DataFrame containing the data (defaults to historical_quotes_df)
        
    Returns:
        str: HTML of the plot
    """
    global plot, historical_quotes_df
    df = df or historical_quotes_df
    if df is None:
        return "{error:No DataFrame available}"
        
    try:
        # Calculate percentages for hover text
        total = df[values_col].sum()
        percentages = (df[values_col] / total * 100).round(2)
        
        # Create hover text with value and percentage
        hover_text = [
            f"{label}<br>Value: ${value:,.2f}<br>{percent}%"
            for label, value, percent in zip(df[labels_col], df[values_col], percentages)
        ]
        
        # Create the pie chart with enhanced styling
        fig = go.Figure(data=[go.Pie(
            labels=df[labels_col],
            values=df[values_col],
            hole=.4,  # Slightly larger hole for better aesthetics
            text=df[labels_col],  # Labels inside the pie
            textinfo='percent+label',
            textposition='inside',
            hoverinfo='text',
            hovertext=hover_text,
            marker=dict(
                colors=pc.qualitative.Pastel,  # Use a pastel color palette
                line=dict(color='#000000', width=1)  # Add black borders
            ),
            pull=[0.1 if i == df[values_col].idxmax() else 0 for i in range(len(df))]  # Pull out the largest slice
        )])
        
        # Update layout with enhanced styling
        fig.update_layout(
            title_text=title,
            title_font=dict(size=24, family='Arial', color='#2c3e50'),
            width=1200,  # Wider for better visualization
            height=800,  # Taller for better visualization
            margin=dict(l=50, r=50, t=100, b=50),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            paper_bgcolor='rgba(0,0,0,0)',  # Transparent background
            plot_bgcolor='rgba(0,0,0,0)',   # Transparent background
            annotations=[
                dict(
                    text=f"Total: ${total:,.2f}",
                    x=0.5,
                    y=0.5,
                    font_size=20,
                    showarrow=False
                )
            ]
        )
        
        # Update traces with enhanced text styling
        fig.update_traces(
            textfont=dict(
                family='Arial',
                size=14,
                color='#2c3e50'
            ),
            hovertemplate="%{hovertext}<extra></extra>"
        )
        
        plot = fig.to_html(full_html=False)
        return "plot is saved in cache"
    except Exception as e:
        return f"{{error:Error creating pie chart: {str(e)}}}"

def create_line_chart(x_col, y_cols, title="Price Trend", df=None):
    """
    Create a line chart from DataFrame columns.
    
    Args:
        x_col: Column name for x-axis
        y_cols: List of column names for y-axis
        title: Chart title
        df: DataFrame containing the data (defaults to historical_quotes_df)
        
    Returns:
        str: HTML of the plot
    """
    global plot, historical_quotes_df
    df = df or historical_quotes_df
    if df is None:
        return "{error:No DataFrame available}"
        
    try:
        fig = go.Figure()
        for y_col in y_cols:
            fig.add_trace(go.Scatter(
                x=df[x_col],
                y=df[y_col],
                name=y_col,
                mode='lines'
            ))
        # Set size for line chart with more width for time series
        fig.update_layout(
            title_text=title,
            width=1200,  # Wider for better time series visualization
            height=600,  # Standard height
            margin=dict(l=50, r=50, t=50, b=50)
        )
        plot = fig.to_html(full_html=False)
        return "plot is saved in cache"
    except Exception as e:
        return f"{{error:Error creating line chart: {str(e)}}}"

def create_bar_chart(x_col, y_col, title="Bar Chart", df=None):
    """
    Create a bar chart from DataFrame columns.
    
    Args:
        x_col: Column name for x-axis
        y_col: Column name for y-axis
        title: Chart title
        df: DataFrame containing the data (defaults to historical_quotes_df)
        
    Returns:
        str: HTML of the plot
    """
    global plot, historical_quotes_df
    df = df or historical_quotes_df
    if df is None:
        return "{error:No DataFrame available}"
        
    try:
        fig = go.Figure(data=[go.Bar(
            x=df[x_col],
            y=df[y_col]
        )])
        # Set size for bar chart with more width for bars
        fig.update_layout(
            title_text=title,
            width=1000,  # Wider for better bar spacing
            height=600,  # Standard height
            margin=dict(l=50, r=50, t=50, b=50)
        )
        plot = fig.to_html(full_html=False)
        return "plot is saved in cache"
    except Exception as e:
        return f"{{error:Error creating bar chart: {str(e)}}}"

def create_histogram(column, title="Distribution", df=None):
    """
    Create a histogram from DataFrame column.
    
    Args:
        column: Column name for the histogram
        title: Chart title
        df: DataFrame containing the data (defaults to historical_quotes_df)
        
    Returns:
        str: HTML of the plot
    """
    global plot, historical_quotes_df
    df = df or historical_quotes_df
    if df is None:
        return "{error:No DataFrame available}"
        
    try:
        fig = go.Figure(data=[go.Histogram(
            x=df[column]
        )])
        # Set size for histogram with more width for bins
        fig.update_layout(
            title_text=title,
            width=1000,  # Wider for better bin visualization
            height=600,  # Standard height
            margin=dict(l=50, r=50, t=50, b=50)
        )
        plot = fig.to_html(full_html=False)
        return "plot is saved in cache"
    except Exception as e:
        return f"{{error:Error creating histogram: {str(e)}}}"

def create_scatter_plot(x_col, y_col, color_col=None, title="Scatter Plot", df=None):
    """
    Create a scatter plot from DataFrame columns.
    
    Args:
        x_col: Column name for x-axis
        y_col: Column name for y-axis
        color_col: Column name for color coding (optional)
        title: Chart title
        df: DataFrame containing the data (defaults to historical_quotes_df)
        
    Returns:
        str: HTML of the plot
    """
    global plot, historical_quotes_df
    df = df or historical_quotes_df
    if df is None:
        return "{error:No DataFrame available}"
        
    try:
        fig = go.Figure()
        if color_col:
            fig.add_trace(go.Scatter(
                x=df[x_col],
                y=df[y_col],
                mode='markers',
                marker=dict(
                    color=df[color_col],
                    colorscale='Viridis',
                    showscale=True
                )
            ))
        else:
            fig.add_trace(go.Scatter(
                x=df[x_col],
                y=df[y_col],
                mode='markers'
            ))
        # Set size for scatter plot with more width and less height
        fig.update_layout(
            title_text=title,
            width=1200,  # Wider for better scatter visualization
            height=500,  # Shorter for scatter plots
            margin=dict(l=50, r=50, t=50, b=50)
        )
        plot = fig.to_html(full_html=False)
        return "plot is saved in cache"
    except Exception as e:
        return f"{{error:Error creating scatter plot: {str(e)}}}"

def create_portfolio_visualization(df=None):
    """
    Create a portfolio visualization with two subplots:
    1. Pie chart showing asset distribution
    2. Bar chart showing profit/loss by asset
    
    Args:
        df: DataFrame containing the portfolio data (defaults to historical_quotes_df)
        
    Returns:
        str: Success or error message in a consistent format
    """
    global plot, historical_quotes_df
    
    # If no DataFrame is provided, try to load it
    if df is None and historical_quotes_df is None:
        result = portfolio()
        if isinstance(result, str) and "error" in result:
            return result
    
    df = df or historical_quotes_df
    if df is None:
        return "{error:No portfolio data available. Please load your portfolio first.}"
        
    try:
        # Create subplot figure
        fig = make_subplots(
            rows=1, 
            cols=2,
            specs=[[{"type": "pie"}, {"type": "bar"}]],
            subplot_titles=("Portfolio Distribution", "Profit/Loss by Asset"),
            horizontal_spacing=0.15  # Increase spacing between subplots
        )
        
        # Define a better color palette - using a more visually distinct and professional palette
        colors = [
            '#2E86AB',  # Steel Blue
            '#A23B72',  # Deep Rose
            '#F18F01',  # Orange
            '#C73E1D',  # Vermillion
            '#3B1F2B',  # Dark Purple
            '#44CF6C',  # Emerald
            '#7209B7',  # Royal Purple
            '#4361EE',  # Royal Blue
            '#4CC9F0',  # Sky Blue
            '#F72585',  # Hot Pink
            '#7A9E9F',  # Sage
            '#B5E48C',  # Lime
            '#FF6B6B',  # Coral
            '#4A4E69'   # Slate
        ]
        
        # Calculate total portfolio value
        total_value = df['current_value'].sum()
        
        # Sort data by value for better visualization
        df_sorted = df.sort_values('current_value', ascending=False)
        
        # Create hover text for pie chart
        pie_hover_text = [
            f"{name}<br>Value: ${value:,.2f}<br>{(value/total_value*100):.1f}%"
            for name, value in zip(df_sorted['name'], df_sorted['current_value'])
        ]
        
        # Add pie chart trace
        fig.add_trace(
            go.Pie(
                labels=df_sorted['name'],
                values=df_sorted['current_value'],
                hole=.5,  # Larger hole for better label spacing
                textinfo='percent',  # Only show percentage to reduce clutter
                textposition='outside',  # Move labels outside
                hoverinfo='text',
                hovertext=pie_hover_text,
                marker=dict(
                    colors=colors[:len(df_sorted)],
                    line=dict(color='#ffffff', width=2)
                ),
                pull=[0.1 if i == 0 else 0 for i in range(len(df_sorted))]  # Pull out largest slice
            ),
            row=1, col=1
        )
        
        # Sort data by profit/loss for bar chart
        df_sorted_pl = df.sort_values('profit_loss', ascending=True)
        
        # Create hover text for bar chart
        bar_hover_text = [
            f"{name}<br>P/L: ${pl:,.2f}<br>{pl_percent:.1f}%"
            for name, pl, pl_percent in zip(
                df_sorted_pl['name'],
                df_sorted_pl['profit_loss'],
                df_sorted_pl['profit_loss_percent']
            )
        ]
        
        # Add bar chart trace
        fig.add_trace(
            go.Bar(
                x=df_sorted_pl['name'],
                y=df_sorted_pl['profit_loss'],
                text=df_sorted_pl['profit_loss_percent'].round(1).astype(str) + '%',
                textposition='auto',
                hoverinfo='text',
                hovertext=bar_hover_text,
                marker=dict(
                    color=df_sorted_pl['profit_loss'].apply(
                        lambda x: '#44CF6C' if x >= 0 else '#FF6B6B'  # Softer green and red
                    ),
                    line=dict(color='#ffffff', width=2)
                )
            ),
            row=1, col=2
        )
        
        # Update layout
        fig.update_layout(
            title_text=f"Total Portfolio Value: ${total_value:,.2f}",
            title_font=dict(size=24, family='Arial', color='#2c3e50'),
            width=1800,  # Even wider for better spacing
            height=900,  # Taller for better label visibility
            margin=dict(l=50, r=50, t=120, b=80),  # Increased margins
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
           
        )
        
        # Update pie chart subplot
        fig.update_traces(
            textfont=dict(
                family='Arial',
                size=14,
                color='#2c3e50'
            ),
            hovertemplate="%{hovertext}<extra></extra>",
            selector=dict(type='pie')
        )
        
        # Update bar chart subplot
        fig.update_xaxes(
            title_text="Assets",
            tickangle=45,
            tickfont=dict(size=12),
            row=1, col=2
        )
        fig.update_yaxes(
            title_text="Profit/Loss ($)",
            title_font=dict(size=14),
            tickformat="$,.0f",  # Format y-axis labels as currency
            row=1, col=2,
            gridcolor='rgba(0,0,0,0.1)'  # Light grid lines
        )
        
        plot = fig.to_html(full_html=False)
        return "{success:Portfolio visualization created successfully}"
    except Exception as e:
        return f"{{error:Error creating portfolio visualization: {str(e)}}}"

def portfolio_json():
    """
    Get user's portfolio information for both stocks and crypto in JSON format.
    
    Returns:
        dict: A JSON-serializable dictionary containing portfolio data
    """
    # Get stocks data
    print("*******************", "Getting stocks data")
    try:
        stocks_data = portfolio_stocks()
        stocks_info = stocks_data.get('data').get('holdings', [])
        crypto_data = portfolio_crypto()
        crypto_info = crypto_data.get('data').get('holdings', [])
    except Exception as e:
        logger.error(f"Error getting crypto data: {str(e)}  details={stocks_data,crypto_data}")
        crypto_info = [f"{str(e)}"]
    
    # Prepare combined portfolio data
    portfolio_data = {
        "stocks": stocks_info,
        "crypto": crypto_info,
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_stocks": len(stocks_info),
            "total_crypto": len(crypto_info)
        }
    }
    
    print("*******************", "portfolio data", portfolio_data)
    # Calculate totals
    total_stock_value = sum(float(stock.get('currentValue', 0)) for stock in stocks_info)
    total_crypto_value = sum(float(crypto.get('currentValue', 0)) for crypto in crypto_info)
    total_portfolio_value = total_stock_value + total_crypto_value
    
    portfolio_data["summary"]["total_stock_value"] = total_stock_value
    portfolio_data["summary"]["total_crypto_value"] = total_crypto_value
    portfolio_data["summary"]["total_portfolio_value"] = total_portfolio_value
    
    if total_portfolio_value > 0:
        portfolio_data["summary"]["stock_percentage"] = (total_stock_value / total_portfolio_value) * 100
        portfolio_data["summary"]["crypto_percentage"] = (total_crypto_value / total_portfolio_value) * 100
    
    return portfolio_data