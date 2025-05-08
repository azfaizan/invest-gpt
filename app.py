import os
import datetime
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.utils.logger_factory import LoggerFactory
from src.tools import financial_api
from src.statics import MODEL_NAME
import json

load_dotenv()

logger = LoggerFactory.create_logger(service_name="invest-gpt")
logger.notice("Application starting up, Logger initialized")


app = FastAPI(
    title="CryptoAdvisor API",
    description="LangChain-based API for cryptocurrency investment information and visualization",
    version="1.0.0"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


required_vars = ["OPENAI_API_KEY"]
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
    return financial_api.portfolio_json()

@app.get("/health")
async def health():
    """Process a query and return a response"""
    current_time = datetime.datetime.now()
    logger.debug("Health check", context={"timestamp": current_time.isoformat()})
    return str(current_time)
        
@app.post("/")
async def process_query(request: QueryRequest):
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
        
        # Set up available functions
        available_functions = {
            "portfolio_get_data": portfolio_get_data
        }
        
        # Bind tools
        llm_with_tools = llm.bind_tools([web_search_tool, portfolio_tool])
        
        # Create conversation
        messages = [
            {"role": "system", "content": "You are a helpful assistant that can search the web and retrieve portfolio data. For queries about the user's investments, holdings, or portfolio, use the portfolio_get_data function."},
            {"role": "user", "content": request.query}
        ]
        
        print("*******************", "Processing query:", request.query)
        
        # First model call to get response or tool calls
        response = llm_with_tools.invoke(messages)
        print("*******************", "Initial response:", response)
        
        # Check for tool calls
        if hasattr(response, 'tool_calls') and response.tool_calls:
            print("*******************", "Found tool calls:", response.tool_calls)
            tool_outputs = []
            
            for tool_call in response.tool_calls:
                print("*******************", "Tool call:", tool_call)
                function_name = tool_call['name']
                function_args = tool_call['args']
                print("*******************", "Function name:", function_name)
                if function_name in available_functions:
                    function_to_call = available_functions[function_name]
                    print(f"*******************", f"Calling {function_name} with args {function_args}")
                    function_response = function_to_call(**function_args)
                    
                    tool_outputs.append({
                        "tool_call_id": tool_call['id'],
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps(function_response)
                    })
            
            # Add the assistant's message with the tool calls
            messages.append(response)
            
            # Add all tool outputs
            messages.extend(tool_outputs)
            
            # Get a second response that incorporates the tool outputs
            second_response = llm_with_tools.invoke(messages)
            print("*******************", "Second response:", second_response)
            
            output = second_response.content
        else:
            # If no tool calls, just use the initial response
            output = response.content
        
        print("*******************", "Final output:", output)
            
        # Handle visualization content
        if "#~#plot#~#" in output:
            output = output.replace("#~#plot#~#", financial_api.plot if financial_api.plot else "")
        if "#~#plot#~#" not in output and financial_api.plot is not None:
            output = output + financial_api.plot
        financial_api.plot = None
        
        logger.debug(
            "Returning HTML response",
            context={"response": output, "content_type": "text/html"}
        )
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'text/html'},
            'body': output
        }
    
    except Exception as e:
        import traceback
        traceback_str = traceback.format_exc()
        logger.error(
            f"Error processing query",
            context={"request_id": request_id, "traceback": traceback_str},
            exception=e
        )
        raise e
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'text/html'},
            'body': f"<p>Error processing your request: {str(e)}</p>"
        }

# Run the FastAPI app
if __name__ == "__main__":
    import uvicorn
    logger.notice("Starting uvicorn server on port 8000")
    uvicorn.run(app, host="0.0.0.0", port=8000) 