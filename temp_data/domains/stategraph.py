import operator

from typing import Annotated, List, TypedDict
from langchain_core.documents import Document


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