from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class QueryRequest(BaseModel):
    """Model for query requests"""
    query: str

class ResponseBody(BaseModel):
    """Model for response body structure"""
    type: str = "text"
    text: str
    annotations: List[Dict[str, Any]] = []

class APIResponse(BaseModel):
    """Model for complete API response structure"""
    statusCode: int
    headers: Dict[str, str]
    body: List[Dict[str, Any]] = []
    html: Optional[str] = None
