import os,json,datetime
from typing import Any, Dict, List
import uuid
from dotenv import load_dotenv
from fastapi import FastAPI, Depends
from fastapi.security import HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from src.utils.logger_factory import LoggerFactory
from src.statics import MODEL_NAME, STATICS
from src.models import ResponseBody, APIResponse,QueryRequest
from src.utils.api_helpers import initialize_chat_model,verify_api_key, is_trading_related_query, clean_external_references
from src.utils import api_helpers
from src.tools import financial_api
import plotly

plot_cache = {}
load_dotenv()
security = HTTPBearer(
    scheme_name="BearerAuth",
    description="Enter your API key as a Bearer token"
)
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
        
        
        plot_html = plotly.io.to_html(plot, include_plotlyjs='cdn', full_html=False)
        plot_id = str(uuid.uuid4())
        plot_cache[plot_id] = plot_html
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
    
    if not data or len(data) == 0:
        error_message = "Error: Empty data provided. Visualization requires actual data to plot."
        print("**Error in create_subplots**",error_message)
        logger.error(error_message)
        return {
            "message": error_message,
            "error": "Empty data object"
        }
        
    try:
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
# 
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

@app.get("/auth/test",response_model=APIResponse)
async def test_auth(authenticated: bool = Depends(verify_api_key)) -> APIResponse:
    """Test endpoint to verify API key authentication"""
    return APIResponse (
        statusCode=200,
        headers={"Content-Type": "text/html"},
        body=response_format("API key is valid"),
        html=None
    )

@app.get("/health")
async def health():
    """Process a query and return a response"""
    current_time = datetime.datetime.now()
    return str(current_time)
        
@app.post("/query", response_model=APIResponse)
async def process_query(request: QueryRequest, authenticated: bool = Depends(verify_api_key)) -> APIResponse:
    """Process a query and return a response"""
    
    # Start timing the request
    start_time = datetime.datetime.now()
    request_id = str(start_time.timestamp())
    
    try:
        logger.info(
            f"Processing query",
            context={
                "request_id": request_id,
                "query": request.query
            }
        )
        if not await is_trading_related_query(request.query):
            apology_message = "I apologize, but I'm InvestmentMarket.ae's specialized trading assistant. I can only help with questions related to investments, trading, portfolio management, cryptocurrency, stock markets, and financial analysis. Please ask me something related to these topics, and I'll be happy to show you how InvestmentMarket.ae can help you achieve your investment goals." 
            
            return APIResponse(
                statusCode=200,
                headers={"Content-Type": "text/html"},
                body=response_format(apology_message),
                html=None
            )
        
        available_functions = {
            "portfolio_get_data": financial_api.get_portfolio_data,
            "create_plot": create_plot,
            "create_subplots": create_subplots
        }
        
        llm_with_tools = await initialize_chat_model()
        
        messages = [
            {"role": "system", "content": STATICS['SYSTEM_PROMPT']},
            {"role": "user", "content": request.query}
        ]
        
        logger.info("Processing query", context={"query": request.query})
        
        # Initialize variables for the tool calling loop
        max_iterations = 3  # Prevent infinite loops
        iteration = 0
        
        #print(f"{'*'*50}\n{'*'*20} LLM CALL  {'*'*20}\n{'*'*50}")
        logger.info("LLM CALL", context={"messages": messages})
        #print(messages)
        response = llm_with_tools.invoke(messages)
        #print(f"{'*'*50}\n{'*'*20} Response  {'*'*20}\n{'*'*50}")
        #print(response)
        logger.info("LLM Response", context={"response": response.content})
        plot_id=None
        final_response=""
        while iteration < max_iterations:
            iteration += 1
            #print(f"{'*'*50}\n{'*'*20} ITERATION {iteration} {'*'*20}\n{'*'*50}")
            logger.info("ITERATION", context={"iteration": iteration})
            if not hasattr(response, 'tool_calls') or not response.tool_calls:
                final_response = response.content[0]['text']
                #print(f"Assistent:\n{response.content[0]['text']}\n\n")
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
                #print(f"{'*'*50}\n{'*'*20} LLM CALL {'*'*20}\n{'*'*50}")
                #print(messages,"\n\n")
                #logger.info("LLM CALL", context={"messages": "".join(str(message) for message in messages)})
                response = llm_with_tools.invoke(messages)
                #logger.info("LLM Response", context={"response": response.content})
                #print(f"{'*'*50}\n{'*'*20} LLM Response{'*'*20}\n{'*'*50}")
                #print("##"*10,response,"\n\n")
            except Exception as e:
                logger.error(f"Error getting LLM response: {str(e)}")
                print("Error in LLM response:",str(e))
                response = response_format(f"Error processing your request after {iteration} iterations: {str(e)}")
                break
        

        if iteration >= max_iterations and (hasattr(response, 'tool_calls') and response.tool_calls):
            logger.warning(f"Reached maximum iterations ({max_iterations}), breaking the loop")
            final_response = response_format(f"I've reached the maximum number of tool calls ({max_iterations}). Here's what I've found so far:\n\n{response.content[0]['text']}")
       
        if hasattr(response, 'content'):
            response_text = response.content[0]['text']  
            cleaned_text = await clean_external_references(response_text)
            final_response = response_format(cleaned_text[1:-1])
        logger.info("FINAL OUTPUT", context={"output": final_response})
        plot_html=  plot_cache[plot_id] if plot_id else None
        plot_cache.pop(plot_id, None)
        
        # Calculate and log the total processing time
        end_time = datetime.datetime.now()
        processing_duration = (end_time - start_time).total_seconds()
        
        logger.info(
            f"Trading query processed successfully - Start: {start_time.isoformat()} | End: {end_time.isoformat()} | Total execution time: {processing_duration:.3f} seconds",
            context={
                "request_id": request_id,
                "processing_duration_seconds": processing_duration,
                "response_type": "trading_response"
            }
        )
        
        return APIResponse(
            statusCode=200,
            headers={"Content-Type": "text/html"},
            body=final_response,
            html=plot_html
        )
    
    except Exception as e:
        import traceback
        traceback_str = traceback.format_exc()
        logger.error(
            f"Error processing query",
            context={"request_id": request_id, "traceback": traceback_str},
            exception=e
        )
        
        error_message = response_format(str(e))
        
        return APIResponse(
            statusCode=500,
            headers={'Content-Type': 'text/html'},
            body=error_message,
            html=None
        )

def response_format(simple_text: str) -> List[Dict[str, Any]]:
    """Create a standardized response body using Pydantic model"""
    return [{
        "type":"text",
        "text":simple_text,
        "annotations":[]
    }]

# Run the FastAPI app
if __name__ == "__main__":
    import uvicorn
    logger.notice("Starting uvicorn server on port 8000")
    uvicorn.run(app, host="0.0.0.0", port=8000) 