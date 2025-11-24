import json
import random
import os
from typing import List, Dict, Any, Optional, Union, Tuple
from loguru import logger
from datetime import datetime

# Global variables to store loaded scenarios
_scenarios = []
_new_scenarios = []
_scenarios_path = None
_new_scenarios_path = None

def initialize_scenario_manager(
    scenarios_path: str = None,
    new_scenarios_path: str = None
) -> None:
    """
    Initialize the scenario manager.
    
    Args:
        scenarios_path: Path to the traditional scenarios JSON file. If None, uses default path.
        new_scenarios_path: Path to the new format scenarios JSON file. If None, uses default path.
    """
    global _scenarios_path, _new_scenarios_path, _scenarios, _new_scenarios
    
    # Set default paths if not provided
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    
    _scenarios_path = scenarios_path or os.path.join(
        base_dir, 
        "data", 
        "scenarios.json"
    )
    
    _new_scenarios_path = new_scenarios_path or os.path.join(
        base_dir, 
        "data", 
        "new_scenarios.json"
    )
    
    # Load both types of scenarios
    load_scenarios()
    load_new_scenarios()
    
    logger.info(f"Scenario manager initialized with {len(_scenarios)} traditional scenarios and {len(_new_scenarios)} new format scenarios")

def load_scenarios() -> None:
    """
    Load traditional scenarios from the JSON file.
    """
    global _scenarios, _scenarios_path
    
    try:
        if os.path.exists(_scenarios_path):
            with open(_scenarios_path, 'r') as file:
                data = json.load(file)
                _scenarios = data.get('scenarios', [])
                
            # Add version and timestamp if not present
            for scenario in _scenarios:
                if 'version' not in scenario:
                    scenario['version'] = '1.0'
                if 'last_updated' not in scenario:
                    scenario['last_updated'] = datetime.now().isoformat()
                    
            logger.info(f"Loaded {len(_scenarios)} traditional scenarios from {_scenarios_path}")
        else:
            logger.warning(f"Traditional scenarios file not found at {_scenarios_path}")
            _scenarios = []
    except Exception as e:
        logger.error(f"Error loading traditional scenarios: {str(e)}")
        _scenarios = []

def load_new_scenarios() -> None:
    """
    Load new format scenarios from the JSON file.
    """
    global _new_scenarios, _new_scenarios_path
    
    try:
        if os.path.exists(_new_scenarios_path):
            with open(_new_scenarios_path, 'r') as file:
                data = json.load(file)
                _new_scenarios = data.get('scenarios', [])
                
            # Add version and timestamp if not present
            for scenario in _new_scenarios:
                if 'version' not in scenario:
                    scenario['version'] = '1.0'
                if 'last_updated' not in scenario:
                    scenario['last_updated'] = datetime.now().isoformat()
                    
            logger.info(f"Loaded {len(_new_scenarios)} new format scenarios from {_new_scenarios_path}")
        else:
            logger.warning(f"New format scenarios file not found at {_new_scenarios_path}")
            _new_scenarios = []
    except Exception as e:
        logger.error(f"Error loading new format scenarios: {str(e)}")
        _new_scenarios = []

def get_all_scenarios(include_new_format: bool = True) -> List[Dict[str, Any]]:
    """
    Get all available scenarios.
    
    Args:
        include_new_format: Whether to include new format scenarios.
        
    Returns:
        List of all scenarios.
    """
    if include_new_format:
        return _scenarios + _new_scenarios
    else:
        return _scenarios

def get_all_new_format_scenarios() -> List[Dict[str, Any]]:
    """
    Get all available new format scenarios.
    
    Returns:
        List of all new format scenarios.
    """
    return _new_scenarios

def get_scenario_by_id(scenario_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific scenario by ID.
    
    Args:
        scenario_id: The ID of the scenario to retrieve.
        
    Returns:
        The scenario if found, None otherwise.
    """
    # Check traditional scenarios first
    for scenario in _scenarios:
        if scenario.get('id') == scenario_id:
            return scenario
    
    # Then check new format scenarios
    for scenario in _new_scenarios:
        if scenario.get('id') == scenario_id:
            return scenario
    
    logger.warning(f"Scenario with ID {scenario_id} not found")
    return None

def is_new_format_scenario(scenario: Dict[str, Any]) -> bool:
    """
    Check if a scenario is in the new format.
    
    Args:
        scenario: The scenario to check.
        
    Returns:
        True if the scenario is in the new format, False otherwise.
    """
    # New format scenarios have context, customer_profile, and conversation_flow fields
    return all(field in scenario for field in ['context', 'customer_profile', 'conversation_flow'])

def select_random_scenario(new_format_only: bool = False) -> Optional[Dict[str, Any]]:
    """
    Select a random scenario.
    
    Args:
        new_format_only: Whether to select only from new format scenarios.
        
    Returns:
        A randomly selected scenario, or None if no scenarios are available.
    """
    if new_format_only:
        if not _new_scenarios:
            logger.warning("No new format scenarios available to select from")
            return None
        
        selected = random.choice(_new_scenarios)
    else:
        all_scenarios = _scenarios + _new_scenarios
        if not all_scenarios:
            logger.warning("No scenarios available to select from")
            return None
        
        selected = random.choice(all_scenarios)
    
    logger.info(f"Randomly selected scenario: {selected.get('id')} - {selected.get('title')}")
    return selected

def select_random_scenarios(count: int = 1, new_format_only: bool = False) -> List[Dict[str, Any]]:
    """
    Select multiple random scenarios.
    
    Args:
        count: Number of scenarios to select.
        new_format_only: Whether to select only from new format scenarios.
        
    Returns:
        List of randomly selected scenarios.
    """
    if new_format_only:
        scenarios_pool = _new_scenarios
    else:
        scenarios_pool = _scenarios + _new_scenarios
    
    if not scenarios_pool:
        logger.warning("No scenarios available to select from")
        return []
    
    # Ensure we don't try to select more scenarios than are available
    count = min(count, len(scenarios_pool))
    
    # Select random scenarios without replacement
    selected = random.sample(scenarios_pool, count)
    
    scenario_ids = [s.get('id') for s in selected]
    logger.info(f"Randomly selected {count} scenarios: {', '.join(scenario_ids)}")
    
    return selected

def filter_scenarios_by_tags(tags: List[str], include_new_format: bool = True) -> List[Dict[str, Any]]:
    """
    Filter scenarios by tags.
    
    Args:
        tags: List of tags to filter by.
        include_new_format: Whether to include new format scenarios.
        
    Returns:
        List of scenarios that match the given tags.
    """
    if not tags:
        return get_all_scenarios(include_new_format)
    
    if include_new_format:
        scenarios_pool = _scenarios + _new_scenarios
    else:
        scenarios_pool = _scenarios
    
    filtered = []
    for scenario in scenarios_pool:
        scenario_topics = scenario.get('topics', [])
        # Check if any of the specified tags match the scenario's topics
        if any(tag in scenario_topics for tag in tags):
            filtered.append(scenario)
    
    logger.info(f"Filtered scenarios by tags {tags}, found {len(filtered)} matches")
    return filtered

def filter_scenarios_by_difficulty(difficulty: str, include_new_format: bool = True) -> List[Dict[str, Any]]:
    """
    Filter scenarios by difficulty level.
    
    Args:
        difficulty: Difficulty level to filter by (e.g., 'easy', 'medium', 'hard').
        include_new_format: Whether to include new format scenarios.
        
    Returns:
        List of scenarios with the specified difficulty.
    """
    if include_new_format:
        scenarios_pool = _scenarios + _new_scenarios
    else:
        scenarios_pool = _scenarios
    
    filtered = [s for s in scenarios_pool if s.get('difficulty') == difficulty]
    logger.info(f"Filtered scenarios by difficulty {difficulty}, found {len(filtered)} matches")
    return filtered

def get_random_question_from_scenario(scenario_id: str) -> Optional[Dict[str, Any]]:
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
    
    # Handle different scenario formats
    if is_new_format_scenario(scenario):
        # For new format scenarios, return a conversation stage instead of a question
        conversation_flow = scenario.get('conversation_flow', {})
        if not conversation_flow:
            logger.warning(f"No conversation flow found in scenario {scenario_id}")
            return None
        
        # Get a random stage from the conversation flow
        stage_name = random.choice(list(conversation_flow.keys()))
        stage_data = conversation_flow[stage_name]
        
        # Create a question-like structure for compatibility
        question = {
            "id": f"stage_{stage_name}",
            "stage": stage_name,
            "agent_goals": stage_data.get("agent_goals", []),
            "question": f"Handle the {stage_name} stage of the conversation"
        }
        
        logger.info(f"Selected random conversation stage {stage_name} from scenario {scenario_id}")
        return question
    else:
        # For traditional scenarios, get a random question
        questions = scenario.get('questions', [])
        if not questions:
            logger.warning(f"No questions found in scenario {scenario_id}")
            return None
        
        question = random.choice(questions)
        logger.info(f"Selected random question {question.get('id')} from scenario {scenario_id}")
        return question

def get_next_conversation_stage(scenario_id: str, current_stage: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get the next stage in the conversation flow.
    
    Args:
        scenario_id: ID of the scenario.
        current_stage: Current stage in the conversation flow. If None, returns the first stage.
        
    Returns:
        The next conversation stage, or None if the scenario is not found or there are no more stages.
    """
    scenario = get_scenario_by_id(scenario_id)
    if not scenario or not is_new_format_scenario(scenario):
        return None
    
    conversation_flow = scenario.get('conversation_flow', {})
    if not conversation_flow:
        logger.warning(f"No conversation flow found in scenario {scenario_id}")
        return None
    
    # Get the ordered list of stages
    stages = list(conversation_flow.keys())
    
    if current_stage is None:
        # Return the first stage
        first_stage = stages[0]
        stage_data = conversation_flow[first_stage]
        
        # Create a question-like structure for compatibility
        question = {
            "id": f"stage_{first_stage}",
            "stage": first_stage,
            "agent_goals": stage_data.get("agent_goals", []),
            "question": f"Handle the {first_stage} stage of the conversation"
        }
        
        logger.info(f"Selected first conversation stage {first_stage} from scenario {scenario_id}")
        return question
    else:
        # Find the current stage in the list
        try:
            current_index = stages.index(current_stage)
            
            # Check if there's a next stage
            if current_index + 1 < len(stages):
                next_stage = stages[current_index + 1]
                stage_data = conversation_flow[next_stage]
                
                # Create a question-like structure for compatibility
                question = {
                    "id": f"stage_{next_stage}",
                    "stage": next_stage,
                    "agent_goals": stage_data.get("agent_goals", []),
                    "question": f"Handle the {next_stage} stage of the conversation"
                }
                
                logger.info(f"Selected next conversation stage {next_stage} from scenario {scenario_id}")
                return question
            else:
                logger.info(f"No more conversation stages in scenario {scenario_id}")
                return None
        except ValueError:
            logger.warning(f"Current stage {current_stage} not found in scenario {scenario_id}")
            return None

def get_scenario_context(scenario_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the context information for a scenario.
    
    Args:
        scenario_id: ID of the scenario.
        
    Returns:
        The context information, or None if the scenario is not found or has no context.
    """
    scenario = get_scenario_by_id(scenario_id)
    if not scenario or not is_new_format_scenario(scenario):
        return None
    
    context = scenario.get('context', {})
    return context

def get_customer_profile(scenario_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the customer profile for a scenario.
    
    Args:
        scenario_id: ID of the scenario.
        
    Returns:
        The customer profile, or None if the scenario is not found or has no customer profile.
    """
    scenario = get_scenario_by_id(scenario_id)
    if not scenario or not is_new_format_scenario(scenario):
        return None
    
    profile = scenario.get('customer_profile', {})
    return profile

def get_evaluation_criteria(scenario_id: str) -> Optional[Dict[str, str]]:
    """
    Get the evaluation criteria for a scenario.
    
    Args:
        scenario_id: ID of the scenario.
        
    Returns:
        The evaluation criteria, or None if the scenario is not found or has no evaluation criteria.
    """
    scenario = get_scenario_by_id(scenario_id)
    if not scenario or not is_new_format_scenario(scenario):
        return None
    
    criteria = scenario.get('evaluation_criteria', {})
    return criteria

def save_scenarios(traditional_path: str = None, new_format_path: str = None) -> Tuple[bool, bool]:
    """
    Save scenarios to JSON files.
    
    Args:
        traditional_path: Path to save the traditional scenarios. If None, uses the current path.
        new_format_path: Path to save the new format scenarios. If None, uses the current path.
        
    Returns:
        Tuple of (traditional_success, new_format_success).
    """
    global _scenarios_path, _new_scenarios_path
    
    traditional_path = traditional_path or _scenarios_path
    new_format_path = new_format_path or _new_scenarios_path
    
    # Save traditional scenarios
    traditional_success = False
    try:
        with open(traditional_path, 'w') as file:
            json.dump({'scenarios': _scenarios}, file, indent=4)
        logger.info(f"Saved {len(_scenarios)} traditional scenarios to {traditional_path}")
        traditional_success = True
    except Exception as e:
        logger.error(f"Error saving traditional scenarios: {str(e)}")
    
    # Save new format scenarios
    new_format_success = False
    try:
        with open(new_format_path, 'w') as file:
            json.dump({'scenarios': _new_scenarios}, file, indent=4)
        logger.info(f"Saved {len(_new_scenarios)} new format scenarios to {new_format_path}")
        new_format_success = True
    except Exception as e:
        logger.error(f"Error saving new format scenarios: {str(e)}")
    
    return traditional_success, new_format_success

def add_scenario(scenario: Dict[str, Any]) -> bool:
    """
    Add a new scenario.
    
    Args:
        scenario: The scenario to add.
        
    Returns:
        True if successful, False otherwise.
    """
    global _scenarios, _new_scenarios
    
    # Determine if this is a new format scenario
    is_new_format = is_new_format_scenario(scenario)
    
    # Validate required fields
    if is_new_format:
        required_fields = ['id', 'title', 'description', 'context', 'customer_profile', 'conversation_flow']
    else:
        required_fields = ['id', 'title', 'description', 'questions']
    
    for field in required_fields:
        if field not in scenario:
            logger.error(f"Scenario is missing required field: {field}")
            return False
    
    # Check for duplicate ID
    all_scenarios = _scenarios + _new_scenarios
    if any(s.get('id') == scenario['id'] for s in all_scenarios):
        logger.error(f"Scenario with ID {scenario['id']} already exists")
        return False
    
    # Add version and timestamp
    scenario['version'] = '1.0'
    scenario['last_updated'] = datetime.now().isoformat()
    
    # Add to the appropriate list
    if is_new_format:
        _new_scenarios.append(scenario)
    else:
        _scenarios.append(scenario)
    
    logger.info(f"Added new {'new format' if is_new_format else 'traditional'} scenario: {scenario['id']} - {scenario['title']}")
    
    # Save the updated scenarios
    return save_scenarios()[0 if not is_new_format else 1]

def update_scenario(scenario_id: str, updates: Dict[str, Any]) -> bool:
    """
    Update an existing scenario.
    
    Args:
        scenario_id: ID of the scenario to update.
        updates: Dictionary of fields to update.
        
    Returns:
        True if successful, False otherwise.
    """
    global _scenarios, _new_scenarios
    
    # Check traditional scenarios first
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
            
            logger.info(f"Updated traditional scenario {scenario_id} to version {new_version}")
            
            # Save the updated scenarios
            return save_scenarios()[0]
    
    # Then check new format scenarios
    for i, scenario in enumerate(_new_scenarios):
        if scenario.get('id') == scenario_id:
            # Update version
            current_version = scenario.get('version', '1.0')
            try:
                major, minor = current_version.split('.')
                new_version = f"{major}.{int(minor) + 1}"
            except ValueError:
                new_version = '1.1'
            
            # Apply updates
            _new_scenarios[i].update(updates)
            _new_scenarios[i]['version'] = new_version
            _new_scenarios[i]['last_updated'] = datetime.now().isoformat()
            
            logger.info(f"Updated new format scenario {scenario_id} to version {new_version}")
            
            # Save the updated scenarios
            return save_scenarios()[1]
    
    logger.warning(f"Scenario with ID {scenario_id} not found for update")
    return False

# Initialize the scenario manager when the module is imported
initialize_scenario_manager()