# InvestGPT - LangChain Project

This project provides a LangChain-based investment assistant that can perform various financial data queries and visualizations.

## Features

- Search the web for cryptocurrency information
- Retrieve cryptocurrency metadata and price performance statistics
- View portfolio information (stocks and crypto)
- Generate data visualizations for financial analysis
- **NEW**: Direct API access for flexible data retrieval

## Setup

1. Clone this repository
2. Install required dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and add your API keys:
   ```
   cp .env.example .env
   ```
4. Edit the `.env` file and add your API keys

## Usage

### Standard Version (Pre-defined Functions)

Run the main application that uses pre-defined functions:

```
python main.py
```

Or use the API interface:

```
python app.py
```

### Direct API Version

Run the application with direct API access capabilities:

```
python direct_api_cli.py
```

Or use the direct API web server:

```
python app_direct.py
```

## API Functions

### Standard Version

The agent has access to these pre-defined functions:
- Web search for cryptocurrency information
- Cryptocurrency metadata retrieval
- Cryptocurrency price performance statistics
- Portfolio information retrieval
- Data visualization generation

### Direct API Version

The agent can:
- Make HTTP requests to any API endpoint
- Perform Tavily web searches directly
- Access stock and crypto portfolio data
- Retrieve cryptocurrency metadata and price stats
- Create data visualizations

## How Direct API Calls Work

Instead of wrapping API calls in custom functions, the direct API version allows the LLM to:

1. Construct and execute HTTP requests to any endpoint
2. Choose appropriate API endpoints based on the task
3. Handle request parameters, headers, and response data directly
4. Dynamically adapt to different API formats and requirements

This gives the model much more flexibility to access any data source without being constrained to pre-defined functions.

## Project Structure

- `main.py`: Main entry point for the standard console application
- `app.py`: FastAPI web server for the standard API
- `direct_api_cli.py`: Console application with direct API capabilities
- `app_direct.py`: FastAPI web server with direct API capabilities
- `src/tools/`: Tools and functions for financial data
- `src/chains/`: LangChain chains and agents
- `src/visualization/`: Data visualization utilities 