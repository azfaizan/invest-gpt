import http.client,os,json,http,logging
from dotenv import load_dotenv
from src.statics import INVESTMENT_MARKET_API_BASE_URL
import plotly.graph_objects as go, plotly.colors as pc
from plotly.subplots import make_subplots
from datetime import datetime
from src.utils.logger_factory import LoggerFactory
from typing import Dict, Any, List, Optional, Tuple, Union


# Load environment variables
load_dotenv()
logger = LoggerFactory.create_logger(service_name="invest-gpt")
logger.notice("Application starting up, Logger initialized")

payload = ''

class AuthenticationError(Exception):
    """Exception raised for authentication issues."""
    pass


def get_new_token() -> str:
    """
    Get a new authentication token using refresh token.
    
    Returns:
        str: New access token
        
    Raises:
        AuthenticationError: If token retrieval fails
    """
    try:
        conn = http.client.HTTPConnection(INVESTMENT_MARKET_API_BASE_URL)
        payload = json.dumps({
            "refreshToken": os.getenv("REFRESH_TOKEN"),
            "userName": os.getenv("USER_NAME")
        })
        headers = {
            'Content-Type': 'application/json',
        }
        logger.info(f"Getting new token", context={"payload_length": len(payload)})
        
        conn.request("POST", "/auth/refresh-token", payload, headers)
        res = conn.getresponse()
        data = res.read()
        data_r = json.loads(data.decode("utf-8"))
        
        # Check if the 'data' key exists in the response
        if 'data' not in data_r:
            logger.error(f"Invalid token response", context={"response": data_r})
            raise AuthenticationError("Invalid token response format")
        
        # Check if the 'accessToken' key exists in the data
        if 'accessToken' not in data_r['data']:
            logger.error(f"No accessToken in response data", context={"data": data_r['data']})
            raise AuthenticationError("No access token in response")
        
        return data_r['data']['accessToken']
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in token response", context={"error": str(e)})
        raise AuthenticationError(f"Failed to parse token response: {str(e)}")
    except Exception as e:
        logger.error(f"Error getting new token", context={"error": str(e)})
        raise AuthenticationError(f"Failed to get authentication token: {str(e)}")


def make_authenticated_request(endpoint: str, method: str = "GET", payload: str = '') -> Dict[str, Any]:
    """
    Make an authenticated request to the investment market API.
    
    Args:
        endpoint: API endpoint path
        method: HTTP method (GET, POST, etc.)
        payload: Request payload for POST requests
        
    Returns:
        dict: Response data as dictionary
        
    Raises:
        AuthenticationError: If authentication fails
        ConnectionError: If connection fails
        ValueError: If response parsing fails
    """
    try:
        token = get_new_token()
        bearer = f"Bearer {token}"
        
        conn = http.client.HTTPConnection(INVESTMENT_MARKET_API_BASE_URL)
        headers = {
            'Authorization': bearer,
        }
        
        conn.request(method, endpoint, payload, headers)
        res = conn.getresponse()
        data = res.read()
        
        try:
            return json.loads(data.decode("utf-8"))
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse API response", context={"error": str(e)})
            raise ValueError(f"Invalid JSON response: {str(e)}")
            
    except AuthenticationError:
        # Re-raise authentication errors
        raise
    except Exception as e:
        logger.error(f"API request failed", context={"endpoint": endpoint, "error": str(e)})
        raise ConnectionError(f"Failed to connect to API: {str(e)}")


def portfolio_stocks() -> Dict[str, Any]:
    """
    Get user's stock portfolio information
    
    Returns:
        dict: Stock portfolio data
        
    Raises:
        AuthenticationError: If authentication fails
        ConnectionError: If API request fails
    """
    try:
        return make_authenticated_request("/api-gateway/portfolio/stocks")
    except (AuthenticationError, ConnectionError) as e:
        logger.error(f"Failed to get stock portfolio", context={"error": str(e)})
        return {"error": str(e)}


def portfolio_crypto() -> Dict[str, Any]:
    """
    Get user's cryptocurrency portfolio information
    
    Returns:
        dict: Cryptocurrency portfolio data
        
    Raises:
        AuthenticationError: If authentication fails
        ConnectionError: If API request fails
    """
    try:
        return make_authenticated_request("/api-gateway/portfolio/crypto")
    except (AuthenticationError, ConnectionError) as e:
        logger.error(f"Failed to get crypto portfolio", context={"error": str(e)})
        return {"error": str(e)}

class PlotHelper:
    """Helper class for common plotting operations"""
    
    @staticmethod
    def get_default_colors(num_colors: int = 10) -> List[str]:
        """Get a list of default colors for plots"""
        if num_colors <= 10:
            return pc.qualitative.Plotly
        else:
            return pc.qualitative.Dark24
            
    @staticmethod
    def create_figure_layout(
        title: str, 
        width: int, 
        height: int, 
        show_legend: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """Create a standard figure layout with common parameters"""
        layout = {
            'title': title,
            'width': width,
            'height': height,
            'showlegend': show_legend,
            'margin': dict(t=50, b=50, l=50, r=50),
            'autosize':True
        }
        
        # Add any additional layout parameters
        if kwargs:
            layout.update(kwargs)
            
        return layout


def create_subplots(
    data: Dict[Union[int, str], Dict[str, Dict[str, Any]]],
    plot_types: List[str],
    rows: int = 1,
    cols: int = 2,
    subplot_titles: Optional[List[str]] = None,
    column_widths: Optional[List[float]] = None,
    title: str = "Dynamic Subplots",
    height: int = 600,
    width: Optional[int] = None,
    barmode: str = 'group',
    colors: Optional[List[str]] = None,
    show_legend: bool = True,
    annotations: Optional[List[Dict[str, Any]]] = None,
    layout_custom: Optional[Dict[str, Any]] = None
) -> go.Figure:
    """
    Create dynamic subplots with customizable parameters.
    
    Args:
        data: Dictionary containing data for plots {subplot_idx: {trace_name: {x: [], y: [], text: []}}}
        plot_types: List of plot types ('bar', 'pie', 'scatter', etc.) for each subplot
        rows: Number of rows
        cols: Number of columns
        subplot_titles: Titles for each subplot
        column_widths: List of relative widths for columns
        title: Main figure title
        height: Figure height
        width: Figure width
        barmode: 'group', 'stack', or 'relative' for bar plots
        colors: List of colors for traces
        show_legend: Boolean to show/hide legend
        annotations: List of annotation dictionaries
        layout_custom: Dictionary of additional layout parameters
        
    Returns:
        Plotly figure object with subplots
    """
    print(f"🔍 create_subplots called with:")
    print(f"   data: {data}")
    print(f"   data type: {type(data)}")
    print(f"   data keys: {list(data.keys()) if data else None}")
    print(f"   plot_types: {plot_types}")
    print(f"   title: {title}")
    
    # Handle empty data case
    if not data:
        print("❌ Empty data provided, creating empty figure")
        fig = go.Figure()
        fig.update_layout(title=title, height=height, width=width)
        return fig
    
    print(f"✅ Data validation passed, processing {len(data)} subplots")
    
    # Convert string keys to integers and sort
    try:
        print("🔄 Converting string keys to integers...")
        # Convert keys to integers, handling both string and int keys
        converted_data = {}
        for key, value in data.items():
            print(f"   Processing key: {key} (type: {type(key)})")
            if isinstance(key, str):
                try:
                    int_key = int(key)
                    converted_data[int_key] = value
                    print(f"   ✅ Converted '{key}' to {int_key}")
                except ValueError:
                    # If string key can't be converted to int, use hash or enumerate
                    print(f"   ⚠️ Non-numeric string key '{key}' found, using hash-based conversion")
                    int_key = hash(key) % 1000  # Use a reasonable range
                    converted_data[int_key] = value
                    print(f"   ✅ Hash-converted '{key}' to {int_key}")
            else:
                converted_data[key] = value
                print(f"   ✅ Integer key {key} kept as-is")
        
        data = converted_data
        subplot_indices = sorted(data.keys())
        max_subplot_idx = max(subplot_indices)
        
        print(f"✅ Key conversion successful:")
        print(f"   subplot_indices: {subplot_indices}")
        print(f"   max_subplot_idx: {max_subplot_idx}")
        
    except Exception as e:
        print(f"❌ Error processing data keys: {str(e)}")
        # Fallback: create sequential integer keys
        subplot_indices = list(range(1, len(data) + 1))
        max_subplot_idx = len(data)
        converted_data = {}
        for i, (key, value) in enumerate(data.items(), 1):
            converted_data[i] = value
        data = converted_data
        print(f"🔄 Fallback: created sequential keys {subplot_indices}")
    
    # Create a mapping from user indices to grid positions
    print("🗺️ Creating grid mapping...")
    grid_mapping = {}
    for i, idx in enumerate(subplot_indices):
        grid_row = i // cols + 1
        grid_col = i % cols + 1
        grid_mapping[idx] = (grid_row, grid_col)
        print(f"   subplot {idx} -> grid position ({grid_row}, {grid_col})")
    
    # Determine actual rows needed based on data
    actual_rows = (len(subplot_indices) - 1) // cols + 1 if subplot_indices else rows
    actual_rows = max(rows, actual_rows)  # Ensure at least the specified number of rows
    print(f"📐 Grid dimensions: {actual_rows} rows x {cols} cols")
    
    # Prepare subplot specs - default to xy type
    specs = [[{"type": "xy"} for _ in range(cols)] for _ in range(actual_rows)]
    print(f"📋 Created specs: {specs}")
    
    # Prepare subplot titles list
    if subplot_titles:
        print(f"📝 Using provided subplot titles: {subplot_titles}")
        # Extend titles if necessary
        if len(subplot_titles) < len(subplot_indices):
            subplot_titles.extend([f"Plot {i}" for i in range(len(subplot_titles) + 1, max_subplot_idx + 1)])
            print(f"📝 Extended titles to: {subplot_titles}")
    else:
        # Create default titles if none provided
        subplot_titles = [f"Plot {i}" for i in range(1, actual_rows * cols + 1)]
        print(f"📝 Created default titles: {subplot_titles}")
    
    # Validate and fix column_widths
    if column_widths:
        print(f"📏 Processing column widths: {column_widths}")
        if len(column_widths) != cols:
            # If column_widths length doesn't match cols, adjust it
            if len(column_widths) < cols:
                # Extend with equal widths for missing columns
                remaining_width = 1.0 - sum(column_widths)
                missing_cols = cols - len(column_widths)
                if missing_cols > 0:
                    width_per_missing = remaining_width / missing_cols if remaining_width > 0 else 1.0 / cols
                    column_widths.extend([width_per_missing] * missing_cols)
            else:
                # Truncate to match number of columns
                column_widths = column_widths[:cols]
            
            # Normalize column_widths to sum to 1.0
            total_width = sum(column_widths)
            if total_width > 0:
                column_widths = [w / total_width for w in column_widths]
            else:
                column_widths = None  # Use default equal widths
        print(f"📏 Final column widths: {column_widths}")
    
    # Convert plot types to a dictionary mapped to subplot indices
    print("🎨 Mapping plot types to subplots...")
    plot_type_map = {}
    for i, idx in enumerate(subplot_indices):
        if i < len(plot_types):
            plot_type_map[idx] = plot_types[i]
        elif plot_types:
            # Use the last provided plot type as default
            plot_type_map[idx] = plot_types[-1]
        else:
            # Default to bar if no plot types provided
            plot_type_map[idx] = "bar"
        print(f"   subplot {idx} -> plot type: {plot_type_map[idx]}")
    
    # Update specs for special plot types (like pie charts)
    print("🥧 Updating specs for special plot types...")
    for idx, plot_type in plot_type_map.items():
        if idx in grid_mapping and plot_type == 'pie':
            grid_row, grid_col = grid_mapping[idx]
            # Adjust for 0-based indexing in specs
            specs[grid_row-1][grid_col-1] = {"type": "domain"}
            print(f"   Updated spec for pie chart at subplot {idx}")
    
    # Create subplots
    print("🏗️ Creating subplots...")
    try:
        fig = make_subplots(
            rows=actual_rows,
            cols=cols,
            specs=specs,
            column_widths=column_widths,
            subplot_titles=subplot_titles[:actual_rows * cols]  # Ensure we don't exceed grid size
        )
        print("✅ Subplots structure created successfully")
    except Exception as e:
        print(f"❌ Error creating subplots structure: {str(e)}")
        raise
    
    # Default colors if not provided
    colors = colors or PlotHelper.get_default_colors()
    print(f"🎨 Using colors: {colors[:5]}..." if len(colors) > 5 else f"🎨 Using colors: {colors}")
    
    # Add traces for each subplot
    print("📊 Adding traces to subplots...")
    for subplot_idx, traces in data.items():
        print(f"   Processing subplot {subplot_idx} with traces: {list(traces.keys())}")
        
        # Skip if subplot index not in grid mapping
        if subplot_idx not in grid_mapping:
            print(f"   ⚠️ Skipping subplot {subplot_idx} - not in grid mapping")
            continue
            
        grid_row, grid_col = grid_mapping[subplot_idx]
        plot_type = plot_type_map.get(subplot_idx, 'bar')  # Default to bar if not specified
        print(f"   Adding {plot_type} traces to grid position ({grid_row}, {grid_col})")
        
        try:
            _add_traces_to_subplot(fig, traces, plot_type, grid_row, grid_col, colors)
            print(f"   ✅ Successfully added traces for subplot {subplot_idx}")
        except Exception as e:
            print(f"   ❌ Error adding traces for subplot {subplot_idx}: {str(e)}")
            raise
    
    # Update layout
    print("🎨 Updating layout...")
    layout_params = {
        'title': title,
        'height': height,
        'width': width,
        'showlegend': show_legend,
        'annotations': annotations or []
    }
    
    # Set barmode if any bar plots are present
    for plot_type in plot_type_map.values():
        if plot_type == 'bar':
            layout_params['barmode'] = barmode
            print(f"   Set barmode to: {barmode}")
            break
    
    if layout_custom:
        layout_params.update(layout_custom)
        print(f"   Applied custom layout: {layout_custom}")
    
    try:
        fig.update_layout(**layout_params)
        print("✅ Layout updated successfully")
    except Exception as e:
        print(f"❌ Error updating layout: {str(e)}")
        raise
    
    # Update axes titles if provided in data
    print("📝 Updating axes titles...")
    for subplot_idx, traces in data.items():
        if subplot_idx not in grid_mapping:
            continue
            
        grid_row, grid_col = grid_mapping[subplot_idx]
        if 'xaxis_title' in traces:
            fig.update_xaxes(title_text=traces['xaxis_title'], row=grid_row, col=grid_col)
            print(f"   Set x-axis title for subplot {subplot_idx}: {traces['xaxis_title']}")
        if 'yaxis_title' in traces:
            fig.update_yaxes(title_text=traces['yaxis_title'], row=grid_row, col=grid_col)
            print(f"   Set y-axis title for subplot {subplot_idx}: {traces['yaxis_title']}")
    
    print("🎉 create_subplots completed successfully!")
    return fig

def _add_traces_to_subplot(
    fig: go.Figure, 
    traces: Dict[str, Dict[str, Any]], 
    plot_type: str, 
    grid_row: int, 
    grid_col: int, 
    colors: List[str]
) -> None:
    """
    Add traces to a subplot based on plot type
    
    Args:
        fig: Figure object to add traces to
        traces: Dictionary of trace data
        plot_type: Type of plot ('bar', 'pie', etc.)
        grid_row: Row position in grid
        grid_col: Column position in grid
        colors: List of colors to use
    """
    print(f"    🔧 _add_traces_to_subplot called:")
    print(f"       plot_type: {plot_type}")
    print(f"       grid_row: {grid_row}, grid_col: {grid_col}")
    print(f"       traces: {list(traces.keys())}")
    print(f"       colors available: {len(colors)}")
    
    color_idx = 0
    for trace_name, trace_data in traces.items():
        print(f"       Processing trace: {trace_name}")
        print(f"       Trace data keys: {list(trace_data.keys())}")
        print(f"       x data: {trace_data.get('x', [])}")
        print(f"       y data: {trace_data.get('y', [])}")
        
        if trace_name in ['xaxis_title', 'yaxis_title']:
            print(f"       Skipping axis title: {trace_name}")
            continue
        
        # Plot type specific configurations
        if plot_type == 'bar':
            print(f"       Creating bar trace...")
            fig.add_trace(
                go.Bar(
                    x=trace_data.get('x', []),
                    y=trace_data.get('y', []),
                    name=trace_name,
                    marker_color=colors[color_idx % len(colors)],
                    text=trace_data.get('text', []),
                    textposition='outside',
                    textfont=dict(size=12)
                ),
                row=grid_row,
                col=grid_col
            )
            
            # For bar charts, adjust the y-axis range if there are negative values
            y_values = trace_data.get('y', [])
            if y_values and all(isinstance(y, (int, float)) for y in y_values):
                min_val = min(y_values)
                max_val = max(y_values)
                if min_val < 0:
                    # Add padding for negative values
                    fig.update_yaxes(
                        range=[min_val * 1.1, max(max_val * 1.1, 0.1)],
                        row=grid_row, 
                        col=grid_col
                    )
                    print(f"       Updated y-axis range for negative values")
                    
            # Set up proper grid lines and formatting for bar charts
            fig.update_xaxes(
                showgrid=True,
                gridwidth=1,
                gridcolor='rgba(211,211,211,0.5)',
                row=grid_row,
                col=grid_col
            )
            
            fig.update_yaxes(
                showgrid=True,
                gridwidth=1,
                gridcolor='rgba(211,211,211,0.5)',
                row=grid_row,
                col=grid_col
            )
            print(f"       ✅ Bar trace added successfully")
            
        elif plot_type == 'pie':
            print(f"       Creating pie trace...")
            fig.add_trace(
                go.Pie(
                    labels=trace_data.get('labels', trace_data.get('x', [])),
                    values=trace_data.get('values', trace_data.get('y', [])),
                    name=trace_name,
                    marker_colors=colors,
                    text=trace_data.get('text', [])
                ),
                row=grid_row,
                col=grid_col
            )
            print(f"       ✅ Pie trace added successfully")
            
        elif plot_type == 'scatter':
            print(f"       Creating scatter trace...")
            fig.add_trace(
                go.Scatter(
                    x=trace_data.get('x', []),
                    y=trace_data.get('y', []),
                    mode='markers',
                    name=trace_name,
                    marker=dict(color=colors[color_idx % len(colors)]),
                    text=trace_data.get('text', [])
                ),
                row=grid_row,
                col=grid_col
            )
            print(f"       ✅ Scatter trace added successfully")
            
        elif plot_type == 'line':
            print(f"       Creating line trace...")
            fig.add_trace(
                go.Scatter(
                    x=trace_data.get('x', []),
                    y=trace_data.get('y', []),
                    mode='lines',
                    name=trace_name,
                    line=dict(color=colors[color_idx % len(colors)]),
                    text=trace_data.get('text', [])
                ),
                row=grid_row,
                col=grid_col
            )
            print(f"       ✅ Line trace added successfully")
            
        elif plot_type == 'histogram':
            print(f"       Creating histogram trace...")
            fig.add_trace(
                go.Histogram(
                    x=trace_data.get('x', []),
                    name=trace_name,
                    marker_color=colors[color_idx % len(colors)],
                    text=trace_data.get('text', [])
                ),
                row=grid_row,
                col=grid_col
            )
            print(f"       ✅ Histogram trace added successfully")
        else:
            print(f"       ❌ Unknown plot type: {plot_type}")
            
        color_idx += 1
        print(f"       Color index incremented to: {color_idx}")
    
    print(f"    ✅ _add_traces_to_subplot completed for {plot_type} at ({grid_row}, {grid_col})")

def create_plot(
    data: List[Dict[str, Any]],
    plot_type: str = "pie",
    title: str = "Data Visualization",
    x_column: Optional[str] = None,
    y_column: Optional[str] = None,
    color_column: Optional[str] = None,
    size_column: Optional[str] = None,
    text_column: Optional[str] = None,
    color_map: Optional[Dict[str, str]] = None,
    width: int = 800,
    height: int = 600,
    **kwargs
) -> go.Figure:
    """
    Creates various types of plots with minimal configuration.
    
    Args:
        data: Input data as list of dictionaries
        plot_type: Type of plot to create ('pie', 'bar', 'scatter', 'line', 'histogram')
        title: Title of the plot
        x_column: Column name for x-axis (for bar, scatter, line, histogram)
        y_column: Column name for y-axis (for bar, scatter, line)
        color_column: Column name for color grouping
        size_column: Column name for marker size (for scatter)
        text_column: Column name for hover text
        color_map: Optional mapping of categories to colors
        width: Width of the plot in pixels
        height: Height of the plot in pixels
        **kwargs: Additional plot-specific parameters
    
    Returns:
        Plotly figure object
    """
    # Default configurations for different plot types
    default_configs = {
        "pie": {
            "hole_size": 0.5,
            "show_percentage": True,
            "show_total_value": False
        },
        "bar": {
            "orientation": "v",
            "show_legend": True
        },
        "scatter": {
            "mode": "markers",
            "show_legend": True
        },
        "line": {
            "mode": "lines",
            "show_legend": True
        },
        "histogram": {
            "nbinsx": 30,
            "show_legend": False
        }
    }
    
    # Get default config for the plot type
    config = default_configs.get(plot_type, {})
    config.update(kwargs)
    
    # Create figure based on plot type
    plot_creators = {
        "pie": _create_pie_plot,
        "bar": _create_bar_plot,
        "scatter": _create_scatter_plot,
        "line": _create_line_plot,
        "histogram": _create_histogram_plot
    }
    
    creator = plot_creators.get(plot_type)
    if not creator:
        raise ValueError(f"Unsupported plot type: {plot_type}")
        
    return creator(data, title, x_column, y_column, color_column, size_column, 
                  text_column, color_map, width, height, **config)


def _create_pie_plot(
    data: List[Dict[str, Any]],
    title: str,
    x_column: Optional[str],
    y_column: Optional[str],
    color_column: Optional[str],
    size_column: Optional[str],
    text_column: Optional[str],
    color_map: Optional[Dict[str, str]],
    width: int,
    height: int,
    **kwargs
) -> go.Figure:
    """Helper function to create pie plot"""
    # Sort data by value in descending order
    data = sorted(data, key=lambda x: x.get('value', 0), reverse=True)
    
    # Extract names and values
    names = [item.get('name', f'Item {i}') for i, item in enumerate(data)]
    values = [item.get('value', 0) for item in data]
    
    # Calculate total value
    total_value = sum(values)
    
    # Create labels with name and percentage
    labels = [f"{name} ({value/total_value*100:.1f}%)" for name, value in zip(names, values)]
    
    # Generate color map if not provided
    if color_map is None and color_column is not None:
        # Get unique categories
        categories = set()
        for item in data:
            if color_column in item:
                categories.add(item[color_column])
        
        # Create color map
        unique_categories = list(categories)
        colors_list = PlotHelper.get_default_colors(len(unique_categories))
        color_map = {category: colors_list[i % len(colors_list)] for i, category in enumerate(unique_categories)}
    
    # Get colors if color column is specified
    colors = None
    if color_column:
        colors = [color_map.get(item.get(color_column, ''), '#CCCCCC') for item in data]
    
    # Create pie chart with improved label settings
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        textinfo='percent' if kwargs.get('show_percentage', True) else 'none',
        textposition='outside',
        textfont=dict(size=12),
        insidetextorientation='radial',
        hoverinfo='label+value+percent',
        marker=dict(colors=colors),
        hole=kwargs.get('hole_size', 0.5)
    )])
    
    # Create layout
    layout = PlotHelper.create_figure_layout(
        title=title,
        width=width,
        height=height,
        show_legend=True,
        uniformtext=dict(minsize=12, mode='hide')
    )
    
    # Add total value annotation if requested
    if kwargs.get('show_total_value', True):
        layout['annotations'] = [
            dict(
                text=f'Total: {total_value:.2f}',
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(size=16)
            )
        ]
    
    fig.update_layout(**layout)
    
    # Adjust label positions to prevent overlap
    fig.update_traces(
        textposition='outside',
        textfont_size=12,
        pull=[0.1 if i == 0 else 0 for i in range(len(data))]  # Pull out the largest slice slightly
    )
    
    return fig


def _create_bar_plot(
    data: List[Dict[str, Any]],
    title: str,
    x_column: str,
    y_column: str,
    color_column: Optional[str],
    size_column: Optional[str],
    text_column: Optional[str],
    color_map: Optional[Dict[str, str]],
    width: int,
    height: int,
    **kwargs
) -> go.Figure:
    """Helper function to create bar plot"""
    fig = go.Figure()
    
    if color_column:
        # Group data by color category
        categories = {}
        for item in data:
            category = item.get(color_column, 'Unknown')
            if category not in categories:
                categories[category] = []
            categories[category].append(item)
        
        # Add each category as a separate trace
        for category, items in categories.items():
            x_values = [item.get(x_column, '') for item in items]
            y_values = [item.get(y_column, 0) for item in items]
            text_values = y_values if kwargs.get('show_values', True) else None
            
            fig.add_trace(go.Bar(
                x=x_values,
                y=y_values,
                name=category,
                text=text_values,
                textposition='auto'
            ))
    else:
        # No categories, add all data as one trace
        x_values = [item.get(x_column, '') for item in data]
        y_values = [item.get(y_column, 0) for item in data]
        text_values = y_values if kwargs.get('show_values', True) else None
        
        fig.add_trace(go.Bar(
            x=x_values,
            y=y_values,
            text=text_values,
            textposition='auto'
        ))
    
    layout = PlotHelper.create_figure_layout(
        title=title,
        width=width,
        height=height,
        show_legend=kwargs.get('show_legend', True),
        barmode='group' if color_column else 'stack'
    )
    
    fig.update_layout(**layout)
    
    return fig


def _create_scatter_plot(
    data: List[Dict[str, Any]],
    title: str,
    x_column: str,
    y_column: str,
    color_column: Optional[str],
    size_column: Optional[str],
    text_column: Optional[str],
    color_map: Optional[Dict[str, str]],
    width: int,
    height: int,
    **kwargs
) -> go.Figure:
    """Helper function to create scatter plot"""
    fig = go.Figure()
    
    if color_column:
        # Group data by color category
        categories = {}
        for item in data:
            category = item.get(color_column, 'Unknown')
            if category not in categories:
                categories[category] = []
            categories[category].append(item)
        
        # Add each category as a separate trace
        for category, items in categories.items():
            x_values = [item.get(x_column, 0) for item in items]
            y_values = [item.get(y_column, 0) for item in items]
            
            # Get size values if size column is specified
            size_values = None
            if size_column:
                size_values = [item.get(size_column, 10) for item in items]
                # Calculate size reference for consistent marker size
                max_size = max(size_values) if size_values else 0
                size_ref = 2.0 * max_size / (40.**2) if max_size > 0 else None
            else:
                size_values = 10
                size_ref = None
            
            # Get text values if text column is specified
            text_values = None
            if text_column:
                text_values = [item.get(text_column, '') for item in items]
            
            fig.add_trace(go.Scatter(
                x=x_values,
                y=y_values,
                mode=kwargs.get('mode', 'markers'),
                name=category,
                text=text_values,
                marker=dict(
                    size=size_values,
                    sizemode='area',
                    sizeref=size_ref
                )
            ))
    else:
        # No categories, add all data as one trace
        x_values = [item.get(x_column, 0) for item in data]
        y_values = [item.get(y_column, 0) for item in data]
        
        # Get size values if size column is specified
        size_values = None
        if size_column:
            size_values = [item.get(size_column, 10) for item in data]
            # Calculate size reference for consistent marker size
            max_size = max(size_values) if size_values else 0
            size_ref = 2.0 * max_size / (40.**2) if max_size > 0 else None
        else:
            size_values = 10
            size_ref = None
        
        # Get text values if text column is specified
        text_values = None
        if text_column:
            text_values = [item.get(text_column, '') for item in data]
        
        fig.add_trace(go.Scatter(
            x=x_values,
            y=y_values,
            mode=kwargs.get('mode', 'markers'),
            text=text_values,
            marker=dict(
                size=size_values,
                sizemode='area',
                sizeref=size_ref
            )
        ))
    
    layout = PlotHelper.create_figure_layout(
        title=title,
        width=width,
        height=height,
        show_legend=kwargs.get('show_legend', True)
    )
    
    fig.update_layout(**layout)
    
    return fig

def _create_line_plot(
    data: List[Dict[str, Any]],
    title: str,
    x_column: str,
    y_column: str,
    color_column: Optional[str],
    size_column: Optional[str],
    text_column: Optional[str],
    color_map: Optional[Dict[str, str]],
    width: int,
    height: int,
    **kwargs
) -> go.Figure:
    """Helper function to create line plot"""
    fig = go.Figure()
    
    if color_column:
        # Group data by color category
        categories = {}
        for item in data:
            category = item.get(color_column, 'Unknown')
            if category not in categories:
                categories[category] = []
            categories[category].append(item)
        
        # Add each category as a separate trace
        for category, items in categories.items():
            # Sort items by x value for proper line connection
            sorted_items = sorted(items, key=lambda x: x.get(x_column, 0))
            
            x_values = [item.get(x_column, 0) for item in sorted_items]
            y_values = [item.get(y_column, 0) for item in sorted_items]
            
            fig.add_trace(go.Scatter(
                x=x_values,
                y=y_values,
                mode=kwargs.get('mode', 'lines'),
                name=category
            ))
    else:
        # No categories, add all data as one trace
        print(f"[LINE PLOT] Creating single trace without categories")
        print(f"[LINE PLOT] Raw data count: {len(data)}")
        
        # Sort items by x value for proper line connection
        sorted_data = sorted(data, key=lambda x: x.get(x_column, 0))
        print(f"[LINE PLOT] Data sorted by x_column '{x_column}'")
        
        x_values = [item.get(x_column, 0) for item in sorted_data]
        y_values = [item.get(y_column, 0) for item in sorted_data]
        
        print(f"[LINE PLOT] X values: {x_values}")
        print(f"[LINE PLOT] Y values: {y_values}")
        print(f"[LINE PLOT] Mode: {kwargs.get('mode', 'lines')}")
        
        fig.add_trace(go.Scatter(
            x=x_values,
            y=y_values,
            mode=kwargs.get('mode', 'lines')
        ))
        
        print(f"[LINE PLOT] Scatter trace added successfully")
    
    print(f"[LINE PLOT] Creating layout with title: '{title}'")
    print(f"\nWidth {width}  Height:{height} \n\n")
    layout = PlotHelper.create_figure_layout(
        title=title,
        width=None,
        height=None,
        show_legend=kwargs.get('show_legend', True)
    )
    
    fig.update_layout(**layout)
    print(f"[LINE PLOT] Layout applied successfully")
    
    return fig

def _create_histogram_plot(
    data: List[Dict[str, Any]],
    title: str,
    x_column: str,
    color_column: Optional[str],
    size_column: Optional[str],
    text_column: Optional[str],
    color_map: Optional[Dict[str, str]],
    width: int,
    height: int,
    **kwargs
) -> go.Figure:
    """Helper function to create histogram plot"""
    fig = go.Figure()
    
    if color_column:
        # Group data by color category
        categories = {}
        for item in data:
            category = item.get(color_column, 'Unknown')
            if category not in categories:
                categories[category] = []
            categories[category].append(item)
        
        # Add each category as a separate trace
        for category, items in categories.items():
            x_values = [item.get(x_column, 0) for item in items]
            
            fig.add_trace(go.Histogram(
                x=x_values,
                name=category,
                nbinsx=kwargs.get('nbinsx', 30)
            ))
    else:
        # No categories, add all data as one trace
        x_values = [item.get(x_column, 0) for item in data]
        
        fig.add_trace(go.Histogram(
            x=x_values,
            nbinsx=kwargs.get('nbinsx', 30)
        ))
    
    layout = PlotHelper.create_figure_layout(
        title=title,
        width=width,
        height=height,
        show_legend=kwargs.get('show_legend', False),
        barmode='overlay'
    )
    
    fig.update_layout(**layout)
    
    return fig

def get_portfolio_data() -> Dict[str, Any]:
    """
    Get user's portfolio information for both stocks and crypto in JSON format.
    
    Returns:
        dict: A JSON-serializable dictionary containing portfolio data
    """
    try:
        # Get stocks and crypto data
        stocks_data = portfolio_stocks()
        crypto_data = portfolio_crypto()
        
        # Extract holdings information
        stocks_info = stocks_data.get('data', {}).get('holdings', [])
        crypto_info = crypto_data.get('data', {}).get('holdings', [])
        
        # Prepare combined portfolio data
        portfolio_data = {
            "stocks": stocks_info,
            "crypto": crypto_info,
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_stocks": len(stocks_info),
                "total_crypto": len(crypto_info)
            }
        }
        
        # Calculate totals
        total_stock_value = sum(float(stock.get('currentValue', 0)) for stock in stocks_info)
        total_crypto_value = sum(float(crypto.get('currentValue', 0)) for crypto in crypto_info)
        total_portfolio_value = total_stock_value + total_crypto_value
        
        portfolio_data["summary"]["total_stock_value"] = total_stock_value
        portfolio_data["summary"]["total_crypto_value"] = total_crypto_value
        portfolio_data["summary"]["total_portfolio_value"] = total_portfolio_value
        
        if total_portfolio_value > 0:
            portfolio_data["summary"]["stock_percentage"] = (total_stock_value / total_portfolio_value) * 100
            portfolio_data["summary"]["crypto_percentage"] = (total_crypto_value / total_portfolio_value) * 100
        
        return portfolio_data
        
    except Exception as e:
        logger.error(f"Error getting portfolio data", context={"error": str(e)})
        return {"error": str(e), "message": "Failed to retrieve portfolio data"}