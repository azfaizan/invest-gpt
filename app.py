import os,json,uuid,datetime
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from src.utils.logger_factory import LoggerFactory
from src.tools import financial_api
from pydantic import BaseModel
from src.statics import MODEL_NAME, STATICS


# Security scheme for API key authentication
#security = HTTPBearer()
security = HTTPBearer(
    scheme_name="BearerAuth",
    description="Enter your API key as a Bearer token"
)


def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)):
    """
    Verify the API key from the Authorization header.
    Expected format: Bearer <api_key>
    """
    # Get the expected API key from environment variables
    expected_api_key = os.getenv("API_KEY")
    
    if not expected_api_key:
        logger.critical("API_KEY environment variable not set")
        raise HTTPException(
            status_code=500,
            detail="Server configuration error"
        )
    
    # Extract the token from credentials
    provided_key = credentials.credentials
    
    # Verify the API key
    if provided_key != expected_api_key:
        logger.warning(
            f"Invalid API key attempt",
            context={"provided_key_prefix": provided_key[:8] + "..." if len(provided_key) > 8 else provided_key}
        )
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    
    logger.info("API key validated successfully")
    return True


async def is_trading_related_query(query: str) -> bool:
    """
    Use GPT-4o-mini to determine if a query is related to trading/investment topics.
    Returns True if relevant, False if irrelevant.
    """
    from langchain_openai import ChatOpenAI
    
    try:
        # Create a lightweight LLM instance for classification
        classifier_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        
        classification_prompt = f"""You are a query classifier for InvestmentMarket.ae, the premier investment and trading platform in the UAE. Your job is to determine if a user query is related to trading, investments, finance, or markets.

Respond with ONLY "YES" if the query is about:
- Trading, stocks, shares, investments
- Cryptocurrency, Bitcoin, Ethereum, etc.
- Portfolio management, financial planning
- Market analysis, economic trends
- Financial data, charts, or visualizations
- Banking, finance, money management
- Any financial instruments (bonds, ETFs, options, etc.)
- Any support questions for InvestmentMarket.ae

Respond with ONLY "NO" if the query is about:
- General knowledge questions
- Personal questions unrelated to finance
- Weather, cooking, entertainment, sports
- Any non-financial topics

User query: "{query}"

Response (YES or NO):"""

        response = classifier_llm.invoke([{"role": "user", "content": classification_prompt}])
        
        # Extract the response and check if it's YES
        result = response.content.strip().upper()
        return result == "YES"
        
    except Exception as e:
        # If classification fails, default to allowing the query (fail-safe)
        logger.error(f"Error in query classification: {str(e)}")
        return True


plot_cache = {}
load_dotenv()
app = FastAPI(
    title="InvestmentMarket.ae Trading Assistant API",
    description="Secure API for InvestmentMarket.ae's AI-powered trading and investment assistant",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logger = LoggerFactory.create_logger(service_name="invest-gpt")
logger.notice("Application starting up, Logger initialized")


required_vars = ["OPENAI_API_KEY", "API_KEY"]
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    logger.critical(
        f"Missing required environment variables",
        context={"missing_vars": missing_vars}
    )
    raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")


class QueryRequest(BaseModel):
    """Model for query requests"""
    query: str


def portfolio_get_data():
    """Get the user's portfolio data including stocks and cryptocurrency holdings"""
    print("portfolio_get_data called")
    return financial_api.get_portfolio_data()

def create_plot(data, plot_type="pie", title="Data Visualization", x_column=None, y_column=None, 
                color_column=None, size_column=None, text_column=None, color_map=None, 
                width=800, height=600, **kwargs):
    """
    Creates various types of plots with minimal configuration and caches them.
    
    Returns:
        dict: A message indicating success and a plot_id for retrieval
    """
    print("create_plot called with:", data, plot_type, title)
    try:
        # Call the plotting function from financial_api
        plot = financial_api.create_plot(
            data=data, 
            plot_type=plot_type, 
            title=title, 
            x_column=x_column, 
            y_column=y_column, 
            color_column=color_column, 
            size_column=size_column, 
            text_column=text_column, 
            color_map=color_map, 
            width=width, 
            height=height, 
            **kwargs
        )
        
        # Generate HTML from the plot
        import plotly
        plot_html = plotly.io.to_html(plot, include_plotlyjs='cdn', full_html=False)
        
        # Generate a unique ID for the plot
        plot_id = str(uuid.uuid4())
        
        # Store in cache
        plot_cache[plot_id] = plot_html
        
        # Store in financial_api.plot for backward compatibility
        financial_api.plot = plot_html
        
        return {
            "message": "Plot created successfully",
            "plot_id": plot_id
        }
    except Exception as e:
        import traceback
        logger.error(
            f"Error creating plot",
            context={"error": str(e), "traceback": traceback.format_exc()}
        )
        return {
            "message": f"Error creating plot: {str(e)}",
            "error": str(e)
        }

def create_subplots(data, plot_types, rows=1, cols=2, subplot_titles=None, column_widths=None, 
                   title="Dynamic Subplots", height=600, width=None, barmode='group', 
                   colors=None, show_legend=True, annotations=None, layout_custom=None):
    """
    Create dynamic subplots with customizable parameters and cache them.
    
    Returns:
        dict: A message indicating success and a plot_id for retrieval
    """
    print("create_subplots called with:", data, plot_types, title)
    
    # Validate data is not empty
    if not data or len(data) == 0:
        error_message = "Error: Empty data provided. Visualization requires actual data to plot."
        logger.error(error_message)
        return {
            "message": error_message,
            "error": "Empty data object"
        }
        
    try:
        # Call the subplots function from financial_api
        fig = financial_api.create_subplots(
            data=data,
            plot_types=plot_types,
            rows=rows,
            cols=cols,
            subplot_titles=subplot_titles,
            column_widths=column_widths,
            title=title,
            height=height,
            width=width,
            barmode=barmode,
            colors=colors,
            show_legend=show_legend,
            annotations=annotations,
            layout_custom=layout_custom
        )

        plot_html = fig.to_html(include_plotlyjs='cdn', full_html=True)
        plot_id = str(uuid.uuid4())
        plot_cache[plot_id] = plot_html
        
        return {
            "message": "Subplots created successfully",
            "plot_id": plot_id
        }
    except Exception as e:
        import traceback
        logger.error(
            f"Error creating subplots",
            context={"error": str(e), "traceback": traceback.format_exc()}
        )
        return {
            "message": f"Error creating subplots: {str(e)}",
            "error": str(e)
        }


@app.get("/")
async def root():
    """Public endpoint with basic API information"""
    return {
        "service": "InvestmentMarket.ae Trading Assistant API",
        "version": "1.0.0",
        "description": "Secure API for AI-powered trading and investment assistance",
        "authentication": "Required - Use Bearer token in Authorization header",
        "endpoints": {
            "health": "GET /health - Service health check (authenticated)",
            "query": "POST /query - Process trading queries (authenticated)",
            "docs": "GET /docs - API documentation"
        }
    }

@app.get("/auth/test")
async def test_auth(authenticated: bool = Depends(verify_api_key)):
    """Test endpoint to verify API key authentication"""
    return {
        "status": authenticated,
        "message": "API key is valid",
        "service": "InvestmentMarket.ae Trading Assistant"
    }

@app.get("/health")
async def health():
    """Process a query and return a response"""
    current_time = datetime.datetime.now()
    return str(current_time)
        
@app.post("/query")
async def process_query(request: QueryRequest, authenticated: bool = Depends(verify_api_key)):
    """Process a query and return a response"""
    from langchain_openai import ChatOpenAI
    
    request_id = str(datetime.datetime.now().timestamp())
    
    try:
        # Log incoming query
        logger.info(
            f"Processing query",
            context={
                "request_id": request_id,
                "query": request.query
            }
        )
        
        # Check if query is trading/investment related
        if not await is_trading_related_query(request.query):
            apology_message = "I apologize, but I'm InvestmentMarket.ae's specialized trading assistant. I can only help with questions related to investments, trading, portfolio management, cryptocurrency, stock markets, and financial analysis. Please ask me something related to these topics, and I'll be happy to show you how InvestmentMarket.ae can help you achieve your investment goals." 
            logger.info(
                f"Query filtered as irrelevant",
                context={
                    "request_id": request_id,
                    "query": request.query,
                    "response": "apology_message"
                }
            )
            
            return {
                'statusCode': 200,
                "headers": {"Content-Type": "text/html"},
                'body': apology_message,
                "html": None
            }
        
        # Create LLM instance
        llm = ChatOpenAI(model=MODEL_NAME, temperature=0)

        # Define tools
        web_search_tool = {"type": "web_search_preview"}
        portfolio_tool = {
            "type": "function",
            "function": {
                "name": "portfolio_get_data",
                "description": "Get the user's portfolio data including stocks and cryptocurrency holdings",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        }
        # Add plotting tools based on plotting_prompt from statics.py
        create_plot_tool = {
            "type": "function",
            "function": {
                "name": "create_plot",
                "description": "Creates a single visualization (pie, bar, scatter, line, histogram) with customizable options."}}
        
        create_subplots_tool = {
            "type": "function",
            "function": {
                "name": "create_subplots",
                "description": "Creates multiple visualizations in a single figure for comparison or multi-view analysis"}}
        # Set up available functions
        available_functions = {
            "portfolio_get_data": portfolio_get_data,
            "create_plot": create_plot,
            "create_subplots": create_subplots
        }
        
        # Bind tools
        llm_with_tools = llm.bind_tools([web_search_tool, portfolio_tool, create_plot_tool, create_subplots_tool])
        
        # Create conversation with system and user messages
        messages = [
            {"role": "system", "content": STATICS['SYSTEM_PROMPT']},
            {"role": "user", "content": request.query}
        ]
        
        logger.info("Processing query", context={"query": request.query})
        
        # Initialize variables for the tool calling loop
        max_iterations = 5  # Prevent infinite loops
        iteration = 0
        
        #print(f"{'*'*50}\n{'*'*20} LLM CALL  {'*'*20}\n{'*'*50}")
        logger.info("LLM CALL", context={"messages": messages})
        #print(messages)
        response = llm_with_tools.invoke(messages)
        #print(f"{'*'*50}\n{'*'*20} Response  {'*'*20}\n{'*'*50}")
        #print(response)
        logger.info("LLM Response", context={"response": response.content})
        plot_id=None
        while iteration < max_iterations:
            iteration += 1
            #print(f"{'*'*50}\n{'*'*20} ITERATION {iteration} {'*'*20}\n{'*'*50}")
            logger.info("ITERATION", context={"iteration": iteration})
            if not hasattr(response, 'tool_calls') or not response.tool_calls:
                logger.info("No tool calls in response, using as final output")
                break
  
            messages.append(response)
            

            tool_outputs = []
            for tool_call in response.tool_calls:
                try:
                    function_name = tool_call['name']
                    
                    if function_name not in available_functions:
                        logger.error(f"Invalid function name: {function_name}")
                        continue

                    try:
                        function_args = json.loads(tool_call['args']) if isinstance(tool_call['args'], str) else tool_call['args']
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON in function args: {str(e)}")
                        continue
           
                    function_to_call = available_functions[function_name]
                    function_response = function_to_call(**function_args)
                    if function_response.get('plot_id'):
                        plot_id=function_response['plot_id']
                        function_response="plot has been created and saved in cache, and will be returned with the final response, you should now just explain what plot is all about."
                        print("\n\nHas plot id**\n\n")
                    tool_outputs.append({
                        "tool_call_id": tool_call['id'],
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps(function_response)
                    })
                    
                except Exception as e:
                    logger.error(f"Error processing tool call: {str(e)}")

            messages.extend(tool_outputs)
            
            
            
            try:
                #print(f"{'*'*50}\n{'*'*20} LLM CALL {messages} {'*'*20}\n{'*'*50}")
                logger.info("LLM CALL", context={"messages": "".join(str(message) for message in messages)})
                response = llm_with_tools.invoke(messages)
                logger.info("LLM Response", context={"response": response.content})
                #print(f"{'*'*50}\n{'*'*20} LLM Response{'*'*20}\n{'*'*50}")
                #print(response,"\n\n")
            except Exception as e:
                logger.error(f"Error getting LLM response: {str(e)}")
                response = f"Error processing your request after {iteration} iterations: {str(e)}"
                break
        

        if iteration >= max_iterations and (hasattr(response, 'tool_calls') and response.tool_calls):
            logger.warning(f"Reached maximum iterations ({max_iterations}), breaking the loop")
            response = f"I've reached the maximum number of tool calls ({max_iterations}). Here's what I've found so far:\n\n{response.content}"
        
        response = response.content if type(response) != str else response 
        #print(response)   
        logger.info("FINAL OUTPUT", context={"output": response})
        plot_html=plot_cache[plot_id] if plot_id else None
        plot_cache.pop(plot_id, None)
        return {
            'statusCode': 200,
            "headers": {"Content-Type": "text/html"},
            'body': response,
            "html": plot_html}
    
    except Exception as e:
        import traceback
        traceback_str = traceback.format_exc()
        logger.error(
            f"Error processing query",
            context={"request_id": request_id, "traceback": traceback_str},
            exception=e
        )
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'text/html'},
            'body': f"<p>Error processing your request: {str(e)}</p>",
            "html": None
        }

# Run the FastAPI app
if __name__ == "__main__":
    import uvicorn
    logger.notice("Starting uvicorn server on port 8000")
    uvicorn.run(app, host="0.0.0.0", port=8000) 