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
    from langchain_core.messages import AIMessage
    
    # Custom memory class that can handle non-string outputs
    #class SafeConversationMemory(ConversationBufferWindowMemory):
    #    def save_context(self, inputs, outputs):
    #        """Override save_context to ensure outputs are strings"""
    #        # Convert any non-string outputs to string
    #        if isinstance(outputs, dict) and "output" in outputs:
    #            if not isinstance(outputs["output"], str):
    #                outputs["output"] = str(outputs["output"])
            
            # Call the parent implementation
    #        super().save_context(inputs, outputs)
    
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
        PortfolioTool(),
        CreatePlotTool(),
        CreateSubplotsTool(),
        GetCurrentDateTool(),
        CryptoSearchTool()
    ]
    
    # Set up memory with the safer implementation
    memory = ConversationBufferWindowMemory(
        memory_key="chat_history",
        k=5,
        return_messages=True,
    )
    
   
    
    # Initialize the agent with system message and callbacks
    agent = initialize_agent(
        tools,
        llm,
        agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
        verbose=verbose,
        memory=memory,
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