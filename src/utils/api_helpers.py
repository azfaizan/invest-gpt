import os,json,datetime
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials
from src.utils.logger_factory import LoggerFactory
from langchain_openai import ChatOpenAI
from src.tools import financial_api
from src.statics import MODEL_NAME, STATICS


logger = LoggerFactory.create_protocol_logger(service_name="invest-gpt", is_console_command=True)
logger.notice("Application starting up, Protocol Logger initialized")

security = HTTPBearer(
    scheme_name="BearerAuth",
    description="Enter your API key as a Bearer token"
)

plot_cache = {}

def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)):
    """
    Verify the API key from the Authorization header.
    Expected format: Bearer <api_key>
    """
    # Get the expected API key from environment variables
    expected_api_key = os.getenv("API_KEY")
    
    if not expected_api_key:
        logger.critical("API_KEY environment variable not set")
        raise HTTPException(
            status_code=500,
            detail="Server configuration error"
        )
    
    # Extract the token from credentials
    provided_key = credentials.credentials
    
    # Verify the API key
    if provided_key != expected_api_key:
        logger.warning(
            f"Invalid API key attempt",
            context={"provided_key_prefix": provided_key[:8] + "..." if len(provided_key) > 8 else provided_key}
        )
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    
    logger.info("API key validated successfully")
    return True


async def is_trading_related_query(query: str) -> bool:

    try:
        # Create a lightweight LLM instance for classification
        classifier_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        
        classification_prompt = f"""You are a query classifier for InvestmentMarket.ae, the premier investment and trading platform in the UAE. Your job is to determine if a user query should be handled by our trading assistant.

Respond with ONLY "YES" if the query is about:
- Trading, stocks, shares, investments, financial markets
- Cryptocurrency, Bitcoin, Ethereum, digital assets
- Portfolio management, financial planning, wealth management
- Market analysis, economic trends, financial news
- Financial data, charts, visualizations, technical analysis
- Banking, finance, money management, budgeting
- Any financial instruments (bonds, ETFs, options, futures, etc.)
- Support questions for InvestmentMarket.ae platform
- Requests to talk to a person, human agent, customer service, or support team
- Questions about account management, platform features, or services
- Basic greetings like "Hi", "Hello", "How are you" (these should be welcomed)
- General questions about what the assistant can do or help with
- Questions about InvestmentMarket.ae company, services, or platform

Respond with ONLY "NO" if the query is clearly about:
- Weather, cooking, entertainment, sports (unrelated to finance)
- Personal relationships, dating advice
- Medical advice, health issues
- Travel planning (unless related to financial planning)
- Academic subjects unrelated to finance (like history, literature)
- Technical support for non-financial software/hardware
- Any topic completely unrelated to finance, trading, or business

IMPORTANT: When in doubt, respond with "YES" - it's better to be helpful than to reject a potentially relevant query.

User query: "{query}"

Response (YES or NO):"""

        response = classifier_llm.invoke([{"role": "user", "content": classification_prompt}])
        
        # Extract the response and check if it's YES
        result = response.content.strip().upper()
        return result == "YES"
        
    except Exception as e:
        # If classification fails, default to allowing the query (fail-safe)
        logger.error(f"Error in query classification: {str(e)}", exception=e)
        return True



async def clean_external_references(text: str) -> str:
    """
    Use GPT-4o-mini to clean external links, URLs, domains, and source references 
    from text while preserving the core message and support@investmentmarket.ae
    """
    if not text or not isinstance(text, str):
        return text
    
    try:
        from langchain_openai import ChatOpenAI
        
        # Create a lightweight LLM instance for text cleaning
        cleaner_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        
        cleaning_prompt = f"""You are a text cleaner for InvestmentMarket.ae. Your job is to remove ALL external website references, URLs, domains, and source attributions from the given text while preserving the core message and meaning.

REMOVE:
- All URLs (http, https, www, etc.)
- All domain names and website references (bloomberg.com, reuters.net, yahoo.finance, etc.)
- All source attributions ("According to...", "Source:", "Based on...", "From...", etc.)
- All email addresses EXCEPT support@investmentmarket.ae
- All bracketed references [source.something]
- All parenthetical website references (website.com)
- All file references (.pdf, .html, etc.)
- Any mention of external websites or platforms

PRESERVE:
- The core message and information
- support@investmentmarket.ae (this should NEVER be removed)
- Natural flow and readability
- Proper punctuation and grammar

INSTRUCTIONS:
- Do NOT rewrite or change the meaning of the text
- Simply remove the external references cleanly
- Ensure the text flows naturally after removal
- Keep all financial information and advice intact
- Return ONLY the cleaned text, no explanations

Text to clean:
"{text}"

Cleaned text:"""

        response = cleaner_llm.invoke([{"role": "user", "content": cleaning_prompt}])
        return response.content
        
    except Exception as e:
        # If cleaning fails, return original text to avoid breaking the response
        logger.error(f"Error in external reference cleaning: {str(e)}", exception=e)
        return text


async def initialize_chat_model():
    llm = ChatOpenAI(model=MODEL_NAME, temperature=0)

    web_search_tool = {"type": "web_search_preview"}
    portfolio_tool = {
            "type": "function",
            "function": {
                "name": "portfolio_get_data",
                "description": "Get the user's portfolio data including stocks and cryptocurrency holdings",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        }
    create_plot_tool = {
            "type": "function",
            "function": {
                "name": "create_plot",
                "description": "Creates a single visualization (pie, bar, scatter, line, histogram) with customizable options."}}
        
    create_subplots_tool = {
            "type": "function",
            "function": {
                "name": "create_subplots",
                "description": "Creates multiple visualizations in a single figure for comparison or multi-view analysis"}}

    llm_with_tools = llm.bind_tools([web_search_tool, portfolio_tool, create_plot_tool, create_subplots_tool])
    return llm_with_tools
