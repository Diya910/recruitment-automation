from typing import Dict, List, Any, Optional, Union
from loguru import logger
import json
import os
import sqlite3
from datetime import datetime
import uuid

# Global variables
_db_path = None
_db_connection = None

def initialize_storage_system(db_path: str = None) -> None:
    """
    Initialize the storage system.
    
    Args:
        db_path: Path to the SQLite database file. If None, uses a default path.
    """
    global _db_path
    
    # Set default database path if not provided
    if db_path is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        db_path = os.path.join(base_dir, "data", "interviews.db")
    
    _db_path = db_path
    _initialize_database()

def _initialize_database() -> None:
    """Initialize the database schema if it doesn't exist."""
    global _db_path
    
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(_db_path), exist_ok=True)
        
        # Connect to the database
        conn = sqlite3.connect(_db_path)
        cursor = conn.cursor()
        
        # Create tables if they don't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            scenario_id TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT,
            status TEXT NOT NULL,
            metadata TEXT
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS responses (
            response_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            question_id TEXT NOT NULL,
            response_text TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions (session_id)
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS evaluations (
            evaluation_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            evaluation_type TEXT NOT NULL,
            evaluation_data TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions (session_id)
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            report_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            report_data TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions (session_id)
        )
        ''')
        
        # Commit changes and close connection
        conn.commit()
        conn.close()
        
        logger.info(f"Initialized database at {_db_path}")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise

def create_session(scenario_id: str, metadata: Optional[Dict[str, Any]] = None) -> str:
    """
    Create a new interview session.
    
    Args:
        scenario_id: ID of the scenario being used
        metadata: Optional metadata about the session
        
    Returns:
        The session ID
    """
    global _db_path
    
    try:
        session_id = str(uuid.uuid4())
        start_time = datetime.now().isoformat()
        
        # Connect to the database
        conn = sqlite3.connect(_db_path)
        cursor = conn.cursor()
        
        # Insert the session
        cursor.execute(
            "INSERT INTO sessions (session_id, scenario_id, start_time, status, metadata) VALUES (?, ?, ?, ?, ?)",
            (
                session_id,
                scenario_id,
                start_time,
                "started",
                json.dumps(metadata or {})
            )
        )
        
        # Commit changes and close connection
        conn.commit()
        conn.close()
        
        logger.info(f"Created new session {session_id} for scenario {scenario_id}")
        return session_id
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}")
        raise

def update_session_status(session_id: str, status: str, end_time: Optional[str] = None) -> None:
    """
    Update the status of a session.
    
    Args:
        session_id: The session ID
        status: The new status (e.g., "completed", "aborted")
        end_time: Optional end time. If None, uses current time.
    """
    global _db_path
    
    try:
        if end_time is None:
            end_time = datetime.now().isoformat()
        
        # Connect to the database
        conn = sqlite3.connect(_db_path)
        cursor = conn.cursor()
        
        # Update the session
        cursor.execute(
            "UPDATE sessions SET status = ?, end_time = ? WHERE session_id = ?",
            (status, end_time, session_id)
        )
        
        # Commit changes and close connection
        conn.commit()
        conn.close()
        
        logger.info(f"Updated session {session_id} status to {status}")
    except Exception as e:
        logger.error(f"Error updating session status: {str(e)}")
        raise

def store_response(session_id: str, question_id: str, response_text: str) -> str:
    """
    Store a candidate's response.
    
    Args:
        session_id: The session ID
        question_id: The question ID
        response_text: The candidate's response
        
    Returns:
        The response ID
    """
    global _db_path
    
    try:
        response_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        # Connect to the database
        conn = sqlite3.connect(_db_path)
        cursor = conn.cursor()
        
        # Insert the response
        cursor.execute(
            "INSERT INTO responses (response_id, session_id, question_id, response_text, timestamp) VALUES (?, ?, ?, ?, ?)",
            (
                response_id,
                session_id,
                question_id,
                response_text,
                timestamp
            )
        )
        
        # Commit changes and close connection
        conn.commit()
        conn.close()
        
        logger.info(f"Stored response {response_id} for session {session_id}, question {question_id}")
        return response_id
    except Exception as e:
        logger.error(f"Error storing response: {str(e)}")
        raise

def store_evaluation(session_id: str, evaluation_type: str, evaluation_data: Dict[str, Any]) -> str:
    """
    Store an evaluation.
    
    Args:
        session_id: The session ID
        evaluation_type: Type of evaluation (e.g., "detailed", "overall")
        evaluation_data: The evaluation data
        
    Returns:
        The evaluation ID
    """
    global _db_path
    
    try:
        evaluation_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        # Connect to the database
        conn = sqlite3.connect(_db_path)
        cursor = conn.cursor()
        
        # Insert the evaluation
        cursor.execute(
            "INSERT INTO evaluations (evaluation_id, session_id, evaluation_type, evaluation_data, timestamp) VALUES (?, ?, ?, ?, ?)",
            (
                evaluation_id,
                session_id,
                evaluation_type,
                json.dumps(evaluation_data),
                timestamp
            )
        )
        
        # Commit changes and close connection
        conn.commit()
        conn.close()
        
        logger.info(f"Stored {evaluation_type} evaluation {evaluation_id} for session {session_id}")
        return evaluation_id
    except Exception as e:
        logger.error(f"Error storing evaluation: {str(e)}")
        raise

def store_report(session_id: str, report_data: Dict[str, Any]) -> str:
    """
    Store a final report.
    
    Args:
        session_id: The session ID
        report_data: The report data
        
    Returns:
        The report ID
    """
    global _db_path
    
    try:
        report_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        # Connect to the database
        conn = sqlite3.connect(_db_path)
        cursor = conn.cursor()
        
        # Insert the report
        cursor.execute(
            "INSERT INTO reports (report_id, session_id, report_data, timestamp) VALUES (?, ?, ?, ?)",
            (
                report_id,
                session_id,
                json.dumps(report_data),
                timestamp
            )
        )
        
        # Commit changes and close connection
        conn.commit()
        conn.close()
        
        logger.info(f"Stored report {report_id} for session {session_id}")
        return report_id
    except Exception as e:
        logger.error(f"Error storing report: {str(e)}")
        raise

def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a session by ID.
    
    Args:
        session_id: The session ID
        
    Returns:
        The session data, or None if not found
    """
    global _db_path
    
    try:
        # Connect to the database
        conn = sqlite3.connect(_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Query the session
        cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()
        
        if not row:
            logger.warning(f"Session {session_id} not found")
            return None
        
        # Convert row to dict
        session = dict(row)
        
        # Parse metadata
        if session.get("metadata"):
            session["metadata"] = json.loads(session["metadata"])
        
        # Close connection
        conn.close()
        
        return session
    except Exception as e:
        logger.error(f"Error getting session: {str(e)}")
        raise

def get_session_responses(session_id: str) -> List[Dict[str, Any]]:
    """
    Get all responses for a session.
    
    Args:
        session_id: The session ID
        
    Returns:
        List of responses
    """
    global _db_path
    
    try:
        # Connect to the database
        conn = sqlite3.connect(_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Query the responses
        cursor.execute("SELECT * FROM responses WHERE session_id = ? ORDER BY timestamp", (session_id,))
        rows = cursor.fetchall()
        
        # Convert rows to dicts
        responses = [dict(row) for row in rows]
        
        # Close connection
        conn.close()
        
        return responses
    except Exception as e:
        logger.error(f"Error getting session responses: {str(e)}")
        raise

def get_session_evaluations(session_id: str) -> List[Dict[str, Any]]:
    """
    Get all evaluations for a session.
    
    Args:
        session_id: The session ID
        
    Returns:
        List of evaluations
    """
    global _db_path
    
    try:
        # Connect to the database
        conn = sqlite3.connect(_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Query the evaluations
        cursor.execute("SELECT * FROM evaluations WHERE session_id = ? ORDER BY timestamp", (session_id,))
        rows = cursor.fetchall()
        
        # Convert rows to dicts and parse evaluation data
        evaluations = []
        for row in rows:
            evaluation = dict(row)
            if evaluation.get("evaluation_data"):
                evaluation["evaluation_data"] = json.loads(evaluation["evaluation_data"])
            evaluations.append(evaluation)
        
        # Close connection
        conn.close()
        
        return evaluations
    except Exception as e:
        logger.error(f"Error getting session evaluations: {str(e)}")
        raise

def get_session_report(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the report for a session.
    
    Args:
        session_id: The session ID
        
    Returns:
        The report data, or None if not found
    """
    global _db_path
    
    try:
        # Connect to the database
        conn = sqlite3.connect(_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Query the report
        cursor.execute("SELECT * FROM reports WHERE session_id = ? ORDER BY timestamp DESC LIMIT 1", (session_id,))
        row = cursor.fetchone()
        
        if not row:
            logger.warning(f"No report found for session {session_id}")
            return None
        
        # Convert row to dict and parse report data
        report = dict(row)
        if report.get("report_data"):
            report["report_data"] = json.loads(report["report_data"])
        
        # Close connection
        conn.close()
        
        return report
    except Exception as e:
        logger.error(f"Error getting session report: {str(e)}")
        raise

def get_all_sessions(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """
    Get all sessions with pagination.
    
    Args:
        limit: Maximum number of sessions to return
        offset: Offset for pagination
        
    Returns:
        List of sessions
    """
    global _db_path
    
    try:
        # Connect to the database
        conn = sqlite3.connect(_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Query the sessions
        cursor.execute("SELECT * FROM sessions ORDER BY start_time DESC LIMIT ? OFFSET ?", (limit, offset))
        rows = cursor.fetchall()
        
        # Convert rows to dicts and parse metadata
        sessions = []
        for row in rows:
            session = dict(row)
            if session.get("metadata"):
                session["metadata"] = json.loads(session["metadata"])
            sessions.append(session)
        
        # Close connection
        conn.close()
        
        return sessions
    except Exception as e:
        logger.error(f"Error getting all sessions: {str(e)}")
        raise

def search_sessions(query: str, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Search for sessions by scenario ID or metadata.
    
    Args:
        query: Search query
        limit: Maximum number of sessions to return
        
    Returns:
        List of matching sessions
    """
    global _db_path
    
    try:
        # Connect to the database
        conn = sqlite3.connect(_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Query the sessions
        cursor.execute(
            "SELECT * FROM sessions WHERE scenario_id LIKE ? OR metadata LIKE ? ORDER BY start_time DESC LIMIT ?",
            (f"%{query}%", f"%{query}%", limit)
        )
        rows = cursor.fetchall()
        
        # Convert rows to dicts and parse metadata
        sessions = []
        for row in rows:
            session = dict(row)
            if session.get("metadata"):
                session["metadata"] = json.loads(session["metadata"])
            sessions.append(session)
        
        # Close connection
        conn.close()
        
        return sessions
    except Exception as e:
        logger.error(f"Error searching sessions: {str(e)}")
        raise

def get_complete_session_data(session_id: str) -> Dict[str, Any]:
    """
    Get complete data for a session, including responses, evaluations, and report.
    
    Args:
        session_id: The session ID
        
    Returns:
        Complete session data
    """
    try:
        # Get session data
        session = get_session(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found")
            return {}
        
        # Get responses, evaluations, and report
        responses = get_session_responses(session_id)
        evaluations = get_session_evaluations(session_id)
        report = get_session_report(session_id)
        
        # Combine all data
        complete_data = {
            "session": session,
            "responses": responses,
            "evaluations": evaluations,
            "report": report["report_data"] if report else None
        }
        
        return complete_data
    except Exception as e:
        logger.error(f"Error getting complete session data: {str(e)}")
        raise

def export_session_to_json(session_id: str, output_path: Optional[str] = None) -> str:
    """
    Export a session to a JSON file.
    
    Args:
        session_id: The session ID
        output_path: Optional output path. If None, generates a path based on session ID.
        
    Returns:
        Path to the exported file
    """
    try:
        # Get complete session data
        data = get_complete_session_data(session_id)
        
        # Generate output path if not provided
        if output_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            exports_dir = os.path.join(base_dir, "exports")
            os.makedirs(exports_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(exports_dir, f"session_{session_id}_{timestamp}.json")
        
        # Write to file
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Exported session {session_id} to {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Error exporting session: {str(e)}")
        raise

# Initialize the storage system when the module is imported
initialize_storage_system()