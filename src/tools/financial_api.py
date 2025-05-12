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

payload = ''

def get_new_token():
 
    conn = http.client.HTTPConnection(INVESTMENT_MARKET_API_BASE_URL)
    payload = json.dumps({
        "refreshToken": os.getenv("REFRESH_TOKEN"),
        "userName": os.getenv("USER_NAME")
    })
    headers = {
        'Content-Type': 'application/json',
    }
    logger.info(f"Getting new token, payload={payload}, headers={headers}")
    conn.request("POST", "/auth/refresh-token", payload, headers)
    res = conn.getresponse()
    data = res.read()
    data_r = json.loads(data.decode("utf-8"))
    
    # Check if the 'data' key exists in the response
    if 'data' not in data_r:
        logger.error(f"Invalid token response: {json.dumps(data_r)}")
        return json.dumps(data_r)
    
    # Check if the 'accessToken' key exists in the data
    if 'accessToken' not in data_r['data']:
        logger.error(f"No accessToken in response data: {json.dumps(data_r['data'])}")
        return json.dumps(data_r)
    
    return data_r['data']['accessToken']



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

def portfolio_stocks(barear):
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

def portfolio_crypto(barear):
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


def portfolio_json():
    """
    Get user's portfolio information for both stocks and crypto in JSON format.
    
    Returns:
        dict: A JSON-serializable dictionary containing portfolio data
    """
    # Get stocks data
    barear = "Bearer " + get_new_token()
    
    try:
        stocks_data = portfolio_stocks(barear)
        stocks_info = stocks_data.get('data').get('holdings', [])
        crypto_data = portfolio_crypto(barear)
        crypto_info = crypto_data.get('data').get('holdings', [])
    except Exception as e:
        logger.error(f"Error getting crypto data: {str(e)}  details={stocks_data}")
        crypto_info = [f"{str(e)}"]
        return stocks_data
    
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