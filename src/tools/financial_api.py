import http.client
import os,json,http,logging
from dotenv import load_dotenv
from tavily import TavilyClient
from fuzzywuzzy import fuzz
from src.statics import CRYPTO_LIST, EXCHANGE_LIST, LAST_REFRESH, CACHE_DURATION, COIN_MARKET_CAP_API_BASE_URL ,INVESTMENT_MARKET_API_BASE_URL
import time,sys,pandas as pd



# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

tavily_client= None
historical_quotes_df = pd.DataFrame()
plot = None
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
def web_search(query, days=7, include_domains=None, exclude_domains=None):
    """
    Search the web for real-time cryptocurrency information using Tavily API.
    
    Args:
        query (str): The search query about cryptocurrency information
        days (int, optional): Number of days to look back. Defaults to 7.
        include_domains (list, optional): List of domains to include in search. 
        exclude_domains (list, optional): List of domains to exclude from search.
    
    Returns:
        dict: Search results and information from the web
    """
    global tavily_client
    if not tavily_client:
        return {"status": 1, "error": "Tavily client is not initialized"}
    
    if not query:
        return {"status": 1, "error": "No search query provided"}
    
    # Set default domains if not provided
    if not include_domains:
        include_domains = ["https://coinmarketcap.com/currencies/*/historical-data/"]
    
    try:
        response = tavily_client.search(
            query=query,
            search_depth="advanced",
            max_results=4,
            include_answer=True,
            include_raw_data=True,
            include_images=True,
            include_domains=include_domains,
            exclude_domains=exclude_domains or []
        )
        
        return {
            "status": 0,
            "results": response,
            "query": query
        }
    except Exception as e:
        logger.error(f"Error in web search: {str(e)}")
        return {"status": 1, "error": f"Web search failed: {str(e)}"}

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
    Get user's portfolio information for both stocks and crypto
    
    Returns:
        dict: Portfolio information for stocks and crypto
    """
    information_set = {"stocks": None, "crypto": None}
    
    # Get stocks data
    try:
        stocks_data = portfolio_stocks()
        information_set["stocks"] = stocks_data
    except Exception as e:
        logger.error(f"Error fetching portfolio stocks: {str(e)}")
        information_set["stocks"] = {"error": str(e)}
    
    # Get crypto data
    try:
        crypto_data = portfolio_crypto()
        information_set["crypto"] = crypto_data
    except Exception as e:
        logger.error(f"Error fetching portfolio crypto: {str(e)}")
        information_set["crypto"] = {"error": str(e)}
    
    return information_set

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
    storing data in a DataFrame and returning summarized statistics of specified attributes.
    
    Args:
        id_list (str): Comma-separated list of cryptocurrency IDs from CoinMarketCap
        time_start (str): Start time in ISO 8601 format (e.g., '2024-04-01')
        time_end (str): End time in ISO 8601 format (e.g., '2025-04-01')
        count (int, optional): Number of data points to return. Defaults to 1.
        interval (str, optional): Time interval between data points ('daily', 'hourly', etc). Defaults to 'daily'.
        attributes (list, optional): List of attributes to extract (e.g., ['price', 'market_cap']). Defaults to ['price', 'market_cap'].
        convert (str, optional): Currency to convert quotes to. Defaults to 'USD'.
        
    Returns:
        dict: Summary statistics of historical data and plotting information
    """
    print(f"DEBUG - cryptocurrency_historical_quotes called with: id_list={id_list}, time_start={time_start}, time_end={time_end}, count={count}, interval={interval}, attributes={attributes}, convert={convert}")
    
    if not id_list:
        logger.error("No cryptocurrency IDs provided for historical quotes")
        return "{error:No cryptocurrency IDs provided}"
        
    CMC_API_KEY = os.getenv("CMC_PRO_API_KEY")
    if not CMC_API_KEY:
        logger.error("CMC API key not found")
        return "{error:CMC API key not found}"
    
    conn = http.client.HTTPSConnection(COIN_MARKET_CAP_API_BASE_URL)
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
        print(f"DEBUG - API raw response: {raw_response[:200]}...")
        
        result = json.loads(raw_response)
        
        if "data" not in result:
            error_message = result.get("status", {}).get("error_message", "Unknown error")
            logger.error(f"API error in cryptocurrency_historical_quotes: {error_message}")
            return f"{{error:{error_message}}}"
        
        output = []
        data = result["data"]
        
        # Handle response1 (multiple IDs) or response2 (single ID)
        if isinstance(data, dict) and all(k.isdigit() for k in data.keys()):  # response1: {"1": {"quotes": [...]}, ...}
            for crypto_id, crypto_info in data.items():
                for crypto_data in crypto_info.get("quotes", []):
                    timestamp = crypto_data["timestamp"]
                    currency_data = crypto_data["quote"].get(convert, {})
                    for attr in attributes:
                        if attr in currency_data:
                            output.append(f"{{{timestamp},{crypto_id},{attr}:{currency_data[attr]}}}")
        else:  # response2: {"quotes": [...]}
            # Assume single ID from id_list (first ID)
            single_id = id_list.split(",")[0] if "," in id_list else id_list
            for crypto_data in data.get("quotes", []):
                timestamp = crypto_data["timestamp"]
                currency_data = crypto_data["quote"].get(convert, {})
                for attr in attributes:
                    if attr in currency_data:
                        output.append(f"{{{timestamp},{single_id},{attr}:{currency_data[attr]}}}")
        
        return "".join(output) if output else "{error:No valid data found}"
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse API response: {str(e)}")
        return f"{{error:Failed to parse API response: {str(e)}}}"
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return f"{{error:Unexpected error: {str(e)}}}"
    finally:
        conn.close()

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