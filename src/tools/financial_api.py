import http.client
import os,json,http,logging
from dotenv import load_dotenv
from tavily import TavilyClient
from fuzzywuzzy import fuzz
from src.statics import WEBSEARCH_MODEL,CRYPTO_LIST, EXCHANGE_LIST, LAST_REFRESH, CACHE_DURATION, COIN_MARKET_CAP_API_BASE_URL ,INVESTMENT_MARKET_API_BASE_URL,historical_quotes_df
import time,sys,pandas as pd , numpy as np
import plotly.graph_objects as go
import plotly.colors as pc
from plotly.subplots import make_subplots
import pandas as pd
import re
from langchain_openai import ChatOpenAI
#from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


plot, historical_quotes_df = None, None


# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

tavily_client= None

# Initialize Tavily client
try:
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
    tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
except Exception as e:
    logger.error(f"Failed to initialize Tavily client: {str(e)}")
    tavily_client = None

def handle_request_error(func):
    """Decorator to handle common API request errors"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (http.client.HTTPException, ConnectionError) as e:
            logger.error(f"HTTP connection error in {func.__name__}: {str(e)}")
            return {"status": 1, "error": f"Connection error: {str(e)}"}
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in {func.__name__}: {str(e)}")
            return {"status": 1, "error": f"Invalid response format: {str(e)}"}
        except KeyError as e:
            logger.error(f"Key error in {func.__name__}: {str(e)}")
            return {"status": 1, "error": f"Data structure error: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
            return {"status": 1, "error": f"Unexpected error: {str(e)}"}
    return wrapper

@handle_request_error
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
    return data_r['data']['accessToken']

try:
    barear = f"Bearer {get_new_token()}"
except Exception as e:
    logger.error(f"Failed to set bearer token: {str(e)}")
    barear = None

payload = ''

@handle_request_error
def web_search(query):
    """
    Search the web for real-time information using OpenAI's Chat API.
    
    Args:
        query (str): The search query about information
    
    Returns:
        str: A concise and accurate response based on the search results
    """
    if not query:
        return "No search query provided"
    
    try:
        print(f"DEBUG - web_search called with query: '{query}'")
        
        if not os.getenv("OPENAI_API_KEY"):
            return "OpenAI API key not found"
            
        llm = ChatOpenAI(
            model=WEBSEARCH_MODEL,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Simple LLM call with the query
        result = llm.invoke(f"Answer the following question: {query}")
        
        print(f"DEBUG - web_search result: {result}")

        return result.content
        
    except Exception as e:
        error_msg = f"Error in web search: {str(e)}"
        print(f"DEBUG - {error_msg}")
        logger.error(error_msg)
        return error_msg

@handle_request_error
def stats_bond_meta(slug):
    """Get detailed metadata for a cryptocurrency by its slug"""
    CMC_API_KEY = os.getenv("CMC_PRO_API_KEY")
    conn = http.client.HTTPSConnection(COIN_MARKET_CAP_API_BASE_URL)
    headers = {
      'X-CMC_PRO_API_KEY': CMC_API_KEY,
      'Accept': '*/*'
    }
    conn.request("GET", f"/v2/cryptocurrency/info?slug={slug}", payload, headers)
    res = conn.getresponse()
    data = res.read()
    crypto_data = json.loads(data.decode("utf-8"))['data']
    
    if not crypto_data:
        logger.warning(f"No data found for slug: {slug}")
        return {"status": 1, "error": "No cryptocurrency data found"}
        
    first_node = list(crypto_data.keys())[0]
    crypto_id = crypto_data[first_node].get("id")
    price_stats = {}
    
    if crypto_id:
        try:
            price_stats = cryptocurrency_price_performance_stats(crypto_id)
        except Exception as e:
            logger.error(f"Error getting price stats for {crypto_id}: {str(e)}")
            price_stats = {"error": str(e)}
    
    return {
        "status": 0,
        "id": crypto_data[first_node].get("id"),
        "name": crypto_data[first_node].get("name"),
        "symbol": crypto_data[first_node].get("symbol"),
        "description": crypto_data[first_node].get("description"),
        "slug": crypto_data[first_node].get("slug"),
        "logo": crypto_data[first_node].get("logo"),
        "urls": crypto_data[first_node].get("urls"),
        "cryptocurrency_price_performance_stats": price_stats
    }

@handle_request_error
def cryptocurrency_meta_info(slug):
    """
    Get cryptocurrency metadata by slug
    
    Args:
        slug (str): Cryptocurrency slug (e.g., 'bitcoin')
    
    Returns:
        dict: Cryptocurrency metadata
    """
    if not slug:
        logger.error("No slug provided for cryptocurrency_meta_info")
        return {"status": 1, "error": "No cryptocurrency slug provided"}
    return stats_bond_meta(slug)

@handle_request_error
def cryptocurrency_price_performance_stats(id):
    """
    Get price performance statistics for a cryptocurrency
    
    Args:
        id (str): Cryptocurrency ID from CoinMarketCap
        
    Returns:
        dict: Price performance statistics
    """
    print("*"*10,id)
    CMC_API_KEY = os.getenv("CMC_PRO_API_KEY")
    conn = http.client.HTTPSConnection(COIN_MARKET_CAP_API_BASE_URL)
    headers = {
        'X-CMC_PRO_API_KEY': CMC_API_KEY,
        'Accept': '*/*'
    }
    conn.request("GET", f"/v2/cryptocurrency/price-performance-stats/latest?id={id}", payload, headers)
    res = conn.getresponse()
    data = res.read()
    print("*"*10,data.decode("utf-8"))
    result = json.loads(data.decode("utf-8"))['data']
    return result

@handle_request_error
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

@handle_request_error
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

def manipulate_dataset(code_string):
    """
    Execute LLM-provided Python code to manipulate the global historical_quotes_df DataFrame
    and return a summary of the modified DataFrame.
    
    Args:
        code_string (str): Python code to execute, manipulating historical_quotes_df.
        
    Returns:
        str: String representation of the custom describe statistics of the modified DataFrame,
             or an error message if execution fails.
    """
    global historical_quotes_df    
    if historical_quotes_df is None:
        return "{error:No DataFrame available}"
    
    if not code_string.strip():
        return "{error:No code provided}"
    
    # Define a restricted namespace for safe execution
    namespace = {
        'historical_quotes_df': historical_quotes_df,
        'pd': pd,
        'np': np
    }
    
    try:
        # Execute the code string
        exec(code_string, namespace)
        
        # Update global DataFrame if modified in namespace
        if 'historical_quotes_df' in namespace:
            historical_quotes_df = namespace['historical_quotes_df']
        
        # Return custom describe of the modified DataFrame
        return historical_quotes_df.describe(include='all').to_string()
        
    except SyntaxError as e:
        logger.error(f"Syntax error in provided code: {str(e)}")
        return f"{{error:Syntax error: {str(e)}}}"
    except Exception as e:
        logger.error(f"Error executing code: {str(e)}")
        return f"{{error:Execution error: {str(e)}}}"

def fetch_coinmarketcap_data():
    """
    Fetch data from CoinMarketCap API for cryptocurrencies and exchanges.
    
    Returns:
        tuple: (crypto_list, exchange_list)
        - crypto_list: List of comma-separated strings (id,name,slug) for cryptocurrencies
        - exchange_list: List of comma-separated strings (id,name,slug) for exchanges
    """
    CMC_API_KEY = os.getenv("CMC_PRO_API_KEY")
    if not CMC_API_KEY:
        logger.error("CMC_PRO_API_KEY environment variable not set")
        return [], []

    base_url = "pro-api.coinmarketcap.com"
    headers = {
        'X-CMC_PRO_API_KEY': CMC_API_KEY,
        'Accept': 'application/json'
    }
    
    # Initialize lists for results
    crypto_list = []
    exchange_list = []
    
    # Endpoints to fetch
    endpoints = [
        "/v1/cryptocurrency/map",
        "/v1/exchange/map"
    ]
    
    conn = http.client.HTTPSConnection(base_url)
    
    try:
        for endpoint in endpoints:
            logger.info(f"Fetching data from {endpoint}")
            conn.request("GET", endpoint, "", headers)
            res = conn.getresponse()
            data = res.read()
            api_data = json.loads(data.decode("utf-8"))
            
            # Check for API errors
            if api_data.get("status", {}).get("error_code", 1) != 0:
                logger.error(f"API error for {endpoint}: {api_data.get('status', {}).get('error_message', 'Unknown error')}")
                continue
                
            # Process data
            if "data" in api_data:
                for item in api_data["data"]:
                    item_id = item.get("id", "")
                    name = item.get("name", "Unknown")
                    slug = item.get("slug", "")
                    if item_id and name and slug:
                        result = f"{item_id},{name},{slug}"
                        if endpoint == "/v1/cryptocurrency/map":
                            crypto_list.append(result)
                        elif endpoint == "/v1/exchange/map":
                            exchange_list.append(result)
            else:
                logger.warning(f"No data found in response for {endpoint}")
                
    except Exception as e:
        logger.error(f"Error fetching data: {str(e)}")
    finally:
        conn.close()
    
    return crypto_list, exchange_list

def get_coinmarketcap_data():
    """
    Get CoinMarketCap data, refreshing only if 24 hours have passed since last refresh.
    
    Returns:
        tuple: (crypto_list, exchange_list)
    """
    global CRYPTO_LIST, EXCHANGE_LIST, LAST_REFRESH
    current_time = time.time()
    
    # Check if cache is valid (less than 24 hours old)
    if CRYPTO_LIST and EXCHANGE_LIST and (current_time - LAST_REFRESH) < CACHE_DURATION:
        logger.info("Using in-memory data")
        return CRYPTO_LIST, EXCHANGE_LIST
    
    # Refresh data from API
    logger.info("Refreshing data from CoinMarketCap API")
    CRYPTO_LIST, EXCHANGE_LIST = fetch_coinmarketcap_data()
    print(f"******X******CRYPTO_LIST: {sys.getsizeof(CRYPTO_LIST)}, EXCHANGE_LIST: {sys.getsizeof(EXCHANGE_LIST)}")
    LAST_REFRESH = time.time()
    return CRYPTO_LIST, EXCHANGE_LIST

def search_assets(query, threshold=70, limit=10):
    """
    Search for cryptocurrencies and exchanges by matching the query against the entire id,name,slug string.
    
    Args:
        query (str): The string to search for (e.g., 'bitcoin', '1,Bitcoin,bitcoin')
        threshold (int, optional): Minimum match score (0-100). Defaults to 70.
        limit (int, optional): Maximum number of results to return. Defaults to 10.
        
    Returns:
        tuple: (crypto_matches, exchange_matches)
        - crypto_matches: List of tuples (asset_string, match_score)
        - exchange_matches: List of tuples (asset_string, match_score)
    """
    if not query:
        logger.error("No query provided for search_assets")
        return [], []
        
    # Get data (from memory or API)
    crypto_list, exchange_list = get_coinmarketcap_data()
    
    # Initialize match lists
    crypto_matches = []
    exchange_matches = []
    
    # Search cryptocurrencies
    for asset in crypto_list:
        score = fuzz.token_set_ratio(query.lower(), asset.lower())
        if score >= threshold:
            crypto_matches.append((asset, score))
    
    # Search exchanges
    for asset in exchange_list:
        score = fuzz.token_set_ratio(query.lower(), asset.lower())
        if score >= threshold:
            exchange_matches.append((asset, score))
    
    # Sort matches by score (descending) and limit results
    crypto_matches.sort(key=lambda x: x[1], reverse=True)
    exchange_matches.sort(key=lambda x: x[1], reverse=True)
    
    return crypto_matches[:limit], exchange_matches[:limit]

def plotting_with_generated_code(code_string):
    """
    Execute user-provided or LLM-generated Plotly code to create a plot from the global historical_quotes_df DataFrame,
    storing the plot's HTML in the global 'plot' variable.
    
    Args:
        code_string (str): Plotly code to execute, creating a figure named 'fig'.
        
    Returns:
        str: "plot is saved in cache" on success, or an error message if execution fails.
    """
    global historical_quotes_df, plot
    #logger = logging.getLogger(__name__)
    print(f"DEBUG - plotting_with_generated_code called with code: {code_string}")
    print(f"DEBUG - historical_quotes_df: {historical_quotes_df}")
    if historical_quotes_df is None:
        #logger.error("No DataFrame available. Run cryptocurrency_historical_quotes first.")
        return "{error:No DataFrame available}"
    
    if not code_string.strip():
        #logger.error("No code provided for plotting")
        return "{error:No code provided}"
    
    # Clean the code - remove any fig.show() or similar display calls
    # This is a safety measure in case the model still adds them despite the rules
    cleaned_code = re.sub(r'fig\.show\(\s*\)', '', code_string)
    cleaned_code = re.sub(r'fig\.write_html\(.*?\)', '', cleaned_code)
    cleaned_code = re.sub(r'fig\.write_image\(.*?\)', '', cleaned_code)
    cleaned_code = re.sub(r'display\(.*?fig.*?\)', '', cleaned_code)
    
    # Check if code was modified
    if cleaned_code != code_string:
        print("WARNING: Removed display/save calls from the code")
    
    # Define a restricted namespace for safe execution
    namespace = {
        'historical_quotes_df': historical_quotes_df,
        'pd': pd,
        'go': go,
        'pc': pc,
        'make_subplots': make_subplots
    }
    
    try:
        # Execute the cleaned code string
        exec(cleaned_code, namespace)
        
        # Check if 'fig' was created
        if 'fig' not in namespace:
        #    logger.error("No Plotly figure named 'fig' was created")
            return "{error:No Plotly figure named 'fig' was created}"
        plot = namespace['fig'].to_html(full_html=False)
        
        return "plot is saved in cache"
        
    except SyntaxError as e:
        #logger.error(f"Syntax error in provided code: {str(e)}")
        return f"{{error:Syntax error: {str(e)}}}"
    except Exception as e:
        #logger.error(f"Error executing Plotly code: {str(e)}")
        return f"{{error:Execution error: {str(e)}}}"

@handle_request_error
def search_coins(query, threshold=70, limit=10):
    """
    Search for cryptocurrencies and stocks by name, symbol, or partial match 
    
    Args:
        query (str): The name or symbol or partial name to search for (e.g., 'bitcoin', 'ethereum', 'apple')
        threshold (int, optional): Minimum match score (0-100). Defaults to 70.
        limit (int, optional): Maximum number of results to return. Defaults to 10.
        
    Returns:
        list: List of tuples containing (coinmarketcap_id, name, slug, match_score)
    """
    if not query:
        logger.error("No query provided for search_coins")
        return []
    crypto_matches, exchange_matches = search_assets(query, threshold=70, limit=5)
    matches = crypto_matches + exchange_matches
    
    return matches