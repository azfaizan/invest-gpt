from langchain.tools import BaseTool
from typing import Dict, Any, List, Optional, Type, ClassVar
from pydantic import BaseModel, Field
from src.tools.financial_api import (
    web_search,
    cryptocurrency_meta_info,
    cryptocurrency_price_performance_stats,
    cryptocurrency_historical_quotes,
    portfolio,
    search_coins,
    manipulate_dataset
)
from src.tools.financial_api import plotting_with_generated_code
from src.statics import STATICS
from datetime import datetime
import json

class WebSearchInput(BaseModel):
    query: str = Field(..., description="The search query about information")

class CryptoMetaInfoInput(BaseModel):
    slug: str = Field(..., description="Cryptocurrency slug (e.g., 'bitcoin')")

class CryptoPriceStatsInput(BaseModel):
    id: str = Field(..., description="Cryptocurrency ID from CoinMarketCap")

class CryptoHistoricalQuotesInput(BaseModel):
    id: str = Field(..., description="Comma-separated list of cryptocurrency IDs from CoinMarketCap (e.g., '1,1027' for Bitcoin and Ethereum)")
    time_start: str = Field(..., description="Start time in ISO 8601 format (e.g., '2024-04-01')")
    time_end: str = Field(..., description="End time in ISO 8601 format (e.g., '2025-04-01')")
    count: int = Field(1, description="Number of data points to return")
    interval: str = Field("daily", description="Time interval between data points ('daily', 'hourly', etc)")

class ManipulateDatasetInput(BaseModel):
    code_string: str = Field(..., description="Python code to manipulate the historical_quotes_df DataFrame")

class PlottingWithGeneratedCodeInput(BaseModel):
    code_string: str = Field(..., description="Plotly Python code to create a visualization")

class WebSearchTool(BaseTool):
    name: ClassVar[str] = "web_search"
    description: ClassVar[str] = STATICS["web_search"]
    args_schema: Type[BaseModel] = WebSearchInput
    
    def _run(
        self, 
        query: str
    ) -> str:
        """
        Execute web search using OpenAI's Chat API
        
        Args:
            query: The search query
        """
        try:
            result = web_search(query=query)
          
            return result
            
        except Exception as e:
           
            return str(e)
    
    def _arun(self, query: str) -> str:
        """Async version of _run"""
        return self._run(query)

class CryptoMetaInfoTool(BaseTool):
    name: ClassVar[str] = "cryptocurrency_meta_info"
    description: ClassVar[str] = STATICS["cryptocurrency_meta_info"]
    
    def _run(self, slug: str) -> dict:
        """Execute with a string input (the cryptocurrency slug)"""
        return cryptocurrency_meta_info(slug=slug)

class CryptoPriceStatsTool(BaseTool):
    name: ClassVar[str] = "cryptocurrency_price_performance_stats"
    description: ClassVar[str] = STATICS["cryptocurrency_price_performance_stats"]
    
    def _run(self, id: str) -> dict:
        """Execute with a string input (the cryptocurrency ID)"""
        return cryptocurrency_price_performance_stats(id=id)

class PortfolioTool(BaseTool):
    name: ClassVar[str] = "portfolio"
    description: ClassVar[str] = STATICS["portfolio"]
    
    def _run(self, _: str = "") -> dict:
        """Execute with no specific input required"""
        return portfolio()

class CryptoHistoricalQuotesTool(BaseTool):
    name: ClassVar[str] = "cryptocurrency_historical_quotes"
    description: ClassVar[str] = STATICS["cryptocurrency_historical_quotes"]
    
    def _run(
        self, 
        input_str: str = "",
        id: str = None,
        time_start: str = "2024-01-01",
        time_end: str = "2025-04-01",
        count: int = 30,
        interval: str = "daily",
        attributes: List[str] = None,
        convert: str = "USD"
    ) -> str:
        """
        Execute with either a string input or direct parameters
        
        Args:
            input_str: A string input (either ID or JSON)
            id: Comma-separated list of cryptocurrency IDs
            time_start: Start time in ISO 8601 format
            time_end: End time in ISO 8601 format
            count: Number of data points to return
            interval: Time interval between data points
            attributes: List of attributes to extract
            convert: Currency to convert quotes to
        """
        print(f"DEBUG - CryptoHistoricalQuotesTool received input: '{input_str}', id={id}, time_start={time_start}, time_end={time_end}, count={count}, interval={interval}")
        
        # Default parameters
        params = {
            "id": id,
            "time_start": time_start,
            "time_end": time_end,
            "count": count,
            "interval": interval,
            "attributes": attributes or ["price", "market_cap"],
            "convert": convert
        }
        

        # Validate that we have the required id parameter
        if not params["id"]:
            error_message = "Could not determine cryptocurrency ID. Please provide a numeric ID (e.g., '1' for Bitcoin) or a valid JSON with 'id'."
            print(f"DEBUG - Error: {error_message}")
            error_html = f"""
            <div style="color: red; padding: 10px; border: 1px solid red; border-radius: 5px;">
                <h3>Missing Required Parameter</h3>
                <p>{error_message}</p>
            </div>
            """
            return error_html
        
        print(f"DEBUG - Final parameters: {params}")
        
        # Call the API function with extracted parameters
        result = cryptocurrency_historical_quotes(
            id_list=params["id"],
            time_start=params["time_start"],
            time_end=params["time_end"],
            count=params["count"],
            interval=params["interval"],
            attributes=params["attributes"],
            convert=params["convert"]
        )
        
        # Check if result is an error
        return result

class GetCurrentDateTool(BaseTool):
    name: ClassVar[str] = "get_current_date"
    description: ClassVar[str] = """
    Description: Gets the current date in ISO 8601 format.
    Returns: Current date and time in ISO 8601 format.
    """
    
    def _run(self, _: str = "") -> str:
        """Get the current date in ISO 8601 format"""
        return f"Today's date is: {datetime.today().date()}"

class CryptoSearchTool(BaseTool):
    name: ClassVar[str] = "crypto_search"
    description: ClassVar[str] = STATICS["crypto_search"]
    
    def _run(self, query: str, threshold: int = 70, limit: int = 10) -> str:
        """Search for cryptocurrencies and stocks by name or symbol"""
        try:
            matches = search_coins(query, threshold, limit)
            return matches
            
        except Exception as e:
            return f"Error searching for assets: {str(e)}"

class ManipulateDatasetTool(BaseTool):
    name: ClassVar[str] = "manipulate_dataset"
    description: ClassVar[str] = STATICS["manipulate_dataset"]
    
    def _run(self, code_string: str) -> str:
        """
        Execute Python code to manipulate the historical_quotes_df DataFrame
        
        Args:
            code_string: Python code to execute on the historical_quotes_df DataFrame
        """
        print(f"DEBUG - ManipulateDatasetTool received code: '{code_string[:100]}...'")
        return manipulate_dataset(code_string)

class PlottingWithGeneratedCodeTool(BaseTool):
    name: ClassVar[str] = "plotting_with_generated_code"
    description: ClassVar[str] = STATICS["plotting_with_generated_code"]
    
    def _run(self, code_string: str) -> str:
        """
        Execute Plotly code to create a visualization
        
        Args:
            code_string: Plotly Python code to create a visualization
        """
        print(f"DEBUG - PlottingWithGeneratedCodeTool received code: '{code_string[:100]}...'")
        result = plotting_with_generated_code(code_string)
        
        if result.startswith("{error:"):
            return result
            
        # Format the response as a valid JSON blob
        response = {
            "action": "Final Answer",
            "action_input": f"The plot has been generated and saved. {result}"
        }
        return json.dumps(response)
    
    def _arun(self, code_string: str) -> str:
        """Async version of _run"""
        return self._run(code_string)
            