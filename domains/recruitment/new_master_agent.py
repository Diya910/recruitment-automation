from typing import Dict, List, Any, Optional, Literal, TypedDict, Annotated, Union
from loguru import logger
import operator
import json
from enum import Enum
import os
from datetime import datetime

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain.prompts import PromptTemplate
from langgraph.graph import StateGraph, START, END
from langgraph.constants import Send
# No persistence imports needed

from domains.utils import get_chat_llm
from domains.stategraph import InterviewAnalysisState
from domains.recruitment.new_scenario_manager import (
    select_random_scenario,
    get_scenario_by_id,
    is_new_format_scenario,
    get_next_conversation_stage,
    get_scenario_context,
    get_customer_profile,
    get_evaluation_criteria
)
from domains.recruitment.tools import grammar_check, validation_tool, summarize_interview_history

# Define the state for the master agent
class MasterAgentState(TypedDict):
    """State for the master agent orchestrating the conversation process."""
    scenario: Dict[str, Any]
    scenario_id: str
    is_new_format: bool
    current_stage: Optional[str]
    stages_completed: List[str]
    conversation_history: List[Union[HumanMessage, AIMessage, SystemMessage]]
    customer_response: Optional[str]
    context: Dict[str, Any]
    customer_profile: Dict[str, Any]
    evaluation_criteria: Dict[str, str]
    interview_complete: bool
    final_summary: Optional[str]
    grammar_evaluation: Optional[str]
    validation_result: Optional[str]
    tools_to_run: List[str]
    error: Optional[str]
    session_id: Optional[str]
    persistence_path: Optional[str]

# Define the possible actions for the master agent
class MasterAgentAction(str, Enum):
    PROCESS_RESPONSE = "process_response"
    ADVANCE_CONVERSATION = "advance_conversation"
    RUN_EVALUATION = "run_evaluation"
    GENERATE_SUMMARY = "generate_summary"
    COMPLETE_CONVERSATION = "complete_conversation"
    ERROR = "error"

# System prompt for the master agent
MASTER_AGENT_SYSTEM_PROMPT = """
You are an AI customer service agent for {company_name}. Your role is to provide helpful, friendly, and professional assistance to customers.

CONTEXT INFORMATION:
{context}

CUSTOMER PROFILE:
{customer_profile}

CURRENT CONVERSATION STAGE: {current_stage}

GOALS FOR THIS STAGE:
{stage_goals}

CONVERSATION HISTORY:
{conversation_history}

Respond in a natural, conversational manner. Be empathetic, professional, and helpful. Focus on achieving the goals for the current stage of the conversation.
"""

# Create the master agent graph
def create_master_agent_graph():
    """
    Create the LangGraph for the master agent orchestration.
    """
    # Initialize components
    llm = get_chat_llm()
    
    # Define the nodes for the graph
    
    async def initialize_conversation(state: MasterAgentState) -> MasterAgentState:
        """Initialize a new conversation session."""
        try:
            # Start a new conversation with a random scenario, preferring new format
            scenario = select_random_scenario(new_format_only=True)
            if not scenario:
                # Fall back to any scenario if no new format scenarios are available
                scenario = select_random_scenario()
                if not scenario:
                    raise ValueError("No scenarios available")
            
            scenario_id = scenario.get('id', '')
            is_new_format = is_new_format_scenario(scenario)
            
            # Initialize state differently based on scenario format
            if is_new_format:
                # Get the first stage of the conversation
                first_stage_data = get_next_conversation_stage(scenario_id)
                if not first_stage_data:
                    raise ValueError(f"No conversation stages found in scenario {scenario_id}")
                
                current_stage = first_stage_data.get('stage', '')
                stage_goals = first_stage_data.get('agent_goals', [])
                
                # Get context and customer profile
                context = get_scenario_context(scenario_id) or {}
                customer_profile = get_customer_profile(scenario_id) or {}
                evaluation_criteria = get_evaluation_criteria(scenario_id) or {}
                
                # Create system message with context
                company_name = context.get('company_name', 'Our Company')
                system_prompt = MASTER_AGENT_SYSTEM_PROMPT.format(
                    company_name=company_name,
                    context=json.dumps(context, indent=2),
                    customer_profile=json.dumps(customer_profile, indent=2),
                    current_stage=current_stage,
                    stage_goals="\n".join([f"- {goal}" for goal in stage_goals]),
                    conversation_history="No conversation yet."
                )
                
                # Initialize conversation history with system message
                conversation_history = [SystemMessage(content=system_prompt)]
                
                # Add greeting message based on the first stage (usually "greeting")
                greeting_message = f"Hello! Welcome to {company_name}. My name is AI Assistant. How may I help you today?"
                conversation_history.append(AIMessage(content=greeting_message))
                
                # Update state
                state.update({
                    "scenario": scenario,
                    "scenario_id": scenario_id,
                    "is_new_format": True,
                    "current_stage": current_stage,
                    "stages_completed": [],
                    "conversation_history": conversation_history,
                    "customer_response": None,
                    "context": context,
                    "customer_profile": customer_profile,
                    "evaluation_criteria": evaluation_criteria,
                    "interview_complete": False,
                    "final_summary": None,
                    "grammar_evaluation": None,
                    "validation_result": None,
                    "tools_to_run": [],
                    "error": None,
                    "session_id": f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                })
            else:
                # For traditional scenarios, use a simpler initialization
                # This is for backward compatibility
                system_prompt = "You are an HR interviewer conducting a technical assessment interview."
                conversation_history = [SystemMessage(content=system_prompt)]
                
                # Add first question
                first_question = scenario.get('questions', [{}])[0]
                conversation_history.append(
                    AIMessage(content=f"Let's begin the interview. {first_question.get('question', '')}")
                )
                
                # Update state
                state.update({
                    "scenario": scenario,
                    "scenario_id": scenario_id,
                    "is_new_format": False,
                    "current_stage": "question_1",
                    "stages_completed": [],
                    "conversation_history": conversation_history,
                    "customer_response": None,
                    "context": {},
                    "customer_profile": {},
                    "evaluation_criteria": {},
                    "interview_complete": False,
                    "final_summary": None,
                    "grammar_evaluation": None,
                    "validation_result": None,
                    "tools_to_run": [],
                    "error": None,
                    "session_id": f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                })
            
            logger.info(f"Initialized conversation with scenario: {scenario_id}, format: {'new' if is_new_format else 'traditional'}")
            return state
        except Exception as e:
            logger.error(f"Error initializing conversation: {str(e)}")
            state["error"] = f"Failed to initialize conversation: {str(e)}"
            return state
    
    async def process_response(state: MasterAgentState) -> MasterAgentState:
        """Process the customer's response."""
        try:
            if not state.get("customer_response"):
                logger.warning("No customer response to process")
                return state
            
            # Add customer response to conversation history
            state["conversation_history"].append(
                HumanMessage(content=state["customer_response"])
            )
            
            # Clear the customer response
            state["customer_response"] = None
            
            logger.info("Processed customer response")
            return state
        except Exception as e:
            logger.error(f"Error processing response: {str(e)}")
            state["error"] = f"Failed to process response: {str(e)}"
            return state
    
    async def advance_conversation(state: MasterAgentState) -> MasterAgentState:
        """Advance the conversation to the next stage or continue the current stage."""
        try:
            # Handle differently based on scenario format
            if state["is_new_format"]:
                # For new format scenarios, use the conversation flow
                current_stage = state["current_stage"]
                scenario_id = state["scenario_id"]
                
                # Check if we should advance to the next stage
                # This is a simplified decision - in a real system, you might use an LLM to decide
                # based on the conversation history whether the current stage is complete
                
                # For now, we'll advance to the next stage after each customer response
                # Add the current stage to completed stages
                if current_stage not in state["stages_completed"]:
                    state["stages_completed"].append(current_stage)
                
                # Get the next stage
                next_stage_data = get_next_conversation_stage(scenario_id, current_stage)
                
                if next_stage_data:
                    # Move to the next stage
                    next_stage = next_stage_data.get('stage', '')
                    stage_goals = next_stage_data.get('agent_goals', [])
                    
                    # Update the system message with the new stage information
                    company_name = state["context"].get('company_name', 'Our Company')
                    system_prompt = MASTER_AGENT_SYSTEM_PROMPT.format(
                        company_name=company_name,
                        context=json.dumps(state["context"], indent=2),
                        customer_profile=json.dumps(state["customer_profile"], indent=2),
                        current_stage=next_stage,
                        stage_goals="\n".join([f"- {goal}" for goal in stage_goals]),
                        conversation_history="\n".join([
                            f"{'Agent' if isinstance(msg, AIMessage) else 'Customer'}: {msg.content}"
                            for msg in state["conversation_history"]
                            if not isinstance(msg, SystemMessage)
                        ])
                    )
                    
                    # Generate agent response for the new stage
                    agent_prompt = PromptTemplate(
                        template="""
                        {system_prompt}
                        
                        Based on the conversation history and the current stage, provide a natural, helpful response to advance the conversation.
                        Focus on achieving the goals for the current stage: {current_stage}
                        
                        Your response should be conversational and human-like. Do not use phrases like "As an AI" or "As a language model".
                        """,
                        input_variables=["system_prompt", "current_stage"]
                    )
                    
                    agent_chain = agent_prompt | llm | StrOutputParser()
                    agent_response = await agent_chain.ainvoke({
                        "system_prompt": system_prompt,
                        "current_stage": next_stage
                    })
                    
                    # Add agent response to conversation history
                    state["conversation_history"].append(
                        AIMessage(content=agent_response)
                    )
                    
                    # Update current stage
                    state["current_stage"] = next_stage
                    
                    logger.info(f"Advanced conversation to stage: {next_stage}")
                else:
                    # No more stages, complete the conversation
                    state["interview_complete"] = True
                    
                    # Add closing message
                    closing_message = "Thank you for your time today. Is there anything else I can help you with?"
                    state["conversation_history"].append(
                        AIMessage(content=closing_message)
                    )
                    
                    logger.info("Conversation complete, no more stages")
            else:
                # For traditional scenarios, use a simpler approach
                # This is for backward compatibility
                
                # Generate a response based on the conversation history
                conversation_history_text = "\n".join([
                    f"{'Interviewer' if isinstance(msg, AIMessage) else 'Candidate'}: {msg.content}"
                    for msg in state["conversation_history"]
                    if not isinstance(msg, SystemMessage)
                ])
                
                agent_prompt = PromptTemplate(
                    template="""
                    You are an HR interviewer conducting a technical assessment interview.
                    
                    CONVERSATION HISTORY:
                    {conversation_history}
                    
                    Based on the conversation history, provide a natural, helpful response to continue the interview.
                    Your response should be conversational and professional.
                    """,
                    input_variables=["conversation_history"]
                )
                
                agent_chain = agent_prompt | llm | StrOutputParser()
                agent_response = await agent_chain.ainvoke({
                    "conversation_history": conversation_history_text
                })
                
                # Add agent response to conversation history
                state["conversation_history"].append(
                    AIMessage(content=agent_response)
                )
                
                # Check if we've reached the end of the questions
                # This is a simplified approach - in a real system, you might have more complex logic
                questions = state["scenario"].get("questions", [])
                if len(state["conversation_history"]) / 2 > len(questions):
                    # We've gone through all questions, complete the interview
                    state["interview_complete"] = True
                    
                    # Add closing message
                    closing_message = "Thank you for completing this technical interview. We'll now evaluate your responses."
                    state["conversation_history"].append(
                        AIMessage(content=closing_message)
                    )
                    
                    logger.info("Interview complete, all questions asked")
                else:
                    # Update current stage
                    state["current_stage"] = f"question_{len(state['stages_completed']) + 1}"
                    state["stages_completed"].append(state["current_stage"])
                    
                    logger.info(f"Advanced to question {len(state['stages_completed'])}")
            
            return state
        except Exception as e:
            logger.error(f"Error advancing conversation: {str(e)}")
            state["error"] = f"Failed to advance conversation: {str(e)}"
            return state
    
    async def run_evaluation_tools(state: MasterAgentState) -> MasterAgentState:
        """Run evaluation tools on the conversation data."""
        try:
            # Prepare the conversation contents for evaluation
            contents = []
            for i, message in enumerate(state["conversation_history"]):
                if isinstance(message, HumanMessage):
                    role = "Customer"
                elif isinstance(message, AIMessage):
                    role = "Agent"
                else:
                    continue  # Skip system messages
                
                contents.append(f"{role}: {message.content}")
            
            # Create an InterviewAnalysisState for the tools
            analysis_state = InterviewAnalysisState(
                contents=contents,
                final_summary="",
                grammar_evaluation=[],
                spelling_mistakes_evaluation=[],
                vocabulary_score_evaluation=0,
                sentence_structure_score=0,
                professional_tone_score=0,
                overall_language_score=0
            )
            
            # Run tools based on the tools_to_run list or run all tools if empty
            tools_to_run = state.get("tools_to_run", [])
            
            # Run summarization
            if not tools_to_run or "summarize_interview_history" in tools_to_run:
                logger.info("Running conversation summarization")
                try:
                    analysis_state = await summarize_interview_history(analysis_state)
                    state["final_summary"] = analysis_state.get("final_summary", "")
                except Exception as e:
                    logger.error(f"Error in summarization: {str(e)}")
                    state["final_summary"] = "Error generating summary."
            
            # Run grammar check
            if (not tools_to_run or "grammar_check" in tools_to_run) and state["final_summary"]:
                logger.info("Running grammar check")
                try:
                    grammar_result = grammar_check(analysis_state)
                    state["grammar_evaluation"] = grammar_result
                except Exception as e:
                    logger.error(f"Error in grammar check: {str(e)}")
                    state["grammar_evaluation"] = "Error performing grammar check."
            
            # Run validation
            if (not tools_to_run or "validation_tool" in tools_to_run) and state["final_summary"]:
                logger.info("Running validation")
                try:
                    validation_state = validation_tool(analysis_state)
                    state["validation_result"] = validation_state.get("validation_result", "")
                except Exception as e:
                    logger.error(f"Error in validation: {str(e)}")
                    state["validation_result"] = "Error performing validation."
            
            # Run any additional tools that might be added in the future
            for tool_name in tools_to_run:
                if tool_name not in ["summarize_interview_history", "grammar_check", "validation_tool"]:
                    logger.info(f"Running additional tool: {tool_name}")
                    try:
                        # This would need to be updated to handle additional tools
                        pass
                    except Exception as e:
                        logger.error(f"Error running {tool_name}: {str(e)}")
                        state[f"{tool_name}_result"] = f"Error running {tool_name}."
            
            logger.info("Completed evaluation tools")
            return state
        except Exception as e:
            logger.error(f"Error running evaluation tools: {str(e)}")
            state["error"] = f"Failed to run evaluation tools: {str(e)}"
            return state
    
    async def generate_final_report(state: MasterAgentState) -> MasterAgentState:
        """Generate a final report for the conversation."""
        try:
            # Create a prompt for generating the final report
            if state["is_new_format"]:
                # For new format scenarios, use the evaluation criteria
                evaluation_criteria = state["evaluation_criteria"]
                criteria_text = "\n".join([f"{key}: {value}" for key, value in evaluation_criteria.items()])
                
                report_prompt = PromptTemplate(
                    template="""
                    You are evaluating a customer service conversation. Generate a comprehensive evaluation report based on the following information:
                    
                    SCENARIO: {scenario_title}
                    DESCRIPTION: {scenario_description}
                    
                    EVALUATION CRITERIA:
                    {evaluation_criteria}
                    
                    CONVERSATION SUMMARY:
                    {final_summary}
                    
                    GRAMMAR EVALUATION:
                    {grammar_evaluation}
                    
                    VALIDATION RESULT:
                    {validation_result}
                    
                    Please provide a structured report with the following sections:
                    1. Executive Summary
                    2. Communication Skills Assessment
                    3. Problem Resolution Evaluation
                    4. Strengths and Areas for Improvement
                    5. Overall Rating (1-10) with Justification
                    
                    Format the report in a clear, professional manner suitable for HR records.
                    """,
                    input_variables=[
                        "scenario_title", 
                        "scenario_description", 
                        "evaluation_criteria",
                        "final_summary", 
                        "grammar_evaluation", 
                        "validation_result"
                    ]
                )
                
                # Generate the report
                report_chain = report_prompt | llm | StrOutputParser()
                final_report = await report_chain.ainvoke({
                    "scenario_title": state["scenario"]["title"],
                    "scenario_description": state["scenario"]["description"],
                    "evaluation_criteria": criteria_text,
                    "final_summary": state["final_summary"] or "No summary available.",
                    "grammar_evaluation": state["grammar_evaluation"] or "No grammar evaluation available.",
                    "validation_result": state["validation_result"] or "No validation result available."
                })
            else:
                # For traditional scenarios, use a more generic approach
                report_prompt = PromptTemplate(
                    template="""
                    You are an HR professional reviewing a technical interview. Generate a comprehensive evaluation report based on the following information:
                    
                    SCENARIO: {scenario_title}
                    DESCRIPTION: {scenario_description}
                    
                    INTERVIEW SUMMARY:
                    {final_summary}
                    
                    GRAMMAR EVALUATION:
                    {grammar_evaluation}
                    
                    VALIDATION RESULT:
                    {validation_result}
                    
                    Please provide a structured report with the following sections:
                    1. Executive Summary
                    2. Technical Skills Assessment
                    3. Communication Evaluation
                    4. Strengths and Areas for Improvement
                    5. Overall Rating (1-10) with Justification
                    
                    Format the report in a clear, professional manner suitable for HR records.
                    """,
                    input_variables=[
                        "scenario_title", 
                        "scenario_description", 
                        "final_summary", 
                        "grammar_evaluation", 
                        "validation_result"
                    ]
                )
                
                # Generate the report
                report_chain = report_prompt | llm | StrOutputParser()
                final_report = await report_chain.ainvoke({
                    "scenario_title": state["scenario"]["title"],
                    "scenario_description": state["scenario"]["description"],
                    "final_summary": state["final_summary"] or "No summary available.",
                    "grammar_evaluation": state["grammar_evaluation"] or "No grammar evaluation available.",
                    "validation_result": state["validation_result"] or "No validation result available."
                })
            
            # Store the final report
            state["final_report"] = final_report
            
            logger.info("Generated final conversation report")
            return state
        except Exception as e:
            logger.error(f"Error generating final report: {str(e)}")
            state["error"] = f"Failed to generate final report: {str(e)}"
            return state
    
    # Define the conditional routing logic
    
    def route_after_processing(state: MasterAgentState) -> Literal["advance_conversation", "run_evaluation_tools"]:
        """Determine the next step after processing a response."""
        if state.get("interview_complete", False):
            return "run_evaluation_tools"
        
        return "advance_conversation"
    
    def route_after_advancing(state: MasterAgentState) -> Literal["process_response", "run_evaluation_tools"]:
        """Determine the next step after advancing the conversation."""
        if state.get("interview_complete", False):
            return "run_evaluation_tools"
        
        return "process_response"
    
    def route_after_evaluation(state: MasterAgentState) -> Literal["generate_final_report", "error"]:
        """Determine the next step after running evaluation tools."""
        if state.get("error"):
            return "error"
        
        return "generate_final_report"
    
    # Create the graph
    graph = StateGraph(MasterAgentState)
    
    # Add nodes
    graph.add_node("initialize_conversation", initialize_conversation)
    graph.add_node("process_response", process_response)
    graph.add_node("advance_conversation", advance_conversation)
    graph.add_node("run_evaluation_tools", run_evaluation_tools)
    graph.add_node("generate_final_report", generate_final_report)
    
    # Add edges
    graph.add_edge(START, "initialize_conversation")
    graph.add_edge("initialize_conversation", "process_response")
    graph.add_conditional_edges("process_response", route_after_processing)
    graph.add_conditional_edges("advance_conversation", route_after_advancing)
    graph.add_conditional_edges("run_evaluation_tools", route_after_evaluation)
    graph.add_edge("generate_final_report", END)
    
    # Compile the graph (without persistence for now)
    return graph.compile()

# Function to run the master agent
async def run_conversation(
    customer_responses: List[str],
    session_id: str = None
) -> Dict[str, Any]:
    """
    Run a complete conversation with the provided customer responses.
    
    Args:
        customer_responses: List of customer responses to use in the conversation.
        session_id: Optional session ID for resuming a conversation. If None, a new conversation is started.
        
    Returns:
        The final state of the conversation, including the evaluation report.
    """
    # Create the master agent graph
    master_agent = create_master_agent_graph()
    
    # Initialize new state
    state = MasterAgentState(
        scenario={},
        scenario_id="",
        is_new_format=False,
        current_stage="",
        stages_completed=[],
        conversation_history=[],
        customer_response=None,
        context={},
        customer_profile={},
        evaluation_criteria={},
        interview_complete=False,
        final_summary=None,
        grammar_evaluation=None,
        validation_result=None,
        tools_to_run=[],
        error=None,
        session_id=session_id
    )
    
    # Start the conversation
    try:
        # Initialize the conversation
        current_state = None
        async for step in master_agent.ainvoke(state):
            current_state = step
            
            # If we need a customer response and have one available, provide it
            if (not current_state.get("customer_response") and 
                not current_state.get("interview_complete") and 
                customer_responses):
                current_state["customer_response"] = customer_responses.pop(0)
        
        # Return the final state
        return current_state
    except Exception as e:
        logger.error(f"Error running conversation: {str(e)}")
        return {
            "error": f"Failed to run conversation: {str(e)}",
            "state": state
        }