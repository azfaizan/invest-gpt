import os
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
from  src.tools import financial_api
from src.statics import MODEL_NAME
from src.chains import create_crypto_agent
import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("crypto_advisor_api.log")
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Check required environment variables
required_vars = ["OPENAI_API_KEY"]
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
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
#gpt-4o-search-preview
agent = create_crypto_agent(
    verbose=True,
    model_name=MODEL_NAME,
    temperature=0,
    streaming=False
)

# Define request and response models
class QueryRequest(BaseModel):
    """Model for query requests"""
    query: str

class QueryResponse(BaseModel):
    """Model for query responses"""
    response: str
    conversation_id: str
    contains_visualization: bool = False
    visualization_html: Optional[str] = None

# Routes
@app.get("/health")
async def health():
    """Process a query and return a response"""
    return str(datetime.datetime.now())
        


@app.post("/")
async def process_query(request: QueryRequest):
    """Process a query and return a response"""
    try:
        # Process the query with the agent
        print("*"*10,request.query)
        response = agent.invoke({"input": request.query, "chat_history": []})
        print("*"*10,"FINAL RESPONSE BY LLM *******",response)
        
        # Extract the response content
        if isinstance(response, dict):
            output = response.get("output", "Sorry, I couldn't process your request.")
        else:
            output = str(response)
            
        if "#~#plot#~#" in output:
            output = output.replace("#~#plot#~#", financial_api.plot if financial_api.plot else "")
        if "#~#plot#~#" not in output and financial_api.plot is not None:
            output = output + financial_api.plot
        financial_api.plot = None    
        return  {
            'statusCode': 200,
            'headers': {'Content-Type': 'text/html'},
            'body': output
        }
    
    except Exception as e:
        logger.exception("Error processing query")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'text/html'},
            'body': f"<p>Error processing your request please try again later</p>"
        }

# Run the FastAPI app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 