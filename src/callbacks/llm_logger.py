import logging
import json
from typing import Any, Dict, List, Optional, Union
from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import LLMResult, AgentAction, AgentFinish

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("llm_interactions.log"),
        logging.StreamHandler()
    ]
)

class LLMLogger(BaseCallbackHandler):
    """Callback Handler for logging LLM and agent interactions."""
    
    def __init__(self, log_colors=True):
        """Initialize the callback handler."""
        super().__init__()
        self.log_colors = log_colors
        self.interaction_count = 0
    
    def _format_json(self, obj: Any) -> str:
        """Format an object as a JSON string."""
        try:
            return json.dumps(obj, indent=2, ensure_ascii=False)
        except:
            return str(obj)
    
    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        """Log when LLM starts processing."""
        self.interaction_count += 1
        model_name = serialized.get("name", "unknown_model")
        logger.info(f"======== LLM CALL #{self.interaction_count} ({model_name}) ========")
        for i, prompt in enumerate(prompts):
            logger.info(f"PROMPT #{i+1}:\n{prompt}\n")
    
    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Log when LLM ends processing."""
        logger.info(f"------- LLM RESPONSE #{self.interaction_count} -------")
        for i, generation in enumerate(response.generations):
            for j, g in enumerate(generation):
                logger.info(f"RESPONSE #{i+1}.{j+1}:\n{g.text}\n")
                if g.message and hasattr(g.message, "additional_kwargs") and g.message.additional_kwargs:
                    logger.info(f"ADDITIONAL INFO:\n{self._format_json(g.message.additional_kwargs)}\n")
        logger.info(f"TOTAL TOKENS: {response.llm_output.get('token_usage', {}).get('total_tokens', 'unknown')}")
        logger.info("="*50 + "\n")
    
    def on_llm_error(self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any) -> None:
        """Log when LLM errors."""
        logger.error(f"LLM ERROR: {error}")
    
    def on_chain_start(
        self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any
    ) -> None:
        """Log when chain starts."""
        chain_type = serialized.get("name", "unknown_chain")
        logger.info(f">> CHAIN START: {chain_type}")
        filtered_inputs = {k: v for k, v in inputs.items() if k != "input_documents"}
        logger.info(f"INPUTS: {self._format_json(filtered_inputs)}\n")
    
    def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> None:
        """Log when chain ends."""
        filtered_outputs = {k: v for k, v in outputs.items() if k != "output_documents"}
        logger.info(f"OUTPUTS: {self._format_json(filtered_outputs)}")
        logger.info("<< CHAIN END\n")
    
    def on_chain_error(self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any) -> None:
        """Log when chain errors."""
        logger.error(f"CHAIN ERROR: {error}")
    
    def on_tool_start(
        self, serialized: Dict[str, Any], input_str: str, **kwargs: Any
    ) -> None:
        """Log when tool starts."""
        tool_name = serialized.get("name", "unknown_tool")
        logger.info(f">> TOOL START: {tool_name}")
        logger.info(f"TOOL INPUT: {input_str}\n")
    
    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """Log when tool ends."""
        # Truncate very long outputs
        if len(output) > 1000:
            output = output[:500] + "...[TRUNCATED]..." + output[-500:]
        logger.info(f"TOOL OUTPUT: {output}")
        logger.info("<< TOOL END\n")
    
    def on_tool_error(self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any) -> None:
        """Log when tool errors."""
        logger.error(f"TOOL ERROR: {error}")
    
    def on_agent_action(self, action: AgentAction, **kwargs: Any) -> Any:
        """Log agent actions."""
        logger.info(f">> AGENT ACTION: {action.tool}")
        logger.info(f"ACTION INPUT: {action.tool_input}")
        logger.info(f"OBSERVATION: {action.log}")
    
    def on_agent_finish(self, finish: AgentFinish, **kwargs: Any) -> None:
        """Log agent end."""
        logger.info(f"AGENT FINISH: {finish.return_values}")
        logger.info(f"FINISH LOG: {finish.log}") 