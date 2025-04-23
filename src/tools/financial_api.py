import http.client
import os
import json
import http
import logging
from dotenv import load_dotenv
from tavily import TavilyClient
from fuzzywuzzy import fuzz

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

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
    conn = http.client.HTTPConnection("api-stg-invmkt.agentmarket.ae")
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
    conn = http.client.HTTPSConnection("pro-api.coinmarketcap.com")
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
    conn = http.client.HTTPSConnection("pro-api.coinmarketcap.com")
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

@handle_request_error
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

@handle_request_error
def portfolio_crypto():
    """
    Get user's cryptocurrency portfolio information
    
    Returns:
        dict: Cryptocurrency portfolio data
    """
    if not barear:
        return {"error": "Authentication token is not available"}
        
    conn = http.client.HTTPConnection("api-stg-invmkt.agentmarket.ae")
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
    Get historical price quotes for one or more cryptocurrencies over a specified time period, returning specified attributes as a formatted string.
    
    Args:
        id_list (str): Comma-separated list of cryptocurrency IDs from CoinMarketCap
        time_start (str): Start time in ISO 8601 format (e.g., '2024-04-01')
        time_end (str): End time in ISO 8601 format (e.g., '2025-04-01')
        count (int, optional): Number of data points to return. Defaults to 1.
        interval (str, optional): Time interval between data points ('daily', 'hourly', etc). Defaults to 'daily'.
        attributes (list, optional): List of attributes to extract (e.g., ['price', 'market_cap']). Defaults to ['price', 'market_cap'].
        convert (str, optional): Currency to convert quotes to. Defaults to 'USD'.
        
    Returns:
        str: Formatted string of historical quotes in the format "{datetime,attribute}{datetime:attribute}"
    """
    print(f"DEBUG - cryptocurrency_historical_quotes called with: id_list={id_list}, time_start={time_start}, time_end={time_end}, count={count}, interval={interval}, attributes={attributes}, convert={convert}")
    
    if not id_list:
        logger.error("No cryptocurrency IDs provided for historical quotes")
        return "{error:No cryptocurrency IDs provided}"
        
    CMC_API_KEY = os.getenv("CMC_PRO_API_KEY")
    conn = http.client.HTTPSConnection("pro-api.coinmarketcap.com")
    headers = {
        'X-CMC_PRO_API_KEY': CMC_API_KEY,
        'Accept': '*/*'
    }
    
    # Build the API endpoint with query parameters
    endpoint = f"/v1/cryptocurrency/quotes/historical?id={id_list}&time_start={time_start}&time_end={time_end}&count={count}&interval={interval}&convert={convert}"
    print(f"DEBUG - API endpoint: {endpoint}")
    
    conn.request("GET", endpoint, "", headers)
    res = conn.getresponse()
    data = res.read()
    raw_response = data.decode("utf-8")
    print(f"DEBUG - API raw response: {raw_response[:200]}...")
    
    try:
        result = json.loads(raw_response)
        
        if "data" in result:
            output = []
            for crypto_id, crypto_data in result["data"].items():
                for quote in crypto_data["quotes"]:
                    timestamp = quote["timestamp"]
                    currency_data = quote["quote"][convert]
                    for attr in attributes:
                        if attr in currency_data:
                            output.append(f"{{{timestamp},{attr}:{currency_data[attr]}}}")
            return "".join(output)
        else:
            error_message = result.get("status", {}).get("error_message", "Unknown error")
            logger.error(f"API error in cryptocurrency_historical_quotes: {error_message}")
            return f"{{error:{error_message}}}"
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse API response: {str(e)}")
        return f"{{error:Failed to parse API response: {str(e)}}}"

# Example stock data (to be replaced with real API data in production)
example_stocks = [
    "1 Apple apple",
    "2 Microsoft msft",
    "3 Alphabet googl",
    "4 Amazon amzn",
    "5 Tesla tsla",
    "6 Meta meta",
    "7 Nvidia nvda",
    "8 JPMorgan Chase jpm",
    "9 Visa v",
    "10 Walmart wmt",
    "11 Johnson & Johnson jnj",
    "12 Procter & Gamble pg",
    "13 Mastercard ma",
    "14 UnitedHealth Group unh",
    "15 Exxon Mobil xom",
    "16 Home Depot hd",
    "17 Bank of America bac",
    "18 Chevron cvx",
    "19 Coca-Cola ko",
    "20 Pfizer pfe"
]

@handle_request_error
def search_coins(query, threshold=70, limit=10):
    """
    Search for cryptocurrencies and stocks by name, symbol, or partial match
    
    Args:
        query (str): The name or symbol to search for (e.g., 'bitcoin', 'ethereum', 'apple')
        threshold (int, optional): Minimum match score (0-100). Defaults to 70.
        limit (int, optional): Maximum number of results to return. Defaults to 10.
        
    Returns:
        list: List of tuples containing (asset_info, match_score)
    """
    if not query:
        logger.error("No query provided for search_coins")
        return []
        
    # Try to get cryptocurrency data from CoinMarketCap API
    crypto_data = []
    try:
        CMC_API_KEY = os.getenv("CMC_PRO_API_KEY")
        conn = http.client.HTTPSConnection("pro-api.coinmarketcap.com")
        headers = {
            'X-CMC_PRO_API_KEY': CMC_API_KEY,
            'Accept': '*/*'
        }
        conn.request("GET", "/v1/cryptocurrency/map", "", headers)
        res = conn.getresponse()
        data = res.read()
        api_data = json.loads(data.decode("utf-8"))
        
        if api_data.get("status", {}).get("error_code", 1) == 0 and "data" in api_data:
            for coin in api_data["data"]:
                crypto_data.append(f"{coin.get('rank')} {coin.get('name', 'Unknown')} {coin.get('slug')}")
    except Exception as e:
        logger.error(f"Error fetching cryptocurrency data: {str(e)}")
    
    # Combine with example stocks
    all_assets = crypto_data + example_stocks
    
    # If we couldn't get any data, just use example stocks
    if not all_assets:
        all_assets = example_stocks
        
    # Search for matches using fuzzy matching
    matches = []
    for asset in all_assets:
        name_score = fuzz.token_set_ratio(query.lower(), asset.lower())
        if name_score >= threshold:
            matches.append((asset, name_score))
            if len(matches) >= limit:
                break
    
    # Sort matches by score (descending)
    matches.sort(key=lambda x: x[1], reverse=True)
    
    return matches