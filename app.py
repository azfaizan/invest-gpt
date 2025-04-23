import os
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
import asyncio
import json

from src.chains import create_crypto_agent

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
agent = create_crypto_agent(
    verbose=False,
    model_name="gpt-4-1106-preview",
    temperature=0.1,
    streaming=False
)

# Define request and response models
class QueryRequest(BaseModel):
    """Model for query requests"""
    query: str
    conversation_id: Optional[str] = None

class QueryResponse(BaseModel):
    """Model for query responses"""
    response: str
    conversation_id: str
    contains_visualization: bool = False
    visualization_html: Optional[str] = None

# Routes
@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Root endpoint with simple HTML doc"""
    return """
    <html>
        <head>
            <title>CryptoAdvisor API</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
                h1 { color: #2c3e50; }
                code { background-color: #f8f8f8; padding: 2px 4px; border-radius: 3px; }
            </style>
        </head>
        <body>
            <h1>CryptoAdvisor API</h1>
            <p>Welcome to the CryptoAdvisor API. This service provides cryptocurrency investment information and visualization.</p>
            <h2>Endpoints</h2>
            <ul>
                <li><code>GET /</code> - This page</li>
                <li><code>POST /query</code> - Send a query to the advisor</li>
                <li><code>GET /docs</code> - API documentation</li>
            </ul>
        </body>
    </html>
    """

@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """Process a query and return a response"""
    try:
        # Process the query with the agent
        print("*"*10,request.query)
        response = agent.invoke({"input": request.query})
        
        # Extract the response content
        output = response.get("output", "Sorry, I couldn't process your request.")
        
        # Check if the response contains HTML visualization
        contains_visualization = "<div" in output and "</div>" in output
        visualization_html = None
        
        if contains_visualization:
            # Extract the HTML content
            start_idx = output.find("<div")
            end_idx = output.rfind("</div>") + 6
            visualization_html = output[start_idx:end_idx]
            
            # Remove the HTML content from the text response
            output = output[:start_idx].strip() + " " + output[end_idx:].strip()
        
        # Generate a conversation ID if not provided
        conversation_id = request.conversation_id or os.urandom(8).hex()
        
        return QueryResponse(
            response=output.strip(),
            conversation_id=conversation_id,
            contains_visualization=contains_visualization,
            visualization_html=visualization_html
        )
    
    except Exception as e:
        logger.exception("Error processing query")
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

# Run the FastAPI app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 