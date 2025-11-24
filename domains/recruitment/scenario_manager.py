import json
import random
import os
from typing import List, Dict, Any, Optional, Union
from loguru import logger
from datetime import datetime

# Global variable to store loaded scenarios
_scenarios = []
_scenarios_path = None

def initialize_scenario_manager(scenarios_path: str = None) -> None:
    """
    Initialize the scenario manager.
    
    Args:
        scenarios_path: Path to the scenarios JSON file. If None, uses default path.
    """
    global _scenarios_path, _scenarios
    
    _scenarios_path = scenarios_path or os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
        "data", 
        "scenarios.json"
    )
    
    load_scenarios()

def load_scenarios() -> None:
    """
    Load scenarios from the JSON file.
    """
    global _scenarios, _scenarios_path
    
    try:
        with open(_scenarios_path, 'r') as file:
            data = json.load(file)
            _scenarios = data.get('scenarios', [])
            
        # Add version and timestamp if not present
        for scenario in _scenarios:
            if 'version' not in scenario:
                scenario['version'] = '1.0'
            if 'last_updated' not in scenario:
                scenario['last_updated'] = datetime.now().isoformat()
                
        logger.info(f"Loaded {len(_scenarios)} scenarios from {_scenarios_path}")
    except Exception as e:
        logger.error(f"Error loading scenarios: {str(e)}")
        _scenarios = []

def get_all_scenarios() -> List[Dict[str, Any]]:
    """
    Get all available scenarios.
    
    Returns:
        List of all scenarios.
    """
    return _scenarios

def get_scenario_by_id(scenario_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific scenario by ID.
    
    Args:
        scenario_id: The ID of the scenario to retrieve.
        
    Returns:
        The scenario if found, None otherwise.
    """
    for scenario in _scenarios:
        if scenario.get('id') == scenario_id:
            return scenario
    logger.warning(f"Scenario with ID {scenario_id} not found")
    return None

def select_random_scenario() -> Optional[Dict[str, Any]]:
    """
    Select a random scenario.
    
    Returns:
        A randomly selected scenario, or None if no scenarios are available.
    """
    if not _scenarios:
        logger.warning("No scenarios available to select from")
        return None
    
    selected = random.choice(_scenarios)
    logger.info(f"Randomly selected scenario: {selected.get('id')} - {selected.get('title')}")
    return selected

def select_random_scenarios(count: int = 1) -> List[Dict[str, Any]]:
    """
    Select multiple random scenarios.
    
    Args:
        count: Number of scenarios to select.
        
    Returns:
        List of randomly selected scenarios.
    """
    if not _scenarios:
        logger.warning("No scenarios available to select from")
        return []
    
    # Ensure we don't try to select more scenarios than are available
    count = min(count, len(_scenarios))
    
    # Select random scenarios without replacement
    selected = random.sample(_scenarios, count)
    
    scenario_ids = [s.get('id') for s in selected]
    logger.info(f"Randomly selected {count} scenarios: {', '.join(scenario_ids)}")
    
    return selected

def filter_scenarios_by_tags(tags: List[str]) -> List[Dict[str, Any]]:
    """
    Filter scenarios by tags.
    
    Args:
        tags: List of tags to filter by.
        
    Returns:
        List of scenarios that match the given tags.
    """
    if not tags:
        return _scenarios
    
    filtered = []
    for scenario in _scenarios:
        scenario_topics = scenario.get('topics', [])
        # Check if any of the specified tags match the scenario's topics
        if any(tag in scenario_topics for tag in tags):
            filtered.append(scenario)
    
    logger.info(f"Filtered scenarios by tags {tags}, found {len(filtered)} matches")
    return filtered

def filter_scenarios_by_difficulty(difficulty: str) -> List[Dict[str, Any]]:
    """
    Filter scenarios by difficulty level.
    
    Args:
        difficulty: Difficulty level to filter by (e.g., 'easy', 'medium', 'hard').
        
    Returns:
        List of scenarios with the specified difficulty.
    """
    filtered = [s for s in _scenarios if s.get('difficulty') == difficulty]
    logger.info(f"Filtered scenarios by difficulty {difficulty}, found {len(filtered)} matches")
    return filtered

def get_random_question_from_scenario(scenario_id: str) -> Optional[Dict[str, str]]:
    """
    Get a random question from a specific scenario.
    
    Args:
        scenario_id: ID of the scenario to get a question from.
        
    Returns:
        A randomly selected question, or None if the scenario is not found or has no questions.
    """
    scenario = get_scenario_by_id(scenario_id)
    if not scenario:
        return None
    
    questions = scenario.get('questions', [])
    if not questions:
        logger.warning(f"No questions found in scenario {scenario_id}")
        return None
    
    question = random.choice(questions)
    logger.info(f"Selected random question {question.get('id')} from scenario {scenario_id}")
    return question

def save_scenarios(scenarios_path: str = None) -> bool:
    """
    Save scenarios to a JSON file.
    
    Args:
        scenarios_path: Path to save the scenarios. If None, uses the current path.
        
    Returns:
        True if successful, False otherwise.
    """
    global _scenarios_path
    
    path = scenarios_path or _scenarios_path
    try:
        with open(path, 'w') as file:
            json.dump({'scenarios': _scenarios}, file, indent=4)
        logger.info(f"Saved {len(_scenarios)} scenarios to {path}")
        return True
    except Exception as e:
        logger.error(f"Error saving scenarios: {str(e)}")
        return False

def add_scenario(scenario: Dict[str, Any]) -> bool:
    """
    Add a new scenario.
    
    Args:
        scenario: The scenario to add.
        
    Returns:
        True if successful, False otherwise.
    """
    global _scenarios
    
    # Validate required fields
    required_fields = ['id', 'title', 'description', 'questions']
    for field in required_fields:
        if field not in scenario:
            logger.error(f"Scenario is missing required field: {field}")
            return False
    
    # Check for duplicate ID
    if any(s.get('id') == scenario['id'] for s in _scenarios):
        logger.error(f"Scenario with ID {scenario['id']} already exists")
        return False
    
    # Add version and timestamp
    scenario['version'] = '1.0'
    scenario['last_updated'] = datetime.now().isoformat()
    
    _scenarios.append(scenario)
    logger.info(f"Added new scenario: {scenario['id']} - {scenario['title']}")
    
    # Save the updated scenarios
    return save_scenarios()

def update_scenario(scenario_id: str, updates: Dict[str, Any]) -> bool:
    """
    Update an existing scenario.
    
    Args:
        scenario_id: ID of the scenario to update.
        updates: Dictionary of fields to update.
        
    Returns:
        True if successful, False otherwise.
    """
    global _scenarios
    
    for i, scenario in enumerate(_scenarios):
        if scenario.get('id') == scenario_id:
            # Update version
            current_version = scenario.get('version', '1.0')
            try:
                major, minor = current_version.split('.')
                new_version = f"{major}.{int(minor) + 1}"
            except ValueError:
                new_version = '1.1'
            
            # Apply updates
            _scenarios[i].update(updates)
            _scenarios[i]['version'] = new_version
            _scenarios[i]['last_updated'] = datetime.now().isoformat()
            
            logger.info(f"Updated scenario {scenario_id} to version {new_version}")
            
            # Save the updated scenarios
            return save_scenarios()
    
    logger.warning(f"Scenario with ID {scenario_id} not found for update")
    return False

# Initialize the scenario manager when the module is imported
initialize_scenario_manager()