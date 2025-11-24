import streamlit as st
import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
from loguru import logger

# User credentials dictionary
USERS = {
    "admin": {"password": "admin", "role": "admin"},
    "user": {"password": "user", "role": "user"},
    "john": {"password": "john123", "role": "user"},
    "emma": {"password": "emma123", "role": "user"},
    "alex": {"password": "alex123", "role": "user"}
}

def init_session_state():
    defaults = {
        "user": None,
        "role": None,
        "language": "English",
        "messages": [],
        "theme": "light",
        "upload_history": [],
        "ingested_files": set()  # Track ingested files
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
# Configure logger
logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add("streamlit_app.log", rotation="10 MB", level="DEBUG")

# Import the necessary modules
try:
    from domains.handler import (
        start_interview_session,
        process_response,
        get_session_info,
        get_sessions,
        export_session_data
    )
    from domains.recruitment.scenario_manager import get_all_scenarios, get_scenario_by_id
except ImportError as e:
    st.error(f"Failed to import required modules: {e}")
    st.stop()

# Set page configuration
st.set_page_config(
    page_title="HR Automation Tool",
    page_icon="👔",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #424242;
        margin-bottom: 1rem;
    }
    .card {
        background-color: #f9f9f9;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
    }
    .info-text {
        color: #424242;
        font-size: 1rem;
    }
    .highlight {
        background-color: #e3f2fd;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
    }
    .success-message {
        background-color: #e8f5e9;
        color: #2e7d32;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
    }
    .error-message {
        background-color: #ffebee;
        color: #c62828;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
    }
    .stButton button {
        background-color: #1E88E5;
        color: white;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'active_sessions' not in st.session_state:
    st.session_state.active_sessions = {}
if 'current_session_id' not in st.session_state:
    st.session_state.current_session_id = None
if 'interview_complete' not in st.session_state:
    st.session_state.interview_complete = False
if 'evaluation_report' not in st.session_state:
    st.session_state.evaluation_report = None

# Sidebar navigation
st.sidebar.markdown('<div class="main-header">HR Automation Tool</div>', unsafe_allow_html=True)

# Helper functions
def run_async(func, *args, **kwargs):
    """Run an async function from Streamlit's synchronous environment."""
    loop = asyncio.new_event_loop()
    result = loop.run_until_complete(func(*args, **kwargs))
    loop.close()
    return result

def display_conversation_history(conversation_history):
    """Display the conversation history in a chat-like interface."""
    for msg in conversation_history:
        role = msg.get("role", "")
        content = msg.get("content", "")
        
        if role == "system":
            continue  # Skip system messages
        elif role == "assistant":
            st.markdown(f'<div class="card"><strong>Interviewer:</strong> {content}</div>', unsafe_allow_html=True)
        elif role == "user":
            st.markdown(f'<div class="card" style="background-color: #e3f2fd;"><strong>Candidate:</strong> {content}</div>', unsafe_allow_html=True)

def display_evaluation_report(report):
    """Display the evaluation report in a structured format."""
    if not report:
        st.warning("No evaluation report available.")
        return
    
    # Extract key information from the report
    scenario = report.get("scenario", {})
    final_summary = report.get("final_summary", {})
    detailed_evaluations = report.get("detailed_evaluations", {})
    overall_evaluation = report.get("overall_evaluation", {})
    
    # Display scenario information
    st.markdown('<div class="sub-header">Scenario Information</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="card">'
                f'<strong>Title:</strong> {scenario.get("title", "N/A")}<br>'
                f'<strong>Description:</strong> {scenario.get("description", "N/A")}<br>'
                f'<strong>Difficulty:</strong> {scenario.get("difficulty", "N/A")}<br>'
                f'<strong>Topics:</strong> {", ".join(scenario.get("topics", []))}'
                f'</div>', unsafe_allow_html=True)
    
    # Display overall evaluation
    st.markdown('<div class="sub-header">Overall Evaluation</div>', unsafe_allow_html=True)
    
    # Create a radar chart for the scores
    if overall_evaluation:
        scores = {
            "Technical Skills": overall_evaluation.get("technical_skills_score", 0),
            "Communication": overall_evaluation.get("communication_score", 0),
            "Problem Solving": overall_evaluation.get("problem_solving_score", 0),
            "Domain Knowledge": overall_evaluation.get("domain_knowledge_score", 0),
            "Overall": overall_evaluation.get("overall_score", 0)
        }
        
        # Display scores as a bar chart
        st.bar_chart(scores)
        
        # Display recommendation
        recommendation = overall_evaluation.get("hiring_recommendation", "No recommendation available.")
        st.markdown(f'<div class="highlight"><strong>Recommendation:</strong> {recommendation}</div>', unsafe_allow_html=True)
        
        # Display strengths and improvement areas
        st.markdown('<strong>Key Strengths:</strong>', unsafe_allow_html=True)
        for strength in overall_evaluation.get("key_strengths", []):
            st.markdown(f"- {strength}")
        
        st.markdown('<strong>Areas for Improvement:</strong>', unsafe_allow_html=True)
        for area in overall_evaluation.get("improvement_areas", []):
            st.markdown(f"- {area}")
        
        # Display reasoning
        st.markdown('<strong>Reasoning:</strong>', unsafe_allow_html=True)
        st.markdown(overall_evaluation.get("reasoning", "No reasoning available."))
    
    # Display final summary
    # st.markdown('<div class="sub-header">Interview Summary</div>', unsafe_allow_html=True)
    # st.markdown(f'<div class="card">{final_summary}</div>', unsafe_allow_html=True)
    
    # Display detailed evaluations
    st.markdown('<div class="sub-header">Detailed Evaluations</div>', unsafe_allow_html=True)
    
    for question_id, evaluation in detailed_evaluations.items():
        # Find the question text from the scenario
        question_text = "Unknown question"
        for q in scenario.get("questions", []):
            if q.get("id") == question_id:
                question_text = q.get("question", "Unknown question")
                break
        
        # Create an expander for each question
        with st.expander(f"Question: {question_text}"):
            # Display scores
            scores = {
                "Relevance": evaluation.get("relevance_score", 0),
                "Completeness": evaluation.get("completeness_score", 0),
                "Clarity": evaluation.get("clarity_score", 0),
                "Technical Accuracy": evaluation.get("technical_accuracy_score", 0),
                "Professional Tone": evaluation.get("professional_tone_score", 0),
                "Grammar": evaluation.get("grammar_score", 0),
                "Vocabulary": evaluation.get("vocabulary_score", 0)
            }
            
            # Display scores as a bar chart
            st.bar_chart(scores)
            
            # Display strengths and weaknesses
            st.markdown('<strong>Strengths:</strong>', unsafe_allow_html=True)
            for strength in evaluation.get("strengths", []):
                st.markdown(f"- {strength}")
            
            st.markdown('<strong>Weaknesses:</strong>', unsafe_allow_html=True)
            for weakness in evaluation.get("weaknesses", []):
                st.markdown(f"- {weakness}")
            
            # Display reasoning
            st.markdown('<strong>Reasoning:</strong>', unsafe_allow_html=True)
            st.markdown(evaluation.get("reasoning", "No reasoning available."))

# Page: Start New Interview
def show_start_new_interview():
    st.markdown('<div class="main-header">Start a New Technical Interview</div>', unsafe_allow_html=True)
    try:
        # Get all available scenarios
        try:
            scenarios = get_all_scenarios()
            logger.info(f"Successfully retrieved {len(scenarios)} scenarios")
        except Exception as e:
            logger.error(f"Error getting scenarios: {str(e)}")
            st.error(f"Failed to get scenarios: {str(e)}")
            scenarios = []
        
        if not scenarios:
            st.error("No scenarios available. Please check the data directory.")
            st.stop()
        
        # Create a form for starting a new interview
        with st.form("new_interview_form"):
            st.markdown('<div class="sub-header">Select Interview Parameters</div>', unsafe_allow_html=True)
            
            try:
                # Scenario selection
                scenario_options = {f"{s['id']} - {s['title']}": s['id'] for s in scenarios}
                selected_scenario = st.selectbox("Select a scenario", list(scenario_options.keys()))
                scenario_id = scenario_options[selected_scenario]
                
                # Display scenario details
                try:
                    scenario = get_scenario_by_id(scenario_id)
                    logger.info(f"Retrieved scenario details for {scenario_id}")
                except Exception as e:
                    logger.error(f"Error getting scenario details for {scenario_id}: {str(e)}")
                    st.error(f"Failed to get scenario details: {str(e)}")
                    scenario = None
                
                if scenario:
                    st.markdown('<div class="card">'
                                f'<strong>Title:</strong> {scenario.get("title", "N/A")}<br>'
                                f'<strong>Description:</strong> {scenario.get("description", "N/A")}<br>'
                                f'<strong>Difficulty:</strong> {scenario.get("difficulty", "N/A")}<br>'
                                f'<strong>Topics:</strong> {", ".join(scenario.get("topics", []))}<br>'
                                f'<strong>Number of Questions:</strong> {len(scenario.get("questions", []))}'
                                f'</div>', unsafe_allow_html=True)
            except Exception as e:
                logger.error(f"Error setting up scenario selection: {str(e)}")
                st.error(f"Error setting up scenario selection: {str(e)}")
                st.stop()
            
            # Candidate information
            st.markdown('<div class="sub-header">Candidate Information</div>', unsafe_allow_html=True)
            candidate_name = st.text_input("Candidate Name")
            candidate_email = st.text_input("Candidate Email")
            candidate_position = st.text_input("Position Applied For")
            
            # Submit button
            submit_button = st.form_submit_button("Start Interview")
            
            if submit_button:
                if not candidate_name:
                    st.error("Please enter the candidate's name.")
                else:
                    try:
                        # Create metadata
                        metadata = {
                            "candidate_name": candidate_name,
                            "candidate_email": candidate_email,
                            "candidate_position": candidate_position,
                            "interview_date": datetime.now().isoformat()
                        }
                        
                        # Start the interview session
                        with st.spinner("Starting interview session..."):
                            try:
                                session_info = run_async(start_interview_session, scenario_id, metadata)
                                logger.info(f"Started interview session with scenario {scenario_id}")
                            except Exception as e:
                                logger.error(f"Error starting interview session: {str(e)}")
                                st.error(f"Failed to start interview: {str(e)}")
                                session_info = {"error": str(e)}

                        if "error" in session_info:
                            st.error(f"Failed to start interview: {session_info['error']}")
                        else:
                            try:
                                session_id = session_info["session_id"]
                                st.session_state.current_session_id = session_id
                                st.session_state.active_sessions[session_id] = {
                                    "session_info": session_info,
                                    "metadata": metadata,
                                    "scenario": scenario
                                }
                                st.session_state.interview_complete = False
                                st.session_state.evaluation_report = None

                                st.success(f"Interview session started successfully! Session ID: {session_id}")
                                st.markdown('<div class="highlight">Navigate to "Active Interviews" to continue the interview.</div>', unsafe_allow_html=True)
                                logger.info(f"Successfully started interview session {session_id}")
                            except Exception as e:
                                logger.error(f"Error setting up session state: {str(e)}")
                                st.error(f"Interview started but failed to set up session: {str(e)}")
                    except Exception as e:
                        logger.error(f"Error processing form submission: {str(e)}")
                        st.error(f"Error processing form submission: {str(e)}")
    except Exception as e:
        logger.error(f"Unhandled error in Start New Interview page: {str(e)}")
        st.error(f"An unexpected error occurred: {str(e)}")
        # Display detailed error information in development mode
        import traceback
        st.code(traceback.format_exc(), language="python")

# Page: Active Interviews
def show_active_interviews():
    st.markdown('<div class="main-header">Active Interviews</div>', unsafe_allow_html=True)

    if not st.session_state.active_sessions:
        st.info("No active interviews. Start a new interview from the 'Start New Interview' page.")
        return

    try:
        # Select an active session
        session_options = {}
        for session_id, session_data in st.session_state.active_sessions.items():
            try:
                metadata = session_data.get("metadata", {})
                scenario = session_data.get("scenario", {})
                session_options[f"{metadata.get('candidate_name', 'Unknown')} - {scenario.get('title', 'Unknown')}"] = session_id
            except Exception as e:
                logger.error(f"Error processing session {session_id} for selection: {str(e)}")
                continue

        if not session_options:
            st.warning("Could not process any active interviews. Please start a new interview.")
            return

        selected_session = st.selectbox("Select an active interview", list(session_options.keys()))
        session_id = session_options[selected_session]

        # Display interview information and handle responses
        try:
            # Get the session data
            session_data = st.session_state.active_sessions[session_id]
            session_info = session_data["session_info"]
            metadata = session_data["metadata"]
            scenario = session_data["scenario"]

            # Display session information
            st.markdown('<div class="sub-header">Interview Information</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="card">'
                        f'<strong>Candidate:</strong> {metadata.get("candidate_name", "Unknown")}<br>'
                        f'<strong>Position:</strong> {metadata.get("candidate_position", "Unknown")}<br>'
                        f'<strong>Scenario:</strong> {scenario.get("title", "Unknown")}<br>'
                        f'<strong>Session ID:</strong> {session_id}<br>'
                        f'<strong>Interview Date:</strong> {metadata.get("interview_date", "Unknown")}'
                        f'</div>', unsafe_allow_html=True)

            # Display conversation history
            st.markdown('<div class="sub-header">Conversation History</div>', unsafe_allow_html=True)
            display_conversation_history(session_info.get("conversation_history", []))

            # Handle interview status and responses
            if st.session_state.interview_complete:
                st.markdown('<div class="success-message">Interview completed! View the evaluation report below.</div>', unsafe_allow_html=True)
                if st.session_state.evaluation_report:
                    display_evaluation_report(st.session_state.evaluation_report)
                else:
                    st.warning("Evaluation report not available yet.")
            else:
                # Show current question and response form
                st.markdown('<div class="sub-header">Candidate Response</div>', unsafe_allow_html=True)
                current_question = session_info.get("current_question", {})
                question_text = current_question.get("question", "No question available.")
                st.markdown(f'<div class="highlight"><strong>Current Question:</strong> {question_text}</div>', unsafe_allow_html=True)

                if session_info.get("awaiting_clarification", False):
                    st.markdown('<div class="info-text">The system is awaiting clarification for the previous response.</div>', unsafe_allow_html=True)

                # Response input form
                with st.form("response_form"):
                    response = st.text_area("Enter the candidate's response", height=200)
                    submit_response = st.form_submit_button("Submit Response")

                    if submit_response:
                        if not response:
                            st.error("Please enter a response.")
                        else:
                            try:
                                with st.spinner("Processing response..."):
                                    result = run_async(process_response, session_id, response)
                                    logger.info(f"Processed response for session {session_id}")

                                    if result.get("status") == "completed":
                                        st.session_state.interview_complete = True
                                        st.session_state.evaluation_report = result.get("report")
                                        st.session_state.active_sessions[session_id]["session_info"] = result
                                        st.success("Interview completed successfully!")
                                        st.rerun()
                                    else:
                                        st.session_state.active_sessions[session_id]["session_info"] = result
                                        st.success("Response processed successfully!")
                                        st.rerun()
                            except Exception as e:
                                logger.error(f"Error processing response: {str(e)}")
                                st.error(f"Failed to process response: {str(e)}")

        except Exception as e:
            logger.error(f"Error handling interview session: {str(e)}")
            st.error(f"Error handling interview session: {str(e)}")

    except Exception as e:
        logger.error(f"Error in active interviews page: {str(e)}")
        st.error(f"An unexpected error occurred: {str(e)}")
        import traceback
        st.code(traceback.format_exc(), language="python")

# Page: Completed Interviews
def show_completed_interviews():
    st.markdown('<div class="main-header">Completed Interviews</div>', unsafe_allow_html=True)

    try:
        # Get all sessions
        with st.spinner("Loading completed interviews..."):
            try:
                all_sessions = get_sessions(limit=100)
                logger.info("Successfully retrieved sessions")
            except Exception as e:
                logger.error(f"Error getting sessions: {str(e)}")
                st.error(f"Failed to get sessions: {str(e)}")
                all_sessions = {"error": str(e)}

        if "error" in all_sessions:
            st.error(f"Failed to get sessions: {all_sessions['error']}")
            return

        sessions = all_sessions.get("sessions", [])
        completed_sessions = [s for s in sessions if s.get("status") == "completed"]

        if not completed_sessions:
            st.info("No completed interviews found.")
            return

        # Create a table of completed interviews
        st.markdown('<div class="sub-header">Completed Interviews</div>', unsafe_allow_html=True)

        # Create a dataframe for the table
        import pandas as pd

        data = []
        for session in completed_sessions:
            try:
                metadata_value = session.get("metadata", "{}")
                # Check if metadata is already a dictionary
                if isinstance(metadata_value, dict):
                    metadata = metadata_value
                else:
                    metadata = json.loads(metadata_value)

                data.append({
                    "Session ID": session.get("session_id", "Unknown"),
                    "Candidate": metadata.get("candidate_name", "Unknown"),
                    "Position": metadata.get("candidate_position", "Unknown"),
                    "Date": session.get("start_time", "Unknown"),
                    "Scenario ID": session.get("scenario_id", "Unknown")
                })
            except Exception as e:
                logger.error(f"Error processing session {session.get('session_id', 'Unknown')}: {str(e)}")
                continue

        if not data:
            st.warning("Could not process any completed interviews due to data format issues.")
            return

        df = pd.DataFrame(data)
        st.dataframe(df)

        # Select a session to view details
        session_ids = [s.get("session_id") for s in completed_sessions]
        if session_ids:
            selected_session_id = st.selectbox("Select a session to view details", session_ids)

            if selected_session_id:
                try:
                    # Get session details
                    with st.spinner("Loading session details..."):
                        session_info = get_session_info(selected_session_id)

                    if "error" in session_info:
                        st.error(f"Failed to get session info: {session_info['error']}")
                        return

                    # Display session information
                    session = session_info.get("session", {})
                    metadata_value = session.get("metadata", "{}")
                    # Check if metadata is already a dictionary
                    if isinstance(metadata_value, dict):
                        metadata = metadata_value
                    else:
                        metadata = json.loads(metadata_value)

                    st.markdown('<div class="sub-header">Interview Details</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="card">'
                                f'<strong>Candidate:</strong> {metadata.get("candidate_name", "Unknown")}<br>'
                                f'<strong>Position:</strong> {metadata.get("candidate_position", "Unknown")}<br>'
                                f'<strong>Scenario ID:</strong> {session.get("scenario_id", "Unknown")}<br>'
                                f'<strong>Interview Date:</strong> {session.get("start_time", "Unknown")}<br>'
                                f'<strong>Status:</strong> {session.get("status", "Unknown")}'
                                f'</div>', unsafe_allow_html=True)

                    # Display report
                    report = session_info.get("report")
                    if report:
                        display_evaluation_report(report)
                    else:
                        st.warning("No evaluation report available for this session.")

                    # Export button
                    if st.button("Export Report"):
                        try:
                            with st.spinner("Exporting report..."):
                                export_result = export_session_data(selected_session_id)

                            if "error" in export_result:
                                st.error(f"Failed to export report: {export_result['error']}")
                            else:
                                export_path = export_result.get("export_path")
                                st.success(f"Report exported successfully to: {export_path}")
                        except Exception as e:
                            logger.error(f"Error exporting report: {str(e)}")
                            st.error(f"Failed to export report: {str(e)}")

                except Exception as e:
                    logger.error(f"Error handling session details: {str(e)}")
                    st.error(f"Error handling session details: {str(e)}")

    except Exception as e:
        logger.error(f"Error in completed interviews page: {str(e)}")
        st.error(f"An unexpected error occurred: {str(e)}")
        import traceback
        st.code(traceback.format_exc(), language="python")

# Page: About
def show_about_page():
    logger.info("Displaying About page")
    st.markdown('<div class="main-header">About HR Automation Tool</div>', unsafe_allow_html=True)

    try:
        st.markdown("""
        <div class="card">
        <p>The HR Automation Tool is a comprehensive solution for conducting technical interviews and evaluating candidates. It uses advanced AI techniques to analyze responses, generate evaluations, and provide detailed reports.</p>
        
        <h3>Key Features:</h3>
        <ul>
            <li>Scenario-based technical interviews</li>
            <li>Dynamic conversation flow with clarification questions</li>
            <li>Comprehensive evaluation of responses</li>
            <li>Detailed reports with scores and recommendations</li>
            <li>Export functionality for sharing and archiving</li>
        </ul>
        
        <h3>How to Use:</h3>
        <ol>
            <li>Start a new interview from the "Start New Interview" page</li>
            <li>Select a scenario and enter candidate information</li>
            <li>Navigate to "Active Interviews" to conduct the interview</li>
            <li>Submit candidate responses to each question</li>
            <li>View the evaluation report after the interview is complete</li>
            <li>Export the report for sharing or archiving</li>
        </ol>
        </div>
        """, unsafe_allow_html=True)
        logger.info("Displayed main information card")
    except Exception as e:
        logger.error(f"Error displaying main information card: {str(e)}")
        st.error(f"Error displaying information: {str(e)}")

    try:
        st.markdown('<div class="sub-header">Technical Details</div>', unsafe_allow_html=True)

        st.markdown("""
        <div class="card">
        <p>The HR Automation Tool is built using the following technologies:</p>
        <ul>
            <li>Streamlit for the user interface</li>
            <li>LangChain for the conversational engine</li>
            <li>LangGraph for orchestration and dynamic flow</li>
            <li>SQLite for persistent storage</li>
            <li>Advanced LLMs for response analysis and evaluation</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
        logger.info("Displayed technical details card")
    except Exception as e:
        logger.error(f"Error displaying technical details: {str(e)}")
        st.error(f"Error displaying technical details: {str(e)}")

def login_page():
    st.title("Welcome to Recruitment Bot")

    # Create a clean layout with columns
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.subheader("Please Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        login_button = st.button("Login")

        if login_button:
            if username in USERS and USERS[username]["password"] == password:
                st.session_state["user"] = username
                st.session_state["role"] = USERS[username]["role"]
                st.success(f"Welcome {username}!")
                st.rerun()
            else:
                st.error("Invalid username or password")

def main():
    # Initialize session state first
    init_session_state()

    # Check login status before anything else
    if not st.session_state["user"]:
        login_page()
        return

    # Only show the rest of the app if logged in
    with st.sidebar:
        st.write(f"Logged in as: {st.session_state['user']}")
        if st.button("Logout"):
            st.session_state["user"] = None
            st.session_state["role"] = None
            st.rerun()

    # Show navigation only after login
    page = st.sidebar.radio("Navigation", ["Start New Interview", "Active Interviews", "Completed Interviews", "About"])

    # Rest of your application code...
    if page == "Start New Interview":
        show_start_new_interview()
    elif page == "Active Interviews":
        show_active_interviews()
    elif page == "Completed Interviews":
        show_completed_interviews()
    else:
        show_about_page()

if __name__ == "__main__":
    main()
