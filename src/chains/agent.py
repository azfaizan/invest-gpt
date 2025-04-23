from dotenv import load_dotenv
from langchain.tools import Tool
from src.statics import STATICS
from src.tools import (
    WebSearchTool,
    CryptoMetaInfoTool,
    CryptoPriceStatsTool,
    CryptoHistoricalQuotesTool,
    PortfolioTool,
    CreatePlotTool,
    CreateSubplotsTool,
    GetCurrentDateTool,
    CryptoSearchTool
)
from src.callbacks.llm_logger import LLMLogger

# Load environment variables
load_dotenv()

def create_crypto_agent(model_name="gpt-4o-2024-08-06", verbose=True, **kwargs):
    """
    Create a conversational agent for crypto portfolio management.
    """
    from langchain.agents import initialize_agent, AgentType
    from langchain.memory import ConversationBufferWindowMemory
    from langchain_openai import ChatOpenAI
    
    # Create a callback handler for logging LLM interactions
    llm_logger = LLMLogger()
    
    # Initialize LLM with callbacks
    llm = ChatOpenAI(
        model_name=model_name,
        temperature=0.2,
        streaming=True,
        callbacks=[llm_logger]  # Add our logger to the callbacks
    )

    # Define a function that will handle API failures gracefully
    def safe_crypto_price(id_input):
        """Safe wrapper for the cryptocurrency price stats tool that handles API failures gracefully"""
        try:
            crypto_price_tool = CryptoPriceStatsTool()
            result = crypto_price_tool._run(id_input)
            return result
        except Exception as e:
            # Return a formatted error that suggests alternatives
            return {
                "status": 1,
                "error": str(e),
                "message": "Failed to retrieve cryptocurrency price data. Please try using web_search instead or verify the coin ID is correct."
            }
    
    # Use Tool class to ensure single-input interface
    tools = [
        WebSearchTool(),
        Tool(
            name="cryptocurrency_meta_info",
            func=CryptoMetaInfoTool()._run,
            description=STATICS["cryptocurrency_meta_info"]
        ),
        Tool(
            name="cryptocurrency_price_performance_stats",
            func=CryptoPriceStatsTool()._run,
            description=STATICS["cryptocurrency_price_performance_stats"]
        ),
        # Use the updated CryptoHistoricalQuotesTool which now handles structured inputs correctly
        CryptoHistoricalQuotesTool(),
        Tool(
            name="portfolio",
            func=PortfolioTool()._run,
            description=STATICS["portfolio"]
        ),
        CreatePlotTool(),
        CreateSubplotsTool(),
        Tool(
            name="get_current_date",
            func=GetCurrentDateTool()._run,
            description=GetCurrentDateTool.description
        ),
        Tool(
            name="crypto_search",
            func=CryptoSearchTool()._run,
            description=STATICS["crypto_search"]
        )
    ]
    
    # Set up memory
    memory = ConversationBufferWindowMemory(
        memory_key="chat_history",
        k=5,
        return_messages=True,
    )
    
    # Add system instructions to help the agent understand how to use the tools correctly
    system_message = """
You are a cryptocurrency investment assistant designed to help users manage their portfolios and access comprehensive cryptocurrency information. Your goal is to provide accurate, actionable data by leveraging available tools and APIs, particularly CoinMarketCap APIs, and to visualize results when appropriate, ensuring no blank plots or empty responses.

When users ask about cryptocurrencies, stocks, or other financial assets:

1. Identify the asset by name (e.g., "Bitcoin", "Ethereum", "Apple", "Tesla") and determine its ID or slug as needed.
   - IMPORTANT: When you need to find an asset's ID, ALWAYS use the crypto_search tool first to look up the asset by name or symbol.
   - The search will return the asset's rank/ID, which serves as its identifier in the various APIs.

2. Fetch data using the appropriate tools in the following order of preference:
   - For finding an asset's ID, use the crypto_search tool with the asset name or symbol (works for both cryptocurrencies and stocks).
   - For current price data, use the crypto_price tool with the numeric ID (e.g., "1" for Bitcoin, "1" for Apple).
   - For historical price data or trends, use the crypto_historical tool with the numeric ID.
   - For detailed metadata (e.g., description, tags), use the crypto_meta tool with the asset slug (e.g., "bitcoin", "apple").
   - For portfolio details, use the portfolio tool to fetch holdings, orders, and value.
   - For current date information in ISO 8601 format, use the get_current_date tool.
   - For supplementary or real-time data not available via APIs, use the web_search tool as a fallback.

3. Always attempt to retrieve data from the APIs first. If data is unavailable or insufficient, use web_search to gather additional information.

4. If the user requests a visualization (or it enhances the response), use the create_visualization or create_multi_visualization tools to plot the data (e.g., price trends, portfolio allocation). Ensure plots are meaningful and avoid blank or empty visualizations by validating data availability before plotting.

5. If no data is retrieved, provide a clear explanation and suggest alternative queries or sources.

IMPORTANT: Always format your final response to the user as HTML. Use appropriate HTML elements for structure and styling:
- Use <h1>, <h2>, <h3> tags for headings
- Use <p> tags for paragraphs
- Use <ul> and <li> tags for lists
- Use <table>, <tr>, <th>, and <td> tags for tabular data
- Use <div> tags with inline styles for visual separation
- Use basic styling like colors, padding, and borders to improve readability

Your HTML response should be well-formatted and styled, similar to a simple web page. Include summary information at the top, followed by more detailed data. When including data from tools, embed it directly in your response with appropriate HTML formatting rather than returning raw data.

Always strive to answer the user's question fully, using the retrieved data to provide insights, and include visualizations when relevant to enhance understanding.
"""
    
    # Initialize the agent with system message and callbacks
    agent = initialize_agent(
        tools,
        llm,
        agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
        verbose=verbose,
        memory=memory,
        system_message=system_message,
        callbacks=[llm_logger]  # Add our logger as a callback for the agent
    )
    
    return agent

# Helper function to parse input strings for multi-input tools
def parse_input_string(input_str):
    """Convert a string like 'param1: value1, param2: value2' into a dictionary."""
    params = {}
    parts = [part.strip() for part in input_str.split(',')]
    for part in parts:
        if ':' in part:
            key, value = part.split(':', 1)
            params[key.strip()] = value.strip()
    return params 