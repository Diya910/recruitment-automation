import operator
from typing import Annotated, List, TypedDict, Callable, Any, Union, Literal
from langchain_core.documents import Document
from langchain_core.messages import BaseMessage

def add_messages(existing_messages: List[BaseMessage], new_messages: List[BaseMessage]) -> List[BaseMessage]:
    """
    Combine two lists of messages.
    
    Args:
        existing_messages: The existing list of messages
        new_messages: The new list of messages to add
        
    Returns:
        The combined list of messages
    """
    return existing_messages + new_messages

# Define IsLastStep type
IsLastStep = bool


class OverallState(TypedDict):
    contents: List[str]
    summaries: Annotated[list, operator.add]
    collapsed_summaries: List[Document]
    final_summary: str


class SummaryState(TypedDict):
    content: str


class InterviewAnalysisState(TypedDict):
    """State for analyzing interview responses."""
    question: str
    answer: str
    messages: Annotated[list, add_messages]
    is_last_step: IsLastStep
    contents: List[str]
    final_summary: str
    grammar_evaluation: List[str]
    spelling_mistakes_evaluation: List[str]
    vocabulary_score_evaluation: int
    sentence_structure_score: int
    professional_tone_score: int
    overall_language_score: int