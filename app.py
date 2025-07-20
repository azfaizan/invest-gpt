import os,json,datetime
from typing import Any, Dict, List
import uuid
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, Request,HTTPException
from fastapi.security import HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from src.utils.logger_factory import LoggerFactory
from src.statics import MODEL_NAME, STATICS, HTML_TEMPLATE
from src.models import ResponseBody, APIResponse,QueryRequest
from src.utils.api_helpers import initialize_chat_model,verify_api_key, is_trading_related_query, clean_external_references
from src.utils import api_helpers
from src.tools import financial_api
import plotly,asyncio
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
import time

plot_cache = {}

async def dynamic_kafka_call(request_topic: str, response_topic: str, request_data: dict, 
                           bootstrap_servers: str = 'localhost:9092', timeout: int = 10):
    """
    Perform a dynamic async Kafka call with separate request and response topics.
    
    This function creates fresh producer and consumer instances for each call, making it
    completely stateless and allowing for different topics per request.
    
    Args:
        request_topic (str): The Kafka topic to send the request to
        response_topic (str): The Kafka topic to listen for responses on
        request_data (dict): The data to send in the request
        bootstrap_servers (str): Kafka bootstrap servers (default: 'localhost:9092')
        timeout (int): Maximum time to wait for a response in seconds
    
    Returns:
        dict: The response data from the Kafka response topic
    
    Raises:
        TimeoutError: If no response is received within the timeout period
        Exception: If a Kafka error occurs
        
    Why Consumer Groups Matter:
    - Consumer groups ensure message delivery guarantees and load balancing
    - Each consumer group gets a copy of every message (broadcast behavior)
    - Within a group, only one consumer processes each message (load balancing)
    - Using unique group IDs ensures we get our own copy of responses
    - Without groups, multiple consumers might compete for the same messages
    """
    
    # Generate a unique correlation ID for this specific request
    correlation_id = str(uuid.uuid4())
    
    # Create unique consumer group ID to avoid conflicts with other instances
    consumer_group_id = f'response-consumer-{correlation_id}'
    
    # Initialize producer for sending requests
    producer = AIOKafkaProducer(
        bootstrap_servers=bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        key_serializer=lambda k: k.encode('utf-8') if isinstance(k, str) else k
    )
    
    # Initialize consumer for receiving responses
    # Using 'earliest' to catch responses that might arrive before we start polling
    consumer = AIOKafkaConsumer(
        response_topic,
        bootstrap_servers=bootstrap_servers,
        group_id=consumer_group_id,  # Unique group ensures we get our messages
        auto_offset_reset='latest',  # Start from latest to avoid old messages
        value_deserializer=lambda v: json.loads(v.decode('utf-8')),
        key_deserializer=lambda k: k.decode('utf-8') if k else None,
        consumer_timeout_ms=1000  # Poll timeout
    )
    
    try:
        # Start both producer and consumer
        await producer.start()
        await consumer.start()
        
        print(f"Kafka connections established for correlation_id: {correlation_id}")
        
        # Prepare request data with correlation info
        request_payload = {
            **request_data,
            'correlation_id': correlation_id,
            'response_topic': response_topic,
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        # Send the request message
        await producer.send_and_wait(
            topic=request_topic,
            key=correlation_id,
            value=request_payload
        )
        
        print(f"Request sent to topic '{request_topic}' with correlation_id: {correlation_id}")
        
        # Poll for response with timeout
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Get messages from the response topic
                message_batch = await consumer.getmany(timeout_ms=1000)
                
                for topic_partition, messages in message_batch.items():
                    for message in messages:
                        message_correlation_id = message.key
                        response_data = message.value
                        
                        print(f"Received message with correlation_id: {message_correlation_id}")
                        
                        # Check if this response matches our request
                        if message_correlation_id == correlation_id:
                            print(f"Found matching response for correlation_id: {correlation_id}")
                            return response_data
                        else:
                            print(f"Ignoring message with different correlation_id: {message_correlation_id}")
                            
            except Exception as poll_error:
                print(f"Error during polling: {poll_error}")
                continue
        
        # If we reach here, we've timed out
        raise TimeoutError(f"No response received within {timeout} seconds for correlation_id: {correlation_id}")
        
    except Exception as e:
        print(f"Error in Kafka communication: {e}")
        raise e
        
    finally:
        # Always cleanup resources
        try:
            await producer.stop()
            await consumer.stop()
            print(f"Kafka connections closed for correlation_id: {correlation_id}")
        except Exception as cleanup_error:
            print(f"Error during cleanup: {cleanup_error}")

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


logger = LoggerFactory.create_protocol_logger(service_name="invest-gpt", is_console_command=True)
logger.notice("Application starting up, Protocol Logger initialized")

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
                width=None, height=None, **kwargs):
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
        plot_html = plotly.io.to_html(plot, include_plotlyjs='cdn',config={'responsive': True, 'scrollZoom': False})
        plot_id = str(uuid.uuid4())
        plot_html = HTML_TEMPLATE.replace('{plotly_html}', plot_html)
        plot_cache[plot_id] = plot_html
        financial_api.plot = plot_html
        return {
            "message": "Plot created successfully",
            "plot_id": plot_id
        }
    except Exception as e:
        logger.error(
            f"Error creating plot",
            context={
                "trace_id": str(uuid.uuid4()),
                "is_console_command": True
            },
            exception=e,
            extra=json.dumps({
                "error": str(e), 
                "plot_type": plot_type, 
                "title": title
            })
        )
        return {
            "message": f"Error creating plot: {str(e)}",
            "error": str(e)
        }

def create_subplots(data, plot_types, rows=1, cols=2, subplot_titles=None, column_widths=None, 
                   title="Dynamic Subplots", height=None, width=None, barmode='group', 
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
        logger.error(
            error_message,
            context={
                "trace_id": str(uuid.uuid4()),
                "is_console_command": True
            }
        )
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
        plot_html = fig.to_html(include_plotlyjs='cdn',config={'responsive': True, 'scrollZoom': False})
        plot_id = str(uuid.uuid4())
        plot_html = HTML_TEMPLATE.replace('{plotly_html}', plot_html)
        plot_cache[plot_id] = plot_html
        
        return {
            "message": "Subplots created successfully",
            "plot_id": plot_id
        }
    except Exception as e:
        logger.error(
            f"Error creating subplots",
            context={
                "trace_id": str(uuid.uuid4()),
                "is_console_command": True
            },
            exception=e,
            extra=json.dumps({
                "error": str(e), 
                "plot_types": plot_types, 
                "title": title
            })
        )
        return {
            "message": f"Error creating subplots: {str(e)}",
            "error": str(e)
        }

def synchronous_kafka_call(request_topic, response_topic, request_data, timeout=10):
    """
    Perform a synchronous Kafka call by sending a request and waiting for a response.
    
    Args:
        request_topic (str): The Kafka topic to send the request to.
        response_topic (str): The Kafka topic to receive the response from.
        request_data (dict): The data to send in the request.
        timeout (int): Maximum time to wait for a response in seconds.
    
    Returns:
        dict: The response data from the Kafka response topic.
    
    Raises:
        TimeoutError: If no response is received within the timeout period.
        Exception: If a Kafka consumer error occurs.
    """
    # Generate a unique correlation ID for this request
    correlation_id = str(uuid.uuid4())
    
    # Configure and create the producer
    producer = Producer({'bootstrap.servers': 'localhost:9092'})
    
    # Configure and create the consumer
    consumer = Consumer({
        'bootstrap.servers': 'localhost:9092',
        'group.id': f'response-group',  # Unique group per request
        'auto.offset.reset': 'latest'  # Start from messages produced after subscription
    })
    
    # Subscribe to the response topic before sending the request
    consumer.subscribe([response_topic])
    
    # Send the request with the correlation ID as the key
    producer.produce(
        topic=request_topic,
        key=correlation_id.encode('utf-8'),
        value=json.dumps(request_data).encode('utf-8')
    )
    producer.flush()  # Ensure the message is sent
    
    # Poll for the response
    start_time = time.time()
    while True:
        if time.time() - start_time > timeout:
            consumer.close()
            raise TimeoutError("Response timeout exceeded")
        
        msg = consumer.poll(timeout=1.0)
        if msg is None:
            continue
        if msg.error():
            consumer.close()
            raise Exception(f"Kafka consumer error: {msg.error()}")
        
        # Check if the message key matches the correlation ID
        print("msg.key().decode('utf-8')",msg.key().decode('utf-8'))
        if msg.key().decode('utf-8') == correlation_id:
            response = json.loads(msg.value().decode('utf-8'))
            consumer.close()
            return response

@app.post("/portfolio")
async def get_portfolio(user_id: str):
    """Test endpoint to send a message to Kafka and get Hello World response"""
    try:
        print(f"🚀 Testing Kafka with user_id: {user_id}")
        
        # Use the async dynamic_kafka_call with correct topics
        response = await dynamic_kafka_call(
            request_topic="request-topic",
            response_topic="request-topic.replay",
            request_data={"accountId": user_id, "message": "Hello from FastAPI!"},
            timeout=15
        )
        
        print("✅ Response received:", response)
        
        return {
            "status": "success",
            "user_id": user_id,
            "kafka_response": response,
            "message": "Successfully communicated with Kafka service"
        }
        
    except TimeoutError as e:
        print(f"⏰ Timeout error: {e}")
        return {
            "status": "error",
            "error_type": "timeout",
            "message": f"Kafka request timed out: {str(e)}",
            "user_id": user_id
        }
    except Exception as e:
        print(f"💥 Unexpected error: {e}")
        return {
            "status": "error", 
            "error_type": "general",
            "message": f"Kafka communication failed: {str(e)}",
            "user_id": user_id
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
async def test_auth(request: Request, authenticated: bool = Depends(verify_api_key)) -> APIResponse:
    """Test endpoint to verify API key authentication"""
    # Create a request-specific logger
    request_logger = LoggerFactory.create_protocol_logger(
        service_name="invest-gpt",
        request_path=str(request.url.path),
        request_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    request_logger.info("API key authentication test", context={"authenticated": authenticated})
    
    return APIResponse (
        statusCode=200,
        headers={"Content-Type": "text/html"},
        body=response_format("API key is valid"),
        html=None
    )

@app.get("/health")
async def health(request: Request):
    """Process a query and return a response"""
    current_time = datetime.datetime.now()
    return str(current_time)
        
@app.post("/query", response_model=APIResponse)
async def process_query(request_data: QueryRequest, request: Request, authenticated: bool = Depends(verify_api_key)) -> APIResponse:
    """Process a query and return a response"""
    
    # Start timing the request
    start_time = datetime.datetime.now()
    request_id = str(start_time.timestamp())
    
    # Create a request trace ID that will be used throughout this request
    request_trace_id = str(uuid.uuid4())
    
    # Create a request-specific logger with request context
    request_logger = LoggerFactory.create_protocol_logger(
        service_name="invest-gpt",
        request_path=str(request.url.path),
        request_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    
    try:
        request_logger.info(
            f"Processing query",
            context={
                "trace_id": str(uuid.uuid4())
            },
            extra=json.dumps({
                "request_trace_id": request_trace_id,
                "request_id": request_id,
                "query": request_data.query
            })
        )
        
        if not await is_trading_related_query(request_data.query):
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
            {"role": "user", "content": request_data.query}
        ]
        
        request_logger.info(
            "Processing query", 
            context={
                "trace_id": str(uuid.uuid4())
            },
            extra=json.dumps({
                "request_trace_id": request_trace_id,
                "query": request_data.query
            })
        )
        
        # Initialize variables for the tool calling loop
        max_iterations = 3  # Prevent infinite loops
        iteration = 0
        
        request_logger.info(
            "LLM CALL", 
            context={
                "trace_id": str(uuid.uuid4())
            },
            extra=json.dumps({
                "request_trace_id": request_trace_id,
                "messages": messages
            })
        )
        
        response = llm_with_tools.invoke(messages)
        
        request_logger.info(
            "LLM Response", 
            context={
                "trace_id": str(uuid.uuid4())
            },
            extra=json.dumps({
                "request_trace_id": request_trace_id,
                "response": response.content
            })
        )
        
        plot_id=None
        final_response=""
        while iteration < max_iterations:
            iteration += 1
            
            request_logger.info(
                "ITERATION", 
                context={
                    "trace_id": str(uuid.uuid4())
                },
                extra=json.dumps({
                    "request_trace_id": request_trace_id,
                    "iteration": iteration
                })
            )
            
            if not hasattr(response, 'tool_calls') or not response.tool_calls:
                final_response = response.content[0]['text']
                request_logger.info(
                    "No tool calls in response, using as final output",
                    context={
                        "trace_id": str(uuid.uuid4())
                    },
                    extra=json.dumps({
                        "request_trace_id": request_trace_id
                    })
                )
                break
            
            messages.append(response)
            
            tool_outputs = []
            for tool_call in response.tool_calls:
                try:
                    function_name = tool_call['name']
                    
                    if function_name not in available_functions:
                        request_logger.error(
                            f"Invalid function name: {function_name}",
                            context={
                                "trace_id": str(uuid.uuid4())
                            },
                            extra=json.dumps({
                                "request_trace_id": request_trace_id
                            })
                        )
                        continue

                    try:
                        function_args = json.loads(tool_call['args']) if isinstance(tool_call['args'], str) else tool_call['args']
                    except json.JSONDecodeError as e:
                        request_logger.error(
                            f"Invalid JSON in function args: {str(e)}", 
                            context={
                                "trace_id": str(uuid.uuid4())
                            },
                            exception=e,
                            extra=json.dumps({
                                "request_trace_id": request_trace_id
                            })
                        )
                        continue
           
                    function_to_call = available_functions[function_name]
                    function_response = function_to_call(**function_args)
                    if function_response.get('plot_id'):
                        plot_id=function_response['plot_id']
                        function_response="plot has been created and saved in cache, and will be returned with the final response, you should now just answer the user query."
                        print("\n\nHas plot id**\n\n")
                    tool_outputs.append({
                        "tool_call_id": tool_call['id'],
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps(function_response)
                    })
                    
                except Exception as e:
                    request_logger.error(
                        f"Error processing tool call: {str(e)}", 
                        context={
                            "trace_id": str(uuid.uuid4())
                        },
                        exception=e,
                        extra=json.dumps({
                            "request_trace_id": request_trace_id
                        })
                    )

            messages.extend(tool_outputs)
            try:
                response = llm_with_tools.invoke(messages)
            except Exception as e:
                request_logger.error(
                    f"Error getting LLM response: {str(e)}", 
                    context={
                        "trace_id": str(uuid.uuid4())
                    },
                    exception=e,
                    extra=json.dumps({
                        "request_trace_id": request_trace_id
                    })
                )
                print("Error in LLM response:",str(e))
                response = response_format(f"Error processing your request after {iteration} iterations: {str(e)}")
                break
        

        if iteration >= max_iterations and (hasattr(response, 'tool_calls') and response.tool_calls):
            request_logger.warning(
                f"Reached maximum iterations ({max_iterations}), breaking the loop",
                context={
                    "trace_id": str(uuid.uuid4())
                },
                extra=json.dumps({
                    "request_trace_id": request_trace_id
                })
            )
            final_response = response_format(f"I've reached the maximum number of tool calls ({max_iterations}). Here's what I've found so far:\n\n{response.content[0]['text']}")
       
        if hasattr(response, 'content'):
            response_text = response.content[0]['text']  
            cleaned_text = await clean_external_references(response_text)
            final_response = response_format(cleaned_text[1:-1])
            
        request_logger.info(
            "FINAL OUTPUT", 
            context={
                "trace_id": str(uuid.uuid4())
            },
            extra=json.dumps({
                "request_trace_id": request_trace_id,
                "output": final_response
            })
        )
        
        plot_html=  plot_cache[plot_id] if plot_id else None
        plot_cache.pop(plot_id, None)
        
        # Calculate and log the total processing time
        end_time = datetime.datetime.now()
        processing_duration = (end_time - start_time).total_seconds()
        
        request_logger.info(
            f"Trading query processed successfully - Start: {start_time.isoformat()} | End: {end_time.isoformat()} | Total execution time: {processing_duration:.3f} seconds",
            context={
                "trace_id": str(uuid.uuid4())
            },
            extra=json.dumps({
                "request_trace_id": request_trace_id,
                "request_id": request_id,
                "processing_duration_seconds": processing_duration,
                "response_type": "trading_response"
            })
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
        request_logger.error(
            f"Error processing query",
            context={
                "trace_id": str(uuid.uuid4())
            },
            exception=e,
            extra=json.dumps({
                "request_trace_id": request_trace_id,
                "request_id": request_id,
                "traceback": traceback_str
            })
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

