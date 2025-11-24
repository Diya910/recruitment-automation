from typing import Dict, List, Any, Optional, Literal, TypedDict, Annotated, Union
from loguru import logger
import operator
import json
from enum import Enum

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain.prompts import PromptTemplate
from langgraph.graph import StateGraph, START, END
from langgraph.constants import Send

from domains.utils import get_chat_llm
from domains.stategraph import InterviewAnalysisState
from domains.recruitment.scenario_manager import ScenarioManager
from domains.recruitment.conversation import ConversationEngine
from domains.recruitment.tools import grammar_check, validation_tool, summarize_interview_history

# Define the state for the master agent
class MasterAgentState(TypedDict):
    """State for the master agent orchestrating the interview process."""
    scenario: Dict[str, Any]
    current_question: Dict[str, str]
    questions_asked: List[str]
    conversation_history: List[Union[HumanMessage, AIMessage, SystemMessage]]
    candidate_response: Optional[str]
    awaiting_clarification: bool
    interview_complete: bool
    evaluation: Dict[str, Any]
    final_summary: Optional[str]
    grammar_evaluation: Optional[str]
    validation_result: Optional[str]
    tools_to_run: List[str]
    error: Optional[str]

# Define the possible actions for the master agent
class MasterAgentAction(str, Enum):
    PROCESS_RESPONSE = "process_response"
    ASK_CLARIFICATION = "ask_clarification"
    SELECT_NEXT_QUESTION = "select_next_question"
    RUN_EVALUATION = "run_evaluation"
    GENERATE_SUMMARY = "generate_summary"
    COMPLETE_INTERVIEW = "complete_interview"
    ERROR = "error"

# Create the master agent graph
def create_master_agent_graph():
    """
    Create the LangGraph for the master agent orchestration.
    """
    # Initialize components
    conversation_engine = ConversationEngine()
    llm = get_chat_llm()
    
    # Define the nodes for the graph
    
    async def initialize_interview(state: MasterAgentState) -> MasterAgentState:
        """Initialize a new interview session."""
        try:
            # Start a new interview with a random scenario
            session = conversation_engine.start_interview()
            
            # Update the state with the session information
            state["scenario"] = session["scenario"]
            state["current_question"] = session["current_question"]
            state["questions_asked"] = session["questions_asked"]
            state["conversation_history"] = session["conversation_history"]
            state["awaiting_clarification"] = False
            state["interview_complete"] = False
            state["evaluation"] = {}
            state["final_summary"] = None
            state["grammar_evaluation"] = None
            state["validation_result"] = None
            state["tools_to_run"] = []
            state["error"] = None
            
            logger.info(f"Initialized interview with scenario: {state['scenario']['id']}")
            return state
        except Exception as e:
            logger.error(f"Error initializing interview: {str(e)}")
            state["error"] = f"Failed to initialize interview: {str(e)}"
            return state
    
    async def process_response(state: MasterAgentState) -> MasterAgentState:
        """Process the candidate's response."""
        try:
            if not state.get("candidate_response"):
                logger.warning("No candidate response to process")
                return state
            
            # Create a session object for the conversation engine
            session = {
                "scenario": state["scenario"],
                "current_question": state["current_question"],
                "questions_asked": state["questions_asked"],
                "conversation_history": state["conversation_history"],
                "evaluation": state["evaluation"],
                "awaiting_clarification": state.get("awaiting_clarification", False)
            }
            
            # Process the response
            updated_session = await conversation_engine.process_response(
                session, 
                state["candidate_response"]
            )
            
            # Update the state with the updated session information
            state.update({
                "current_question": updated_session["current_question"],
                "questions_asked": updated_session["questions_asked"],
                "conversation_history": updated_session["conversation_history"],
                "evaluation": updated_session["evaluation"],
                "awaiting_clarification": updated_session.get("awaiting_clarification", False),
                "interview_complete": updated_session.get("interview_complete", False)
            })
            
            # Clear the candidate response
            state["candidate_response"] = None
            
            logger.info("Processed candidate response")
            return state
        except Exception as e:
            logger.error(f"Error processing response: {str(e)}")
            state["error"] = f"Failed to process response: {str(e)}"
            return state
    
    async def run_evaluation_tools(state: MasterAgentState) -> MasterAgentState:
        """Run evaluation tools on the interview data."""
        try:
            # Prepare the interview contents for evaluation
            contents = []
            for i, message in enumerate(state["conversation_history"]):
                if isinstance(message, HumanMessage):
                    role = "Candidate"
                elif isinstance(message, AIMessage):
                    role = "Interviewer"
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
            
            # Run summarization
            logger.info("Running interview summarization")
            try:
                analysis_state = await summarize_interview_history(analysis_state)
                state["final_summary"] = analysis_state.get("final_summary", "")
            except Exception as e:
                logger.error(f"Error in summarization: {str(e)}")
                state["final_summary"] = "Error generating summary."
            
            # Run grammar check
            if state["final_summary"]:
                logger.info("Running grammar check")
                try:
                    grammar_result = grammar_check(analysis_state)
                    state["grammar_evaluation"] = grammar_result
                except Exception as e:
                    logger.error(f"Error in grammar check: {str(e)}")
                    state["grammar_evaluation"] = "Error performing grammar check."
            
            # Run validation
            if state["final_summary"]:
                logger.info("Running validation")
                try:
                    validation_state = validation_tool(analysis_state)
                    state["validation_result"] = validation_state.get("validation_result", "")
                except Exception as e:
                    logger.error(f"Error in validation: {str(e)}")
                    state["validation_result"] = "Error performing validation."
            
            logger.info("Completed evaluation tools")
            return state
        except Exception as e:
            logger.error(f"Error running evaluation tools: {str(e)}")
            state["error"] = f"Failed to run evaluation tools: {str(e)}"
            return state
    
    async def generate_final_report(state: MasterAgentState) -> MasterAgentState:
        """Generate a final report for the interview."""
        try:
            # Create a prompt for generating the final report
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
                
                DETAILED EVALUATIONS:
                {detailed_evaluations}
                
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
                    "validation_result", 
                    "detailed_evaluations"
                ]
            )
            
            # Format the detailed evaluations
            detailed_evaluations = []
            for question_id, eval_data in state["evaluation"].items():
                question = eval_data["question"]
                response = eval_data["response"]
                analysis = eval_data["analysis"]
                
                eval_text = f"QUESTION: {question}\n"
                eval_text += f"RESPONSE: {response}\n"
                eval_text += f"ANALYSIS:\n"
                eval_text += f"- Relevance: {analysis['relevance_score']}/10\n"
                eval_text += f"- Completeness: {analysis['completeness_score']}/10\n"
                eval_text += f"- Clarity: {analysis['clarity_score']}/10\n"
                eval_text += f"- Technical Accuracy: {analysis['technical_accuracy_score']}/10\n"
                eval_text += f"- Professional Tone: {analysis['professional_tone_score']}/10\n"
                eval_text += f"- Reasoning: {analysis['reasoning']}\n"
                
                detailed_evaluations.append(eval_text)
            
            # Generate the report
            report_chain = report_prompt | llm | StrOutputParser()
            final_report = await report_chain.ainvoke({
                "scenario_title": state["scenario"]["title"],
                "scenario_description": state["scenario"]["description"],
                "final_summary": state["final_summary"] or "No summary available.",
                "grammar_evaluation": state["grammar_evaluation"] or "No grammar evaluation available.",
                "validation_result": state["validation_result"] or "No validation result available.",
                "detailed_evaluations": "\n\n".join(detailed_evaluations)
            })
            
            # Store the final report
            state["final_report"] = final_report
            
            logger.info("Generated final interview report")
            return state
        except Exception as e:
            logger.error(f"Error generating final report: {str(e)}")
            state["error"] = f"Failed to generate final report: {str(e)}"
            return state
    
    # Define the conditional routing logic
    
    def route_after_processing(state: MasterAgentState) -> Literal["run_evaluation_tools", "process_response"]:
        """Determine the next step after processing a response."""
        if state.get("error"):
            return "error"
        
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
    graph.add_node("initialize_interview", initialize_interview)
    graph.add_node("process_response", process_response)
    graph.add_node("run_evaluation_tools", run_evaluation_tools)
    graph.add_node("generate_final_report", generate_final_report)
    
    # Add edges
    graph.add_edge(START, "initialize_interview")
    graph.add_edge("initialize_interview", "process_response")
    graph.add_conditional_edges("process_response", route_after_processing)
    graph.add_conditional_edges("run_evaluation_tools", route_after_evaluation)
    graph.add_edge("generate_final_report", END)
    
    # Compile the graph
    return graph.compile()

# Function to run the master agent
async def run_interview(candidate_responses: List[str]) -> Dict[str, Any]:
    """
    Run a complete interview with the provided candidate responses.
    
    Args:
        candidate_responses: List of candidate responses to use in the interview.
        
    Returns:
        The final state of the interview, including the evaluation report.
    """
    # Create the master agent graph
    master_agent = create_master_agent_graph()
    
    # Initialize the state
    state = MasterAgentState(
        scenario={},
        current_question={},
        questions_asked=[],
        conversation_history=[],
        candidate_response=None,
        awaiting_clarification=False,
        interview_complete=False,
        evaluation={},
        final_summary=None,
        grammar_evaluation=None,
        validation_result=None,
        tools_to_run=[],
        error=None
    )

    try:
        # Initialize the interview
        current_state = None
        async for step in master_agent.ainvoke(state):
            current_state = step
            
            # If we need a candidate response and have one available, provide it
            if (not current_state.get("candidate_response") and 
                not current_state.get("interview_complete") and 
                candidate_responses):
                current_state["candidate_response"] = candidate_responses.pop(0)
        
        # Return the final state
        return current_state
    except Exception as e:
        logger.error(f"Error running interview: {str(e)}")
        return {
            "error": f"Failed to run interview: {str(e)}",
            "state": state
        }