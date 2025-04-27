from langchain.tools import BaseTool
from typing import Dict, Any, List, Optional, Type, ClassVar
from pydantic import BaseModel, Field
import json
from src.tools.financial_api import (
    web_search,
    cryptocurrency_meta_info,
    cryptocurrency_price_performance_stats,
    cryptocurrency_historical_quotes,
    portfolio,
    search_coins
)
from src.visualization.plot_utils import create_plot, create_subplots
from src.statics import STATICS
from datetime import datetime

class WebSearchInput(BaseModel):
    query: str = Field(..., description="The search query about cryptocurrency information")
    days: int = Field(7, description="Number of days to look back")
    include_domains: Optional[List[str]] = Field(None, description="List of domains to include in search")
    exclude_domains: Optional[List[str]] = Field(None, description="List of domains to exclude from search")

class CryptoMetaInfoInput(BaseModel):
    slug: str = Field(..., description="Cryptocurrency slug (e.g., 'bitcoin')")

class CryptoPriceStatsInput(BaseModel):
    id: str = Field(..., description="Cryptocurrency ID from CoinMarketCap")

class CreatePlotInput(BaseModel):
    data: List[Dict[str, Any]] = Field(..., description="Input data as list of dictionaries")
    plot_type: str = Field("pie", description="Type of plot to create ('pie', 'bar', 'scatter', 'line', 'histogram')")
    title: str = Field("Data Visualization", description="Title of the plot")
    x_column: Optional[str] = Field(None, description="Column name for x-axis (for bar, scatter, line, histogram)")
    y_column: Optional[str] = Field(None, description="Column name for y-axis (for bar, scatter, line)")
    color_column: Optional[str] = Field(None, description="Column name for color grouping")
    size_column: Optional[str] = Field(None, description="Column name for marker size (for scatter)")
    text_column: Optional[str] = Field(None, description="Column name for hover text")
    width: int = Field(800, description="Width of the plot in pixels")
    height: int = Field(600, description="Height of the plot in pixels")

class CreateSubplotsInput(BaseModel):
    data: Dict[int, Dict[str, Dict[str, Any]]] = Field(..., 
        description="Dictionary containing data for plots {subplot_idx: {trace_name: {x: [], y: [], text: []}}}")
    plot_types: List[str] = Field(..., 
        description="List of plot types ('bar', 'pie', 'scatter', etc.) for each subplot")
    rows: int = Field(1, description="Number of rows")
    cols: int = Field(2, description="Number of columns")
    subplot_titles: Optional[List[str]] = Field(None, description="Titles for each subplot")
    title: str = Field("Dynamic Subplots", description="Main figure title")
    height: int = Field(600, description="Figure height")
    width: Optional[int] = Field(None, description="Figure width")
    barmode: str = Field('group', description="'group', 'stack', or 'relative' for bar plots")

class CryptoHistoricalQuotesInput(BaseModel):
    id: str = Field(..., description="Comma-separated list of cryptocurrency IDs from CoinMarketCap (e.g., '1,1027' for Bitcoin and Ethereum)")
    time_start: str = Field(..., description="Start time in ISO 8601 format (e.g., '2024-04-01')")
    time_end: str = Field(..., description="End time in ISO 8601 format (e.g., '2025-04-01')")
    count: int = Field(1, description="Number of data points to return")
    interval: str = Field("daily", description="Time interval between data points ('daily', 'hourly', etc)")

class WebSearchTool(BaseTool):
    name: ClassVar[str] = "web_search"
    description: ClassVar[str] = STATICS["web_search"]
    
    def _run(
        self, 
        query: str = "", 
        days: int = 7,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None
    ) -> dict:
        """
        Execute with either a string input or structured parameters
        
        Args:
            query: The search query
            days: Number of days to look back
            include_domains: List of domains to include in search
            exclude_domains: List of domains to exclude from search
        """
        print(f"DEBUG - WebSearchTool received input: query='{query}', days={days}")
        
        # Handle case where input is just a string (basic query)
        if not include_domains and not exclude_domains and query:
            return web_search(
                query=query,
                days=days,
                include_domains=None,
                exclude_domains=None
            )
            
        # Handle structured input case
        return web_search(
            query=query,
            days=days,
            include_domains=include_domains,
            exclude_domains=exclude_domains
        )

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

class CreatePlotTool(BaseTool):
    name: ClassVar[str] = "create_plot"
    description: ClassVar[str] = STATICS["create_plot"] 
    
    def _run(
        self, 
        input_str: str = "", 
        data: List[Dict[str, Any]] = None,
        plot_type: str = "pie",
        title: str = "Data Visualization",
        x_column: str = None,
        y_column: str = None,
        color_column: str = None,
        size_column: str = None,
        text_column: str = None,
        width: int = 800,
        height: int = 600,
        **kwargs
    ) -> str:
        """
        Execute with either a JSON string input or direct parameters
        
        Args:
            input_str: A JSON string input
            data: List of data points as dictionaries
            plot_type: Type of plot to create
            title: Title of the plot
            x_column: Column name for x-axis
            y_column: Column name for y-axis
            color_column: Column name for color grouping
            size_column: Column name for marker size
            text_column: Column name for hover text
            width: Width of the plot in pixels
            height: Height of the plot in pixels
        """
        print(f"DEBUG - CreatePlotTool received input: '{input_str}'")
        
        # Default parameters
        params = {
            "data": data or [],
            "plot_type": plot_type,
            "title": title,
            "x_column": x_column,
            "y_column": y_column,
            "color_column": color_column,
            "size_column": size_column,
            "text_column": text_column,
            "width": width,
            "height": height
        }
        
        # Update with any additional kwargs
        params.update(kwargs)
        
        if not params["data"]:
            error_message = "No data provided for visualization."
            print(f"DEBUG - Error: {error_message}")
            return f"Error: {error_message}"
        
        print(f"DEBUG - Creating plot with parameters: {params}")
        
        # Extract all parameters for create_plot function
        plot_params = {k: v for k, v in params.items()}
        
        # Create the plot
        fig = create_plot(**plot_params)
        
        # Return HTML representation of the plot
        return fig.to_html(full_html=False, include_plotlyjs='cdn')

class CreateSubplotsTool(BaseTool):
    name: ClassVar[str] = "create_subplots"
    description: ClassVar[str] = STATICS["create_subplots"]
    
    def _run(
        self,
        input_str: str = "",
        data: Dict[int, Dict[str, Dict[str, Any]]] = None,
        plot_types: List[str] = None,
        rows: int = 1,
        cols: int = 2,
        subplot_titles: List[str] = None,
        title: str = "Dynamic Subplots",
        height: int = 600,
        width: int = None,
        barmode: str = "group",
        **kwargs
    ) -> str:
        """
        Execute with either a JSON string input or direct parameters
        
        Args:
            input_str: A JSON string input
            data: Dictionary containing data for plots
            plot_types: List of plot types for each subplot
            rows: Number of rows in subplot grid
            cols: Number of columns in subplot grid
            subplot_titles: Titles for each subplot
            title: Main figure title
            height: Figure height in pixels
            width: Figure width in pixels
            barmode: Mode for bar plots ('group', 'stack', 'relative')
        """
        print(f"DEBUG - CreateSubplotsTool received input: '{input_str}'")
        
        # Default parameters
        params = {
            "data": data or {},
            "plot_types": plot_types or [],
            "rows": rows,
            "cols": cols,
            "subplot_titles": subplot_titles,
            "title": title,
            "height": height,
            "width": width,
            "barmode": barmode
        }
        
        # Update with any additional kwargs
        params.update(kwargs)
        
        print(f"DEBUG - Creating subplots with parameters: {params}")
        
        # Extract all parameters for create_subplots function
        plot_params = {k: v for k, v in params.items()}
        
        # Create the subplots
        fig = create_subplots(**plot_params)
        
        # Return HTML representation of the plot
        return fig.to_html(full_html=False)

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
            