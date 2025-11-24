from loguru import logger
from typing import Dict, Any, Callable, List, Optional
from langchain_core.output_parsers import StrOutputParser
from langchain.prompts import PromptTemplate

from domains.utils import get_chat_llm
from domains.recruitment.utils import get_attribute
from domains.stategraph import OverallState, InterviewAnalysisState
from domains.recruitment.summary import create_summarization_graph
from domains.recruitment.prompts import (
    initialize_validation_prompt,
    initialize_grammar_check_prompt
)

# Dictionary to store all available tools
TOOLS_REGISTRY = {}

def register_tool(name: str, description: str = None):
    """
    Decorator to register a tool in the tools registry.
    
    Args:
        name: Name of the tool
        description: Optional description of the tool
    """
    def decorator(func):
        TOOLS_REGISTRY[name] = {
            "function": func,
            "description": description or func.__doc__ or "No description available"
        }
        logger.info(f"Registered tool: {name}")
        return func
    return decorator

def get_available_tools() -> Dict[str, Dict[str, Any]]:
    """
    Get all available tools.
    
    Returns:
        Dictionary of available tools with their descriptions
    """
    return {name: {"description": info["description"]} for name, info in TOOLS_REGISTRY.items()}

def get_tool(name: str) -> Optional[Callable]:
    """
    Get a specific tool by name.
    
    Args:
        name: Name of the tool
        
    Returns:
        The tool function if found, None otherwise
    """
    tool_info = TOOLS_REGISTRY.get(name)
    if tool_info:
        return tool_info["function"]
    logger.warning(f"Tool not found: {name}")
    return None

def get_tools_dict() -> Dict[str, Callable]:
    """
    Get a dictionary of all tool functions.
    
    Returns:
        Dictionary mapping tool names to their functions
    """
    return {name: info["function"] for name, info in TOOLS_REGISTRY.items()}

@register_tool(
    name="summarize_interview_history",
    description="Summarizes the interview history and generates a comprehensive evaluation"
)
async def summarize_interview_history(
        state: InterviewAnalysisState,
) -> InterviewAnalysisState:
    """
    Summarize the interview history and generate a comprehensive evaluation.
    
    Args:
        state: The interview analysis state containing the interview contents
        
    Returns:
        Updated state with the final summary
    """
    interview_contents = state.get("contents", [])

    if not interview_contents:
        logger.warning("No interview contents found for summarization.")
        raise ValueError("No interview contents found for summarization.")

    summary_state = OverallState(
        contents=interview_contents,
        summaries=[],
        collapsed_summaries=[],
        final_summary="",
    )

    contents = summary_state.get("contents", [])
    # Create the summarization graph by calling the function
    summarization_graph = create_summarization_graph()

    try:
        final_state = None
        async for step in summarization_graph.ainvoke(
                {"contents": contents},
                {"recursion_limit": 10},
        ):
            final_state = step

        if final_state is None:
            logger.error("Summarization graph did not return a final state.")
            raise ValueError("Summarization failed: No final state returned.")

        final_summary = get_attribute(final_state, "final_summary")
        state["final_summary"] = final_summary

    except Exception as e:
        logger.error(f"Error running summarization graph: {str(e)}")
        raise

    return state

@register_tool(
    name="grammar_check",
    description="Checks grammar and spelling in the interview summary"
)
def grammar_check(
        state: InterviewAnalysisState,
) -> str:
    """
    Check grammar and spelling in the interview summary.
    
    Args:
        state: The interview analysis state containing the final summary
        
    Returns:
        String containing grammar and spelling analysis
    """
    final_summary = get_attribute(state, "final_summary")

    try:
        llm = get_chat_llm()
        grammar_prompt = initialize_grammar_check_prompt()
        
        chain = grammar_prompt | llm | StrOutputParser()
        response = chain.invoke({"text": final_summary})

        if hasattr(response, 'content'):
            result = response.content.strip()
        else:
            result = str(response).strip()
        logger.success("Grammar check completed.")
        return result
    except Exception as e:
        logger.error(f"Grammar checker failed: {e}")
        raise

@register_tool(
    name="validation_tool",
    description="Validates the quality and completeness of the assessment report"
)
def validation_tool(
        state: InterviewAnalysisState
) -> InterviewAnalysisState:
    """
    Validate the quality and completeness of the assessment report.
    
    Args:
        state: The interview analysis state containing the final summary
        
    Returns:
        Updated state with the validation result
    """
    try:
        logger.info("Checking assessment report quality and completeness...")
        validation_prompt = initialize_validation_prompt()
        llm = get_chat_llm()
        
        final_summary = get_attribute(state, "final_summary", "")
        
        chain = validation_prompt | llm | StrOutputParser()
        response = chain.invoke({"summary": final_summary})

        if hasattr(response, 'content'):
            validation_result = response.content.strip()
        else:
            validation_result = str(response).strip()
            
        # Store validation result in state
        state["validation_result"] = validation_result
        logger.success("Validation completed successfully.")
        
        return state

    except Exception as e:
        logger.error(f"Validation failed: {e}")
        raise e

@register_tool(
    name="technical_accuracy_check",
    description="Evaluates the technical accuracy of the candidate's responses"
)
def technical_accuracy_check(
        state: InterviewAnalysisState
) -> Dict[str, Any]:
    """
    Evaluate the technical accuracy of the candidate's responses.
    
    Args:
        state: The interview analysis state containing the interview contents
        
    Returns:
        Dictionary with technical accuracy scores and analysis
    """
    try:
        logger.info("Evaluating technical accuracy of responses...")
        llm = get_chat_llm()
        
        # Extract technical content from the interview
        contents = state.get("contents", [])
        technical_content = "\n".join(contents)
        
        # Create a prompt for technical evaluation
        prompt = PromptTemplate(
            template="""
            Analyze the following technical interview responses for accuracy and correctness:
            
            {content}
            
            Provide a detailed evaluation of the technical accuracy, including:
            1. Overall technical accuracy score (1-10)
            2. Identification of any technical misconceptions or errors
            3. Assessment of the depth of technical knowledge demonstrated
            4. Evaluation of problem-solving approach
            
            Format your response as a JSON object with the following structure:
            {
                "technical_accuracy_score": int,
                "misconceptions": [list of strings],
                "knowledge_depth_score": int,
                "problem_solving_score": int,
                "overall_assessment": string
            }
            """,
            input_variables=["content"]
        )
        
        chain = prompt | llm | StrOutputParser()
        response = chain.invoke({"content": technical_content})
        
        # Parse the response as JSON
        import json
        try:
            result = json.loads(response)
        except json.JSONDecodeError:
            # If the response is not valid JSON, return a structured result anyway
            result = {
                "technical_accuracy_score": 5,
                "misconceptions": ["Unable to parse response"],
                "knowledge_depth_score": 5,
                "problem_solving_score": 5,
                "overall_assessment": "Unable to properly evaluate technical accuracy due to parsing error."
            }
        
        logger.success("Technical accuracy evaluation completed.")
        return result
    except Exception as e:
        logger.error(f"Technical accuracy evaluation failed: {e}")
        return {
            "technical_accuracy_score": 0,
            "misconceptions": [f"Error during evaluation: {str(e)}"],
            "knowledge_depth_score": 0,
            "problem_solving_score": 0,
            "overall_assessment": f"Evaluation failed due to error: {str(e)}"
        }

# Example of how to add a new tool dynamically
def add_custom_tool(name: str, function: Callable, description: str = None):
    """
    Add a custom tool to the registry.
    
    Args:
        name: Name of the tool
        function: The tool function
        description: Optional description of the tool
    """
    TOOLS_REGISTRY[name] = {
        "function": function,
        "description": description or function.__doc__ or "No description available"
    }
    logger.info(f"Added custom tool: {name}")

# Initialize tools when this module is imported
def initialize_tools():
    """Initialize all tools and ensure they're registered."""
    # The tools are automatically registered via the @register_tool decorator
    # This function is mainly for explicit initialization if needed
    logger.info(f"Initialized {len(TOOLS_REGISTRY)} tools: {', '.join(TOOLS_REGISTRY.keys())}")
    return get_tools_dict()

# Call initialize_tools to register all tools when the module is imported
tools_dict = initialize_tools()