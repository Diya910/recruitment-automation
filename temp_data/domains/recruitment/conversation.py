from typing import List, Dict, Any, Optional, Tuple
from loguru import logger
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain.output_parsers import PydanticOutputParser
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from domains.utils import get_chat_llm
from domains.recruitment.scenario_manager import ScenarioManager

# Define Pydantic models for structured outputs
class ClarificationResponse(BaseModel):
    needs_clarification: bool = Field(description="Whether the response needs clarification")
    clarification_question: Optional[str] = Field(description="Follow-up question to ask for clarification")
    reasoning: str = Field(description="Reasoning behind the decision")

class ResponseAnalysis(BaseModel):
    relevance_score: int = Field(description="How relevant the response is to the question (1-10)")
    completeness_score: int = Field(description="How completely the response answers the question (1-10)")
    clarity_score: int = Field(description="How clear and well-structured the response is (1-10)")
    technical_accuracy_score: int = Field(description="How technically accurate the response is (1-10)")
    professional_tone_score: int = Field(description="How professional the tone of the response is (1-10)")
    reasoning: str = Field(description="Reasoning behind the scores")

# Prompt templates
SYSTEM_PROMPT = """You are an HR interviewer conducting a technical assessment interview. 
Your goal is to evaluate the candidate's responses to technical questions.
Be professional, courteous, and thorough in your interactions.
"""

INTERVIEW_PROMPT = """
You are conducting a technical interview for a candidate. The interview is focused on the following topic:

SCENARIO: {scenario_title}
DESCRIPTION: {scenario_description}

CURRENT QUESTION: {question}

Please analyze the candidate's response and determine if you need to ask a clarifying follow-up question.
"""

CLARIFICATION_PROMPT_TEMPLATE = """
You are conducting a technical interview. The candidate has provided a response to your question, but you need to determine if clarification is needed.

ORIGINAL QUESTION: {question}
CANDIDATE'S RESPONSE: {response}

Analyze the response and determine if you need to ask a clarifying follow-up question. 
If the response is unclear, incomplete, or doesn't fully address the question, formulate a specific follow-up question.
If the response is clear and complete, indicate that no clarification is needed.

{format_instructions}
"""

RESPONSE_ANALYSIS_PROMPT_TEMPLATE = """
You are evaluating a candidate's response to a technical interview question.

QUESTION: {question}
CANDIDATE'S RESPONSE: {response}

Provide a detailed analysis of the response based on the following criteria:
1. Relevance: How directly the response addresses the question
2. Completeness: How thoroughly the question was answered
3. Clarity: How well-organized and clear the response is
4. Technical Accuracy: How technically sound the concepts and solutions are
5. Professional Tone: How professional the language and tone are

For each criterion, provide a score from 1-10 and brief justification.

{format_instructions}
"""

NEXT_QUESTION_PROMPT_TEMPLATE = """
You are conducting a technical interview. Based on the conversation so far, determine the most appropriate next question to ask.

SCENARIO: {scenario_title}
DESCRIPTION: {scenario_description}
QUESTIONS AVAILABLE:
{available_questions}

CONVERSATION HISTORY:
{conversation_history}

Select the most appropriate next question from the available questions. Choose a question that logically follows from the previous discussion and helps evaluate different aspects of the candidate's knowledge.

Return only the ID of the selected question.
"""

class ConversationEngine:
    """
    LangChain-based conversational engine for conducting technical interviews.
    """
    
    def __init__(self, scenario_manager: Optional[ScenarioManager] = None):
        """
        Initialize the ConversationEngine.
        
        Args:
            scenario_manager: ScenarioManager instance for handling scenarios.
        """
        self.scenario_manager = scenario_manager or ScenarioManager()
        self.llm = get_chat_llm()
        
        # Initialize parsers
        self.clarification_parser = PydanticOutputParser(pydantic_object=ClarificationResponse)
        self.response_analysis_parser = PydanticOutputParser(pydantic_object=ResponseAnalysis)
        
        # Initialize prompts
        self.clarification_prompt = PromptTemplate(
            template=CLARIFICATION_PROMPT_TEMPLATE,
            input_variables=["question", "response"],
            partial_variables={"format_instructions": self.clarification_parser.get_format_instructions()}
        )
        
        self.response_analysis_prompt = PromptTemplate(
            template=RESPONSE_ANALYSIS_PROMPT_TEMPLATE,
            input_variables=["question", "response"],
            partial_variables={"format_instructions": self.response_analysis_parser.get_format_instructions()}
        )
        
        self.next_question_prompt = PromptTemplate(
            template=NEXT_QUESTION_PROMPT_TEMPLATE,
            input_variables=["scenario_title", "scenario_description", "available_questions", "conversation_history"]
        )
    
    def start_interview(self, scenario_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Start a new interview session.
        
        Args:
            scenario_id: Optional ID of the scenario to use. If None, a random scenario is selected.
            
        Returns:
            Dictionary with interview session information.
        """
        # Select scenario
        if scenario_id:
            scenario = self.scenario_manager.get_scenario_by_id(scenario_id)
            if not scenario:
                logger.error(f"Scenario with ID {scenario_id} not found")
                scenario = self.scenario_manager.select_random_scenario()
        else:
            scenario = self.scenario_manager.select_random_scenario()
        
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
        first_question = scenario["questions"][0]
        session["current_question"] = first_question
        session["questions_asked"].append(first_question["id"])
        
        # Add first question to conversation history
        session["conversation_history"].append(
            AIMessage(content=f"Let's begin the interview. {first_question['question']}")
        )
        
        return session
    
    async def process_response(self, session: Dict[str, Any], response: str) -> Dict[str, Any]:
        """
        Process a candidate's response and determine next steps.
        
        Args:
            session: The current interview session.
            response: The candidate's response to the current question.
            
        Returns:
            Updated session with next steps.
        """
        # Add response to conversation history
        session["conversation_history"].append(
            HumanMessage(content=response)
        )
        
        # Check if clarification is needed
        clarification_chain = self.clarification_prompt | self.llm | self.clarification_parser
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
            return session
        
        # If no clarification needed or clarification was provided, analyze response
        session["awaiting_clarification"] = False
        
        # Analyze response
        analysis_chain = self.response_analysis_prompt | self.llm | self.response_analysis_parser
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
        
        # Determine if interview should continue
        if len(session["questions_asked"]) >= len(session["scenario"]["questions"]):
            # All questions have been asked
            session["interview_complete"] = True
            session["conversation_history"].append(
                AIMessage(content="Thank you for completing this technical interview. We'll now evaluate your responses.")
            )
            return session
        
        # Select next question
        next_question = await self._select_next_question(session)
        session["current_question"] = next_question
        session["questions_asked"].append(next_question["id"])
        
        # Add next question to conversation history
        session["conversation_history"].append(
            AIMessage(content=next_question["question"])
        )
        
        return session
    
    async def _select_next_question(self, session: Dict[str, Any]) -> Dict[str, str]:
        """
        Select the next question to ask based on the conversation history.
        
        Args:
            session: The current interview session.
            
        Returns:
            The next question to ask.
        """
        scenario = session["scenario"]
        questions_asked = session["questions_asked"]
        
        # Get available questions (those not yet asked)
        available_questions = []
        for q in scenario["questions"]:
            if q["id"] not in questions_asked:
                available_questions.append(q)
        
        if not available_questions:
            # No more questions available
            return None
        
        if len(available_questions) == 1:
            # Only one question left
            return available_questions[0]
        
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
        next_question_chain = self.next_question_prompt | self.llm | StrOutputParser()
        next_question_id = await next_question_chain.ainvoke({
            "scenario_title": scenario["title"],
            "scenario_description": scenario["description"],
            "available_questions": available_questions_text,
            "conversation_history": conversation_history_text
        })
        
        # Clean up the response to get just the ID
        next_question_id = next_question_id.strip().replace("ID: ", "").split(",")[0].strip()
        
        # Find the question with the selected ID
        for q in available_questions:
            if q["id"] == next_question_id:
                return q
        
        # If the selected ID wasn't found, return the first available question
        logger.warning(f"Selected question ID {next_question_id} not found, using first available question")
        return available_questions[0]