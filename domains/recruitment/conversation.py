from typing import List, Dict, Any, Optional, Tuple
from loguru import logger
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain.output_parsers import PydanticOutputParser

from domains.utils import get_chat_llm
from domains.recruitment.prompts import (
    ClarificationResponse,
    ResponseAnalysis,
    initialize_clarification_prompt,
    initialize_response_analysis_prompt,
    initialize_next_question_prompt,
    SYSTEM_PROMPT
)
from domains.recruitment.scenario_manager import (
    get_scenario_by_id,
    select_random_scenario
)

_llm = None

def initialize_conversation_engine():
    """Initialize the conversation engine."""
    global _llm
    _llm = get_chat_llm()
    logger.info("Conversation engine initialized")

def start_interview(scenario_id: Optional[str] = None) -> Dict[str, Any]:
    try:
        # Select scenario
        if scenario_id:
            scenario = get_scenario_by_id(scenario_id)
            if not scenario:
                logger.error(f"Scenario with ID {scenario_id} not found")
                scenario = select_random_scenario()
        else:
            scenario = select_random_scenario()
        
        if not scenario:
            logger.error("No scenarios available")
            raise ValueError("No scenarios available to start interview")
        
        # Initialize session
        session = {
            "scenario": scenario,
            "current_question_index": 0,
            "questions_asked": [],
            "conversation_history": [],
            "evaluation": {}
        }
        
        # Add system message to conversation history
        session["conversation_history"].append(
            SystemMessage(content=SYSTEM_PROMPT)
        )
        
        # Get first question
        try:
            first_question = scenario["questions"][0]
        except (IndexError, KeyError) as e:
            logger.error(f"Error accessing first question in scenario: {str(e)}")
            raise ValueError(f"Invalid scenario format: {str(e)}")
        
        session["current_question"] = first_question
        session["questions_asked"].append(first_question["id"])
        
        # Add first question to conversation history
        session["conversation_history"].append(
            AIMessage(content=f"Let's begin the interview. {first_question['question']}")
        )
        
        logger.info(f"Started interview with scenario: {scenario.get('id', 'unknown')}")
        return session
    except Exception as e:
        logger.error(f"Error starting interview: {str(e)}")
        raise

async def process_response(session: Dict[str, Any], response: str) -> Dict[str, Any]:
    """
    Process a candidate's response and determine next steps.
    
    Args:
        session: The current interview session.
        response: The candidate's response to the current question.
        
    Returns:
        Updated session with next steps.
    """
    try:
        # Ensure LLM is initialized
        global _llm
        if _llm is None:
            initialize_conversation_engine()
        
        # Validate session and current question
        if not session:
            logger.error("Empty session provided to process_response")
            raise ValueError("Empty session provided")
        
        if "current_question" not in session:
            logger.error("Session missing current_question")
            raise ValueError("Invalid session format: missing current_question")
        
        # Add response to conversation history
        session["conversation_history"].append(
            HumanMessage(content=response)
        )
        
        # Check if clarification is needed
        try:
            logger.info("Checking if clarification is needed for response")
            clarification_prompt = initialize_clarification_prompt()
            clarification_parser = PydanticOutputParser(pydantic_object=ClarificationResponse)
            clarification_chain = clarification_prompt | _llm | clarification_parser
            
            clarification_result = await clarification_chain.ainvoke({
                "question": session["current_question"]["question"],
                "response": response
            })
            
            if clarification_result.needs_clarification:
                # Add clarification question to conversation history
                session["conversation_history"].append(
                    AIMessage(content=clarification_result.clarification_question)
                )
                session["awaiting_clarification"] = True
                logger.info("Clarification needed, returning with clarification question")
                return session
        except Exception as e:
            logger.error(f"Error in clarification check: {str(e)}")
            # Continue with response analysis even if clarification check fails
        
        # If no clarification needed or clarification was provided, analyze response
        session["awaiting_clarification"] = False
        
        # Analyze response
        try:
            logger.info("Analyzing candidate response")
            response_analysis_prompt = initialize_response_analysis_prompt()
            response_analysis_parser = PydanticOutputParser(pydantic_object=ResponseAnalysis)
            analysis_chain = response_analysis_prompt | _llm | response_analysis_parser
            
            analysis_result = await analysis_chain.ainvoke({
                "question": session["current_question"]["question"],
                "response": response
            })
            
            # Store analysis
            question_id = session["current_question"]["id"]
            session["evaluation"][question_id] = {
                "question": session["current_question"]["question"],
                "response": response,
                "analysis": analysis_result.dict()
            }
            logger.info(f"Response analysis completed for question {question_id}")
        except Exception as e:
            logger.error(f"Error in response analysis: {str(e)}")
            # Create a default analysis if the analysis fails
            question_id = session["current_question"]["id"]
            session["evaluation"][question_id] = {
                "question": session["current_question"]["question"],
                "response": response,
                "analysis": {
                    "relevance_score": 5,
                    "completeness_score": 5,
                    "clarity_score": 5,
                    "technical_accuracy_score": 5,
                    "professional_tone_score": 5,
                    "reasoning": "Analysis failed due to an error."
                }
            }
        
        # Determine if interview should continue
        try:
            questions_asked_count = len(session["questions_asked"])
            total_questions_count = len(session["scenario"]["questions"])
            logger.info(f"Checking if interview is complete: {questions_asked_count} questions asked out of {total_questions_count} total questions")
            logger.debug(f"Questions asked: {session['questions_asked']}")
            
            if questions_asked_count >= total_questions_count:
                # All questions have been asked
                logger.info("All questions have been asked, marking interview as complete")
                session["interview_complete"] = True
                session["conversation_history"].append(
                    AIMessage(content="Thank you for completing this technical interview. We'll now evaluate your responses.")
                )
                logger.info("Interview completed, all questions asked")
                return session
            else:
                logger.info(f"Interview not complete yet, {total_questions_count - questions_asked_count} questions remaining")
        except KeyError as e:
            logger.error(f"Error checking if interview is complete: {str(e)}")
            logger.error(f"Session keys: {list(session.keys())}")
            # Assume interview should continue if we can't determine if it's complete
        
        # Select next question
        try:
            logger.info("Selecting next question")
            next_question = await select_next_question(session)
            if next_question:
                session["current_question"] = next_question
                session["questions_asked"].append(next_question["id"])
                
                # Add next question to conversation history
                session["conversation_history"].append(
                    AIMessage(content=next_question["question"])
                )
                logger.info(f"Selected next question: {next_question['id']}")
            else:
                # No more questions available
                session["interview_complete"] = True
                session["conversation_history"].append(
                    AIMessage(content="Thank you for completing this technical interview. We'll now evaluate your responses.")
                )
                logger.info("Interview completed, no more questions available")
        except Exception as e:
            logger.error(f"Error selecting next question: {str(e)}")
            # Mark interview as complete if we can't select the next question
            session["interview_complete"] = True
            session["conversation_history"].append(
                AIMessage(content="Thank you for completing this technical interview. We'll now evaluate your responses.")
            )
            logger.info("Interview completed due to error in selecting next question")
        
        return session
    except Exception as e:
        logger.error(f"Error processing response: {str(e)}")
        # Return the session as is if there's an error, to avoid losing data
        return session

async def select_next_question(session: Dict[str, Any]) -> Dict[str, str]:
    """
    Select the next question to ask based on the conversation history.
    
    Args:
        session: The current interview session.
        
    Returns:
        The next question to ask, or None if no more questions are available or an error occurs.
    """
    try:
        # Ensure LLM is initialized
        global _llm
        if _llm is None:
            initialize_conversation_engine()
        
        # Validate session
        if not session:
            logger.error("Empty session provided to select_next_question")
            raise ValueError("Empty session provided")
        
        if "scenario" not in session or "questions_asked" not in session:
            logger.error("Session missing required fields (scenario or questions_asked)")
            raise ValueError("Invalid session format: missing required fields")
        
        try:
            scenario = session["scenario"]
            questions_asked = session["questions_asked"]
            
            # Validate scenario
            if "questions" not in scenario:
                logger.error("Scenario missing questions field")
                raise ValueError("Invalid scenario format: missing questions field")
            
            # Get available questions (those not yet asked)
            available_questions = []
            for q in scenario["questions"]:
                if q["id"] not in questions_asked:
                    available_questions.append(q)
            
            if not available_questions:
                # No more questions available
                logger.info("No more questions available")
                return None
            
            if len(available_questions) == 1:
                # Only one question left
                logger.info(f"Only one question left: {available_questions[0]['id']}")
                return available_questions[0]
        except KeyError as e:
            logger.error(f"Error accessing session data: {str(e)}")
            # Return the first available question as a fallback
            if available_questions:
                logger.info(f"Using first available question as fallback due to error: {available_questions[0]['id']}")
                return available_questions[0]
            return None
        
        try:
            # Format available questions for the prompt
            available_questions_text = "\n".join([
                f"ID: {q['id']}, Question: {q['question']}" for q in available_questions
            ])
            
            # Format conversation history for the prompt
            conversation_history_text = "\n".join([
                f"{'Interviewer' if isinstance(msg, AIMessage) else 'Candidate'}: {msg.content}"
                for msg in session["conversation_history"]
                if not isinstance(msg, SystemMessage)
            ])
            
            # Use LLM to select next question
            logger.info("Using LLM to select next question")
            next_question_prompt = initialize_next_question_prompt()
            next_question_chain = next_question_prompt | _llm | StrOutputParser()
            
            next_question_id = await next_question_chain.ainvoke({
                "scenario_title": scenario.get("title", "Unknown Scenario"),
                "scenario_description": scenario.get("description", "No description available"),
                "available_questions": available_questions_text,
                "conversation_history": conversation_history_text
            })
            
            # Clean up the response to get just the ID
            next_question_id = next_question_id.strip().replace("ID: ", "").split(",")[0].strip()
            logger.info(f"LLM selected question ID: {next_question_id}")
            
            # Find the question with the selected ID
            for q in available_questions:
                if q["id"] == next_question_id:
                    logger.info(f"Found matching question for ID {next_question_id}")
                    return q
            
            # If the selected ID wasn't found, return the first available question
            logger.warning(f"Selected question ID {next_question_id} not found, using first available question")
            return available_questions[0]
        except Exception as e:
            logger.error(f"Error selecting next question with LLM: {str(e)}")
            # Return the first available question as a fallback
            if available_questions:
                logger.info(f"Using first available question as fallback due to LLM error: {available_questions[0]['id']}")
                return available_questions[0]
            return None
    except Exception as e:
        logger.error(f"Unexpected error in select_next_question: {str(e)}")
        return None

# Initialize the conversation engine when the module is imported
initialize_conversation_engine()