#!/usr/bin/env python3
import sys
from loguru import logger

# Configure logger
logger.remove()
logger.add(sys.stderr, level="INFO")

# Import the necessary modules
try:
    from domains.recruitment.scenario_manager import get_all_scenarios
except ImportError as e:
    print(f"Failed to import required modules: {e}")
    sys.exit(1)

def check_scenarios():
    """Check all scenarios and print the number of questions in each."""
    print("Checking all scenarios...")
    
    # Get all scenarios
    scenarios = get_all_scenarios()
    print(f"Found {len(scenarios)} scenarios")
    
    # Check each scenario
    for scenario in scenarios:
        scenario_id = scenario.get('id', 'unknown')
        title = scenario.get('title', 'unknown')
        questions = scenario.get('questions', [])
        
        print(f"Scenario: {scenario_id} - {title}")
        print(f"  Number of questions: {len(questions)}")
        print(f"  Question IDs: {[q.get('id') for q in questions]}")
        print()
    
    print("Scenario check complete")

if __name__ == "__main__":
    check_scenarios()