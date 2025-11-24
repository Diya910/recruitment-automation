from typing import Dict, List, Any, Optional, Union
from loguru import logger
import asyncio
import json
import os
from datetime import datetime
import concurrent.futures
import threading
from functools import partial

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from domains.recruitment.scenario_manager import ScenarioManager
from domains.recruitment.conversation import ConversationEngine
from domains.recruitment.master_agent import run_interview
from domains.recruitment.evaluation import EvaluationSystem
from domains.recruitment.storage import StorageSystem
from domains.settings import config_settings

# Thread-local storage for session-specific data
thread_local = threading.local()

# Semaphore for limiting concurrent interviews
interview_semaphore = asyncio.Semaphore(config_settings.CONCURRENCY_LIMIT)

class HRAutomationHandler:
    """
    Main handler for the HR Automation Tool, orchestrating all components.
    """
    
    def __init__(self):
        """Initialize the HR Automation Handler."""
        self.scenario_manager = ScenarioManager()
        self.conversation_engine = ConversationEngine(self.scenario_manager)
        self.evaluation_system = EvaluationSystem()
        self.storage_system = StorageSystem()
        
        # Create exports directory if it doesn't exist
        base_dir = os.path.dirname(os.path.dirname(__file__))
        self.exports_dir = os.path.join(base_dir, "exports")
        os.makedirs(self.exports_dir, exist_ok=True)
        
        logger.info("Initialized HR Automation Handler")
    
    async def start_interview_session(
        self, 
        scenario_id: Optional[str] = None, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Start a new interview session.
        
        Args:
            scenario_id: Optional ID of the scenario to use. If None, a random scenario is selected.
            metadata: Optional metadata about the session (e.g., candidate info).
            
        Returns:
            Dictionary with session information.
        """
        async with interview_semaphore:
            try:
                # Select scenario
                if scenario_id:
                    scenario = self.scenario_manager.get_scenario_by_id(scenario_id)
                    if not scenario:
                        logger.error(f"Scenario with ID {scenario_id} not found")
                        return {"error": f"Scenario with ID {scenario_id} not found"}
                else:
                    scenario = self.scenario_manager.select_random_scenario()
                
                # Create session in storage
                session_id = self.storage_system.create_session(
                    scenario["id"],
                    metadata
                )
                
                # Start interview
                session = self.conversation_engine.start_interview(scenario["id"])
                
                # Store session information
                session_info = {
                    "session_id": session_id,
                    "scenario": {
                        "id": scenario["id"],
                        "title": scenario["title"],
                        "description": scenario["description"]
                    },
                    "current_question": session["current_question"],
                    "conversation_history": [
                        {"role": "system" if isinstance(msg, SystemMessage) else 
                                 "assistant" if isinstance(msg, AIMessage) else 
                                 "user", 
                         "content": msg.content}
                        for msg in session["conversation_history"]
                    ]
                }
                
                logger.info(f"Started interview session {session_id} with scenario {scenario['id']}")
                return session_info
            except Exception as e:
                logger.error(f"Error starting interview session: {str(e)}")
                return {"error": f"Failed to start interview: {str(e)}"}
    
    async def process_response(
        self, 
        session_id: str, 
        response: str
    ) -> Dict[str, Any]:
        """
        Process a candidate's response in an interview session.
        
        Args:
            session_id: The session ID
            response: The candidate's response
            
        Returns:
            Dictionary with updated session information.
        """
        async with interview_semaphore:
            try:
                # Get session data
                session_data = self.storage_system.get_session(session_id)
                if not session_data:
                    logger.error(f"Session {session_id} not found")
                    return {"error": f"Session {session_id} not found"}
                
                # Get scenario
                scenario_id = session_data["scenario_id"]
                scenario = self.scenario_manager.get_scenario_by_id(scenario_id)
                
                # Get session responses
                responses = self.storage_system.get_session_responses(session_id)
                
                # Reconstruct conversation history
                conversation_history = []
                
                # Add system message
                conversation_history.append(SystemMessage(content="You are an HR interviewer conducting a technical assessment interview."))
                
                # Add previous Q&A pairs
                for resp in responses:
                    # Find the question
                    question_text = ""
                    for q in scenario["questions"]:
                        if q["id"] == resp["question_id"]:
                            question_text = q["question"]
                            break
                    
                    conversation_history.append(AIMessage(content=question_text))
                    conversation_history.append(HumanMessage(content=resp["response_text"]))
                
                # Get current question
                current_question = None
                questions_asked = [resp["question_id"] for resp in responses]
                
                if not questions_asked:
                    # First question
                    current_question = scenario["questions"][0]
                else:
                    # Find the next question
                    for q in scenario["questions"]:
                        if q["id"] not in questions_asked:
                            current_question = q
                            break
                
                if not current_question:
                    # All questions have been asked
                    logger.info(f"All questions have been asked for session {session_id}")
                    return self._complete_interview(session_id, scenario, responses)
                
                # Add current question to conversation history
                conversation_history.append(AIMessage(content=current_question["question"]))
                
                # Create session object for conversation engine
                session = {
                    "scenario": scenario,
                    "current_question": current_question,
                    "questions_asked": questions_asked,
                    "conversation_history": conversation_history,
                    "evaluation": {}
                }
                
                # Process the response
                updated_session = await self.conversation_engine.process_response(
                    session,
                    response
                )
                
                # Store the response
                self.storage_system.store_response(
                    session_id,
                    current_question["id"],
                    response
                )
                
                # Check if interview is complete
                if updated_session.get("interview_complete", False):
                    return await self._complete_interview(session_id, scenario, responses + [{"question_id": current_question["id"], "response_text": response}])
                
                # Return updated session information
                session_info = {
                    "session_id": session_id,
                    "scenario": {
                        "id": scenario["id"],
                        "title": scenario["title"],
                        "description": scenario["description"]
                    },
                    "current_question": updated_session["current_question"],
                    "awaiting_clarification": updated_session.get("awaiting_clarification", False),
                    "conversation_history": [
                        {"role": "system" if isinstance(msg, SystemMessage) else 
                                 "assistant" if isinstance(msg, AIMessage) else 
                                 "user", 
                         "content": msg.content}
                        for msg in updated_session["conversation_history"]
                    ]
                }
                
                logger.info(f"Processed response for session {session_id}")
                return session_info
            except Exception as e:
                logger.error(f"Error processing response: {str(e)}")
                return {"error": f"Failed to process response: {str(e)}"}
    
    async def _complete_interview(
        self, 
        session_id: str, 
        scenario: Dict[str, Any], 
        responses: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Complete an interview session and generate evaluation report.
        
        Args:
            session_id: The session ID
            scenario: The scenario data
            responses: List of responses
            
        Returns:
            Dictionary with final report.
        """
        try:
            # Update session status
            self.storage_system.update_session_status(session_id, "completed")
            
            # Prepare responses for evaluation
            response_dict = {}
            for resp in responses:
                response_dict[resp["question_id"]] = resp["response_text"]
            
            # Generate interview summary
            candidate_responses = [resp["response_text"] for resp in responses]
            interview_result = await run_interview(candidate_responses)
            
            final_summary = interview_result.get("final_summary", "")
            
            # Generate evaluation report
            report = await self.evaluation_system.generate_evaluation_report(
                scenario,
                response_dict,
                final_summary
            )
            
            # Store evaluations
            for question_id, evaluation in report.get("detailed_evaluations", {}).items():
                self.storage_system.store_evaluation(
                    session_id,
                    "detailed",
                    {
                        "question_id": question_id,
                        "evaluation": evaluation
                    }
                )
            
            # Store overall evaluation
            if "overall_evaluation" in report:
                self.storage_system.store_evaluation(
                    session_id,
                    "overall",
                    report["overall_evaluation"]
                )
            
            # Store report
            report_id = self.storage_system.store_report(session_id, report)
            
            # Export report to JSON
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_path = os.path.join(
                self.exports_dir, 
                f"report_{session_id}_{timestamp}.json"
            )
            
            with open(export_path, "w") as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"Completed interview session {session_id} and generated report")
            
            return {
                "session_id": session_id,
                "status": "completed",
                "report": report,
                "export_path": export_path
            }
        except Exception as e:
            logger.error(f"Error completing interview: {str(e)}")
            self.storage_system.update_session_status(session_id, "error")
            return {"error": f"Failed to complete interview: {str(e)}"}
    
    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """
        Get information about a session.
        
        Args:
            session_id: The session ID
            
        Returns:
            Dictionary with session information.
        """
        try:
            # Get complete session data
            data = self.storage_system.get_complete_session_data(session_id)
            
            if not data:
                logger.error(f"Session {session_id} not found")
                return {"error": f"Session {session_id} not found"}
            
            return data
        except Exception as e:
            logger.error(f"Error getting session info: {str(e)}")
            return {"error": f"Failed to get session info: {str(e)}"}
    
    def get_all_sessions(self, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """
        Get all sessions with pagination.
        
        Args:
            limit: Maximum number of sessions to return
            offset: Offset for pagination
            
        Returns:
            Dictionary with sessions.
        """
        try:
            sessions = self.storage_system.get_all_sessions(limit, offset)
            
            return {
                "sessions": sessions,
                "count": len(sessions),
                "limit": limit,
                "offset": offset
            }
        except Exception as e:
            logger.error(f"Error getting all sessions: {str(e)}")
            return {"error": f"Failed to get sessions: {str(e)}"}
    
    def search_sessions(self, query: str, limit: int = 100) -> Dict[str, Any]:
        """
        Search for sessions.
        
        Args:
            query: Search query
            limit: Maximum number of sessions to return
            
        Returns:
            Dictionary with matching sessions.
        """
        try:
            sessions = self.storage_system.search_sessions(query, limit)
            
            return {
                "query": query,
                "sessions": sessions,
                "count": len(sessions)
            }
        except Exception as e:
            logger.error(f"Error searching sessions: {str(e)}")
            return {"error": f"Failed to search sessions: {str(e)}"}
    
    def export_session(self, session_id: str) -> Dict[str, Any]:
        """
        Export a session to a JSON file.
        
        Args:
            session_id: The session ID
            
        Returns:
            Dictionary with export information.
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_path = os.path.join(
                self.exports_dir, 
                f"session_{session_id}_{timestamp}.json"
            )
            
            path = self.storage_system.export_session_to_json(session_id, export_path)
            
            return {
                "session_id": session_id,
                "export_path": path
            }
        except Exception as e:
            logger.error(f"Error exporting session: {str(e)}")
            return {"error": f"Failed to export session: {str(e)}"}
    
    async def run_batch_interviews(
        self, 
        scenario_ids: List[str], 
        responses_list: List[List[str]],
        metadata_list: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Run multiple interviews in parallel.
        
        Args:
            scenario_ids: List of scenario IDs to use
            responses_list: List of response lists, one for each interview
            metadata_list: Optional list of metadata dictionaries, one for each interview
            
        Returns:
            List of results, one for each interview.
        """
        if metadata_list is None:
            metadata_list = [None] * len(scenario_ids)
        
        if len(scenario_ids) != len(responses_list) or len(scenario_ids) != len(metadata_list):
            logger.error("Mismatch in input list lengths")
            return [{"error": "Mismatch in input list lengths"}]
        
        # Create tasks for each interview
        tasks = []
        for i, (scenario_id, responses, metadata) in enumerate(zip(scenario_ids, responses_list, metadata_list)):
            tasks.append(self._run_single_interview(scenario_id, responses, metadata))
        
        # Run interviews in parallel with concurrency limit
        results = await asyncio.gather(*tasks)
        
        return results
    
    async def _run_single_interview(
        self, 
        scenario_id: str, 
        responses: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run a single interview from start to finish.
        
        Args:
            scenario_id: The scenario ID
            responses: List of responses to use
            metadata: Optional metadata about the session
            
        Returns:
            Dictionary with final report.
        """
        async with interview_semaphore:
            try:
                # Start session
                session_info = await self.start_interview_session(scenario_id, metadata)
                
                if "error" in session_info:
                    return session_info
                
                session_id = session_info["session_id"]
                
                # Process each response
                for response in responses:
                    result = await self.process_response(session_id, response)
                    
                    if "error" in result:
                        return result
                    
                    # If interview is complete, return the result
                    if result.get("status") == "completed":
                        return result
                
                # If we get here, the interview wasn't completed with the provided responses
                logger.warning(f"Interview {session_id} not completed with provided responses")
                return {
                    "session_id": session_id,
                    "status": "incomplete",
                    "warning": "Not enough responses provided to complete the interview"
                }
            except Exception as e:
                logger.error(f"Error running single interview: {str(e)}")
                return {"error": f"Failed to run interview: {str(e)}"}

# Create a singleton instance
hr_automation_handler = HRAutomationHandler()

# Convenience functions for external use

async def start_interview(scenario_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Start a new interview session."""
    return await hr_automation_handler.start_interview_session(scenario_id, metadata)

async def process_response(session_id: str, response: str) -> Dict[str, Any]:
    """Process a candidate's response."""
    return await hr_automation_handler.process_response(session_id, response)

def get_session_info(session_id: str) -> Dict[str, Any]:
    """Get information about a session."""
    return hr_automation_handler.get_session_info(session_id)

def get_all_sessions(limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """Get all sessions with pagination."""
    return hr_automation_handler.get_all_sessions(limit, offset)

def search_sessions(query: str, limit: int = 100) -> Dict[str, Any]:
    """Search for sessions."""
    return hr_automation_handler.search_sessions(query, limit)

def export_session(session_id: str) -> Dict[str, Any]:
    """Export a session to a JSON file."""
    return hr_automation_handler.export_session(session_id)

async def run_batch_interviews(
    scenario_ids: List[str], 
    responses_list: List[List[str]],
    metadata_list: Optional[List[Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    """Run multiple interviews in parallel."""
    return await hr_automation_handler.run_batch_interviews(scenario_ids, responses_list, metadata_list)