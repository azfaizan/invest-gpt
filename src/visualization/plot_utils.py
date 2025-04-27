import plotly.graph_objects as go
import plotly.colors as pc
import plotly.express as px
from typing import List, Dict, Any, Optional, Union
from plotly.subplots import make_subplots
import pandas as pd

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
            "show_total_value": True
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
    if plot_type == "pie":
        return _create_pie_plot(data, title, color_column, color_map, width, height, **config)
    elif plot_type == "bar":
        return _create_bar_plot(data, title, x_column, y_column, color_column, width, height, **config)
    elif plot_type == "scatter":
        return _create_scatter_plot(data, title, x_column, y_column, color_column, size_column, text_column, width, height, **config)
    elif plot_type == "line":
        return _create_line_plot(data, title, x_column, y_column, color_column, width, height, **config)
    elif plot_type == "histogram":
        return _create_histogram_plot(data, title, x_column, color_column, width, height, **config)
    else:
        raise ValueError(f"Unsupported plot type: {plot_type}")

def _create_pie_plot(
    data: List[Dict[str, Any]],
    title: str,
    color_column: Optional[str],
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
        colors_list = pc.qualitative.Plotly if len(unique_categories) <= 10 else pc.qualitative.Dark24
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
    
    # Update layout with improved label positioning
    fig.update_layout(
        title=title,
        width=width,
        height=height,
        showlegend=True,
        margin=dict(t=50, b=50, l=50, r=50),
        uniformtext=dict(
            minsize=12,
            mode='hide'
        ),
        annotations=[
            dict(
                text=f'Total: {total_value:.2f}',
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(size=16)
            ) if kwargs.get('show_total_value', True) else None
        ]
    )
    
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
    
    fig.update_layout(
        title=title,
        width=width,
        height=height,
        showlegend=kwargs.get('show_legend', True),
        barmode='group' if color_column else 'stack'
    )
    
    return fig

def _create_scatter_plot(
    data: List[Dict[str, Any]],
    title: str,
    x_column: str,
    y_column: str,
    color_column: Optional[str],
    size_column: Optional[str],
    text_column: Optional[str],
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
    
    fig.update_layout(
        title=title,
        width=width,
        height=height,
        showlegend=kwargs.get('show_legend', True)
    )
    
    return fig

def _create_line_plot(
    data: List[Dict[str, Any]],
    title: str,
    x_column: str,
    y_column: str,
    color_column: Optional[str],
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
        # Sort items by x value for proper line connection
        sorted_data = sorted(data, key=lambda x: x.get(x_column, 0))
        
        x_values = [item.get(x_column, 0) for item in sorted_data]
        y_values = [item.get(y_column, 0) for item in sorted_data]
        
        fig.add_trace(go.Scatter(
            x=x_values,
            y=y_values,
            mode=kwargs.get('mode', 'lines')
        ))
    
    fig.update_layout(
        title=title,
        width=width,
        height=height,
        showlegend=kwargs.get('show_legend', True)
    )
    
    return fig

def _create_histogram_plot(
    data: List[Dict[str, Any]],
    title: str,
    x_column: str,
    color_column: Optional[str],
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
    
    fig.update_layout(
        title=title,
        width=width,
        height=height,
        showlegend=kwargs.get('show_legend', False),
        barmode='overlay'
    )
    
    return fig

def create_subplots(
    data: Dict[int, Dict[str, Dict[str, Any]]],
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
    # Handle empty data case
    if not data:
        # Create an empty figure with default parameters
        fig = go.Figure()
        fig.update_layout(title=title, height=height, width=width)
        return fig
    
    # Get subplot indices from data
    subplot_indices = sorted(data.keys())
    max_subplot_idx = max(subplot_indices)
    
    # Create a mapping from user indices to grid positions
    # This allows for arbitrary subplot indices
    grid_mapping = {}
    for i, idx in enumerate(subplot_indices):
        grid_row = i // cols + 1
        grid_col = i % cols + 1
        grid_mapping[idx] = (grid_row, grid_col)
    
    # Determine actual rows needed based on data
    actual_rows = (len(subplot_indices) - 1) // cols + 1 if subplot_indices else rows
    actual_rows = max(rows, actual_rows)  # Ensure at least the specified number of rows
    
    # Prepare subplot specs - default to xy type
    specs = [[{"type": "xy"} for _ in range(cols)] for _ in range(actual_rows)]
    
    # Prepare subplot titles list
    if subplot_titles:
        # Extend titles if necessary
        if len(subplot_titles) < len(subplot_indices):
            subplot_titles.extend([f"Plot {i}" for i in range(len(subplot_titles) + 1, max_subplot_idx + 1)])
    else:
        # Create default titles if none provided
        subplot_titles = [f"Plot {i}" for i in range(1, actual_rows * cols + 1)]
    
    # Convert plot types to a dictionary mapped to subplot indices
    # This ensures we can handle any number of plot types
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
    
    # Update specs for special plot types (like pie charts)
    for idx, plot_type in plot_type_map.items():
        if idx in grid_mapping and plot_type == 'pie':
            grid_row, grid_col = grid_mapping[idx]
            # Adjust for 0-based indexing in specs
            specs[grid_row-1][grid_col-1] = {"type": "domain"}
    
    # Create subplots
    fig = make_subplots(
        rows=actual_rows,
        cols=cols,
        specs=specs,
        column_widths=column_widths,
        subplot_titles=subplot_titles[:actual_rows * cols]  # Ensure we don't exceed grid size
    )
    
    # Default colors if not provided
    default_colors = ['#3D9970', '#FF851B', '#FF4136', '#2ECC40', '#0074D9']
    colors = colors or default_colors
    
    # Add traces for each subplot
    for subplot_idx, traces in data.items():
        # Skip if subplot index not in grid mapping
        if subplot_idx not in grid_mapping:
            continue
            
        grid_row, grid_col = grid_mapping[subplot_idx]
        plot_type = plot_type_map.get(subplot_idx, 'bar')  # Default to bar if not specified
        
        color_idx = 0
        for trace_name, trace_data in traces.items():
            if trace_name in ['xaxis_title', 'yaxis_title']:
                continue
                
            # Common parameters
            common_params = {
                'name': trace_name,
                'text': trace_data.get('text', []),
                'textposition': 'auto'
            }
            
            # Plot type specific configurations
            if plot_type == 'bar':
                fig.add_trace(
                    go.Bar(
                        x=trace_data.get('x', []),
                        y=trace_data.get('y', []),
                        marker_color=colors[color_idx % len(colors)],
                        **{k:v for k,v in common_params.items() if k != 'textposition'}
                    ),
                    row=grid_row,
                    col=grid_col
                )
            elif plot_type == 'pie':
                fig.add_trace(
                    go.Pie(
                        labels=trace_data.get('labels', trace_data.get('x', [])),
                        values=trace_data.get('values', trace_data.get('y', [])),
                        marker_colors=colors,
                        **common_params
                    ),
                    row=grid_row,
                    col=grid_col
                )
            elif plot_type == 'scatter':
                fig.add_trace(
                    go.Scatter(
                        x=trace_data.get('x', []),
                        y=trace_data.get('y', []),
                        mode='markers',
                        marker=dict(color=colors[color_idx % len(colors)]),
                        **common_params
                    ),
                    row=grid_row,
                    col=grid_col
                )
            elif plot_type == 'line':
                fig.add_trace(
                    go.Scatter(
                        x=trace_data.get('x', []),
                        y=trace_data.get('y', []),
                        mode='lines',
                        marker=dict(color=colors[color_idx % len(colors)]),
                        **common_params
                    ),
                    row=grid_row,
                    col=grid_col
                )
            color_idx += 1
    
    # Update layout
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
            break
    
    if layout_custom:
        layout_params.update(layout_custom)
    
    fig.update_layout(**layout_params)
    
    # Update axes titles if provided in data
    for subplot_idx, traces in data.items():
        if subplot_idx not in grid_mapping:
            continue
            
        grid_row, grid_col = grid_mapping[subplot_idx]
        if 'xaxis_title' in traces:
            fig.update_xaxes(title_text=traces['xaxis_title'], row=grid_row, col=grid_col)
        if 'yaxis_title' in traces:
            fig.update_yaxes(title_text=traces['yaxis_title'], row=grid_row, col=grid_col)
    
    return fig