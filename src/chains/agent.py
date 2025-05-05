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


    # Initialize the agent with memory configuration
    agent = initialize_agent(
        tools,
        llm,
        agent=AgentType.OPENAI_FUNCTIONS,
        verbose=verbose,
        memory=memory
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