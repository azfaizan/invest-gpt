from langchain.tools import BaseTool
from typing import  List, Type, ClassVar
from pydantic import BaseModel, Field
from src.tools.financial_api import (
    web_search,
    cryptocurrency_historical_quotes,
    portfolio,
    manipulate_dataset,
    create_pie_chart,
    create_line_chart,
    create_bar_chart,
    create_histogram,
    create_scatter_plot,
    create_portfolio_visualization,
    search_coins
)
from src.statics import STATICS
from datetime import datetime
import json

class WebSearchInput(BaseModel):
    query: str = Field(..., description="The search query to look up")

class ManipulateDatasetInput(BaseModel):
    operation: str = Field(..., description="Operation to perform on the dataset")
    columns: List[str] = Field(..., description="List of columns to operate on")

class PieChartInput(BaseModel):
    labels_col: str = Field(..., description="Column name for labels")
    values_col: str = Field(..., description="Column name for values")
    title: str = Field("Portfolio Distribution", description="Chart title")

class LineChartInput(BaseModel):
    x_col: str = Field(..., description="Column name for x-axis")
    y_cols: List[str] = Field(..., description="List of column names for y-axis")
    title: str = Field("Price Trend", description="Chart title")

class BarChartInput(BaseModel):
    x_col: str = Field(..., description="Column name for x-axis")
    y_col: str = Field(..., description="Column name for y-axis")
    title: str = Field("Bar Chart", description="Chart title")

class HistogramInput(BaseModel):
    column: str = Field(..., description="Column name for the histogram")
    title: str = Field("Distribution", description="Chart title")

class ScatterPlotInput(BaseModel):
    x_col: str = Field(..., description="Column name for x-axis")
    y_col: str = Field(..., description="Column name for y-axis")
    color_col: str = Field(None, description="Column name for color coding (optional)")
    title: str = Field("Scatter Plot", description="Chart title")

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
            print(f"DEBUG - WebSearchTool._run called with query: '{query}'")
            result = web_search(query=query)
            print(f"DEBUG - WebSearchTool._run result type: {type(result)}")
            print(f"DEBUG - WebSearchTool._run result (first 100 chars): {result[:100] if isinstance(result, str) else result}")
          
            return result
            
        except Exception as e:
            print(f"DEBUG - WebSearchTool._run error: {str(e)}")
            return str(e)
    
    def _arun(self, query: str) -> str:
        """Async version of _run"""
        return self._run(query)

class PortfolioTool(BaseTool):
    name: ClassVar[str] = "portfolio"
    description: ClassVar[str] = STATICS["portfolio"]
    
    def _run(self, _: str = "") -> dict:
        """Execute with no specific input required"""
        return portfolio()

class CryptoHistoricalQuotesInput(BaseModel):
    id_list: str = Field(
        ...,
        description="Comma-separated list of CoinMarketCap cryptocurrency IDs (e.g., '1' for Bitcoin, '1027' for Ethereum). "
        "If you don't know the ID, you can search for it using the cryptocurrency name or symbol. "
        "Example: For Bitcoin use '1', for Ethereum use '1027'."
    )
    time_start: str = Field(..., description="Start time in ISO 8601 format (e.g., '2024-01-01')")
    time_end: str = Field(..., description="End time in ISO 8601 format (e.g., '2024-02-01')")
    count: int = Field(30, description="Number of data points to return")
    interval: str = Field("daily", description="Time interval between data points ('daily', 'hourly', etc)")
    attributes: List[str] = Field(
        ["price", "market_cap"],
        description="List of attributes to extract (e.g., ['price', 'market_cap'])"
    )
    convert: str = Field("USD", description="Currency to convert quotes to")

class CryptoHistoricalQuotesTool(BaseTool):
    name: ClassVar[str] = "get_crypto_historical_quotes"
    description: ClassVar[str] = (
        "Get historical price quotes for cryptocurrencies. "
        "You MUST provide CoinMarketCap IDs (not symbols). "
        "Common IDs: Bitcoin (1), Ethereum (1027), BNB (1839), Solana (5426), Cardano (2010), FLOKI (8916). "
        "If you don't know the ID, first search for it using the cryptocurrency name or symbol. "
        "Example: For Bitcoin use '1', for Ethereum use '1027'. "
        "Returns historical price data and stores it in a DataFrame for further analysis."
    )
    args_schema: Type[BaseModel] = CryptoHistoricalQuotesInput

    def _run(
        self,
        id_list: str,
        time_start: str,
        time_end: str,
        count: int = 30,
        interval: str = "daily",
        attributes: List[str] = ["price", "market_cap"],
        convert: str = "USD"
    ) -> str:
        """Get historical cryptocurrency quotes"""
        try:
            # If id_list contains non-numeric characters, try to search for the IDs
            if not all(c.isdigit() or c == ',' for c in id_list):
                # Split by comma and search for each term
                search_terms = [term.strip() for term in id_list.split(',')]
                id_results = []
                
                for term in search_terms:
                    matches = search_coins(term)
                    if matches:
                        # Extract the ID from the first match
                        crypto_id = matches[0][0].split(',')[0]
                        id_results.append(crypto_id)
                
                if id_results:
                    id_list = ','.join(id_results)
                else:
                    return "{error:Could not find CoinMarketCap IDs for the provided cryptocurrencies}"

            return cryptocurrency_historical_quotes(
                id_list=id_list,
                time_start=time_start,
                time_end=time_end,
                count=count,
                interval=interval,
                attributes=attributes,
                convert=convert
            )
        except Exception as e:
            return f"{{error:Error processing request: {str(e)}}}"

class GetCurrentDateTool(BaseTool):
    name: ClassVar[str] = "get_current_date"
    description: ClassVar[str] = """
    Description: Gets the current date in ISO 8601 format.
    Returns: Current date and time in ISO 8601 format.
    """
    
    def _run(self, _: str = "") -> str:
        """Get the current date in ISO 8601 format"""
        return f"Today's date is: {datetime.today().date()}"

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

class PieChartTool(BaseTool):
    name: ClassVar[str] = "create_pie_chart"
    description: ClassVar[str] = "Create a pie chart from DataFrame columns"
    args_schema: Type[BaseModel] = PieChartInput
    
    def _run(self, labels_col: str, values_col: str, title: str = "Portfolio Distribution") -> str:
        """Create a pie chart"""
        return create_pie_chart(labels_col, values_col, title)

class LineChartTool(BaseTool):
    name: ClassVar[str] = "create_line_chart"
    description: ClassVar[str] = "Create a line chart from DataFrame columns"
    args_schema: Type[BaseModel] = LineChartInput
    
    def _run(self, x_col: str, y_cols: List[str], title: str = "Price Trend") -> str:
        """Create a line chart"""
        return create_line_chart(x_col, y_cols, title)

class BarChartTool(BaseTool):
    name: ClassVar[str] = "create_bar_chart"
    description: ClassVar[str] = "Create a bar chart from DataFrame columns"
    args_schema: Type[BaseModel] = BarChartInput
    
    def _run(self, x_col: str, y_col: str, title: str = "Bar Chart") -> str:
        """Create a bar chart"""
        return create_bar_chart(x_col, y_col, title)

class HistogramTool(BaseTool):
    name: ClassVar[str] = "create_histogram"
    description: ClassVar[str] = "Create a histogram from DataFrame column"
    args_schema: Type[BaseModel] = HistogramInput
    
    def _run(self, column: str, title: str = "Distribution") -> str:
        """Create a histogram"""
        return create_histogram(column, title)

class ScatterPlotTool(BaseTool):
    name: ClassVar[str] = "create_scatter_plot"
    description: ClassVar[str] = "Create a scatter plot from DataFrame columns"
    args_schema: Type[BaseModel] = ScatterPlotInput
    
    def _run(self, x_col: str, y_col: str, color_col: str = None, title: str = "Scatter Plot") -> str:
        """Create a scatter plot"""
        return create_scatter_plot(x_col, y_col, color_col, title)

class PortfolioVisualizationTool(BaseTool):
    name: ClassVar[str] = "create_portfolio_visualization"
    description: ClassVar[str] = (
        "Create a comprehensive portfolio visualization showing asset distribution and profit/loss analysis. "
        "This will generate two charts: "
        "1. A pie chart showing the distribution of assets in your portfolio "
        "2. A bar chart showing profit/loss for each asset"
    )
    
    def _run(self, _: str = "") -> str:
        """Create portfolio visualization"""
        result = create_portfolio_visualization()
        if "error" in result:
            return json.dumps({"status": "error", "message": result})
        return json.dumps({
            "status": "success",
            "message": "Portfolio visualization has been created successfully. The plot shows your asset distribution and profit/loss analysis.",
            "details": "The visualization includes a pie chart of your portfolio distribution and a bar chart showing profit/loss by asset."
        })
            