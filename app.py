import os
import datetime
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
from src.tools import financial_api
from src.statics import MODEL_NAME
from src.chains import create_crypto_agent

# Load environment variables
load_dotenv()

# Setup logging - use regular logging as fallback
logger = logging.getLogger("invest-gpt")
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

# Try to use Axiom logging if available
try:
    from src.utils.axiom_logger import create_logger
    
    # Get Axiom configuration from environment variables
    axiom_token = os.getenv("AXIOM_TOKEN")
    axiom_org_id = os.getenv("AXIOM_ORG_ID")
    axiom_dataset = os.getenv("AXIOM_DATASET", "invest-gpt-logs")
    
    if not axiom_token:
        logger.warning("AXIOM_TOKEN not found in environment variables")
    
    if not axiom_org_id:
        logger.warning("AXIOM_ORG_ID not found in environment variables")
    
    # Create logger with explicit token and org_id
    axiom_logger = create_logger(
        name="invest-gpt",
        dataset=axiom_dataset,
        token=axiom_token,
        org_id=axiom_org_id,
        additional_fields={"app_version": "1.0.0"}
    )
    
    # If successful, replace the default logger
    logger = axiom_logger
    logger.info(f"Axiom logging initialized successfully with dataset: {axiom_dataset}")
except Exception as e:
    logger.warning(f"Failed to initialize Axiom logging, using standard logging: {str(e)}")

# Log app startup
logger.info("Application starting up")

# Check required environment variables
required_vars = ["OPENAI_API_KEY"]
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
    raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")

# Initialize FastAPI app
app = FastAPI(
    title="CryptoAdvisor API",
    description="LangChain-based API for cryptocurrency investment information and visualization",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize agent
agent = create_crypto_agent(
    verbose=True,
    model_name=MODEL_NAME,
    temperature=0,
    streaming=False
)

# Define request model
class QueryRequest(BaseModel):
    """Model for query requests"""
    query: str

# Routes
@app.get("/health")
async def health():
    """Process a query and return a response"""
    return str(datetime.datetime.now())
        
@app.post("/")
async def process_query(request: QueryRequest):
    """Process a query and return a response"""
    try:
        # Log incoming query
        logger.info(f"Processing query: {request.query}")
        
        # Process the query with the agent
        response = agent.invoke({"input": request.query, "chat_history": []})
        logger.info("Query processed successfully")
        
        # Extract the response content
        if isinstance(response, dict):
            output = response.get("output", "Sorry, I couldn't process your request.")
        else:
            output = str(response)
            
        # Handle visualization content
        if "#~#plot#~#" in output:
            output = output.replace("#~#plot#~#", financial_api.plot if financial_api.plot else "")
        if "#~#plot#~#" not in output and financial_api.plot is not None:
            output = output + financial_api.plot
        financial_api.plot = None    
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'text/html'},
            'body': output
        }
    
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'text/html'},
            'body': f"<p>Error processing your request please try again later</p>"
        }

# Run the FastAPI app
if __name__ == "__main__":
    import uvicorn
    logger.info("Starting uvicorn server on port 8000")
    uvicorn.run(app, host="0.0.0.0", port=8000) 