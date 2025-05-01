from dotenv import load_dotenv
from langchain.tools import Tool
from src.statics import STATICS
from src.tools import (
    WebSearchTool,
    CryptoHistoricalQuotesTool,
    PortfolioTool,
    GetCurrentDateTool,
    ManipulateDatasetTool,
    PieChartTool,
    LineChartTool,
    BarChartTool,
    HistogramTool,
    ScatterPlotTool,
    PortfolioVisualizationTool
)
from src.callbacks.llm_logger import LLMLogger

# Load environment variables
load_dotenv()

def create_crypto_agent(model_name="gpt-4-0125-preview", verbose=True, **kwargs):
    """
    Create a conversational agent for crypto portfolio management.
    """
    from langchain.agents import initialize_agent, AgentType
    from langchain.memory import ConversationBufferMemory
    from langchain_openai import ChatOpenAI
    from langchain.prompts import MessagesPlaceholder
    import json
 
    llm_logger = LLMLogger()
    
    # Initialize LLM with callbacks
    llm = ChatOpenAI(
        model_name=model_name,
        callbacks=[llm_logger],  # Add our logger to the callbacks
        **kwargs
    )

    # Use Tool class to ensure single-input interface
    tools = [
        WebSearchTool(),
        CryptoHistoricalQuotesTool(),
        PortfolioTool(),
        GetCurrentDateTool(),
        ManipulateDatasetTool(),
        PieChartTool(),
        LineChartTool(),
        BarChartTool(),
        HistogramTool(),
        ScatterPlotTool(),
        PortfolioVisualizationTool()
    ]

    # Create memory with proper configuration
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True
    )

    # Create the agent with custom prompt
    system_message = """You are a cryptocurrency portfolio management assistant. You help users analyze and visualize their portfolio data.

Key Instructions:
1. When users ask to visualize, plot, show, or display their portfolio, ALWAYS use the create_portfolio_visualization tool first. This tool creates a comprehensive view with:
   - A pie chart showing portfolio distribution
   - A bar chart showing profit/loss by asset
   
2. Only use other plotting tools (pie_chart, line_chart, etc.) when users specifically request:
   - A specific type of chart
   - A custom visualization with specific columns
   - Additional analysis beyond the standard portfolio view

3. For historical data queries:
   - Use the get_crypto_historical_quotes tool with proper parameters
   - If you don't know a cryptocurrency's ID, you can use its name or symbol
   - Common IDs: Bitcoin (1), Ethereum (1027), BNB (1839), Solana (5426), Cardano (2010), FLOKI (8916)
   - When a user asks about market data, use this tool to get the information

4. After creating visualizations:
   - Explain what the charts show
   - Highlight key insights
   - Point out notable patterns or trends

5. Conversation Management:
   - ALWAYS maintain context from previous messages
   - When a user confirms something you asked (like correcting a typo), immediately proceed with the confirmed action
   - For market cap or price queries, use get_crypto_historical_quotes with recent dates to get current data
   - If you asked a clarifying question and got a confirmation, execute the intended action right away

Remember: You must maintain conversation context. If you asked about a typo and the user confirmed the correct name, immediately proceed with their original request using the confirmed information."""

    # Initialize the agent with memory configuration
    agent = initialize_agent(
        tools,
        llm,
        agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
        verbose=verbose,
        memory=memory,
        agent_kwargs={
            "system_message": system_message
        },
        handle_parsing_errors=True
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