from typing import Dict, List, Any, Optional, Union
from loguru import logger
import json
from datetime import datetime

from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain.output_parsers import PydanticOutputParser

from domains.utils import get_chat_llm
from domains.stategraph import InterviewAnalysisState

class DetailedEvaluation(BaseModel):
    """Detailed evaluation of a candidate's response."""
    relevance_score: int = Field(description="How relevant the response is to the question (1-10)")
    completeness_score: int = Field(description="How completely the response answers the question (1-10)")
    clarity_score: int = Field(description="How clear and well-structured the response is (1-10)")
    technical_accuracy_score: int = Field(description="How technically accurate the response is (1-10)")
    professional_tone_score: int = Field(description="How professional the tone of the response is (1-10)")
    grammar_score: int = Field(description="Quality of grammar and spelling (1-10)")
    vocabulary_score: int = Field(description="Richness and appropriateness of vocabulary (1-10)")
    reasoning: str = Field(description="Detailed reasoning behind the scores")
    strengths: List[str] = Field(description="Key strengths of the response")
    weaknesses: List[str] = Field(description="Areas for improvement in the response")

class OverallEvaluation(BaseModel):
    """Overall evaluation of the entire interview."""
    technical_skills_score: int = Field(description="Overall technical skills demonstrated (1-10)")
    communication_score: int = Field(description="Overall communication skills (1-10)")
    problem_solving_score: int = Field(description="Problem-solving abilities (1-10)")
    domain_knowledge_score: int = Field(description="Domain-specific knowledge (1-10)")
    overall_score: int = Field(description="Overall candidate score (1-10)")
    key_strengths: List[str] = Field(description="Key strengths demonstrated throughout the interview")
    improvement_areas: List[str] = Field(description="Areas for improvement")
    hiring_recommendation: str = Field(description="Recommendation for hiring (Strongly Recommend, Recommend, Neutral, Do Not Recommend)")
    reasoning: str = Field(description="Detailed reasoning behind the evaluation")

# Prompt templates
DETAILED_EVALUATION_PROMPT = """
You are an expert technical interviewer evaluating a candidate's response to a technical question.

QUESTION: {question}
CANDIDATE'S RESPONSE: {response}

Provide a detailed evaluation of the response based on the following criteria:
1. Relevance: How directly the response addresses the question
2. Completeness: How thoroughly the question was answered
3. Clarity: How well-organized and clear the response is
4. Technical Accuracy: How technically sound the concepts and solutions are
5. Professional Tone: How professional the language and tone are
6. Grammar: Quality of grammar and spelling
7. Vocabulary: Richness and appropriateness of vocabulary

For each criterion, provide a score from 1-10 and brief justification.
Also identify key strengths and weaknesses in the response.

{format_instructions}
"""

OVERALL_EVALUATION_PROMPT = """
You are an HR professional evaluating a candidate's overall performance in a technical interview.

SCENARIO: {scenario_title}
DESCRIPTION: {scenario_description}

INTERVIEW SUMMARY:
{final_summary}

DETAILED EVALUATIONS:
{detailed_evaluations}

Provide an overall evaluation of the candidate based on the entire interview, considering:
1. Technical Skills: Depth and breadth of technical knowledge
2. Communication: Clarity, conciseness, and effectiveness of communication
3. Problem Solving: Approach to solving problems, critical thinking
4. Domain Knowledge: Understanding of the specific domain (e.g., API design, frontend, data science)
5. Overall Fit: Overall suitability for a technical role

For each criterion, provide a score from 1-10 with justification.
Identify 3-5 key strengths and 2-4 areas for improvement.
Provide a hiring recommendation (Strongly Recommend, Recommend, Neutral, Do Not Recommend) with reasoning.

{format_instructions}
"""

class EvaluationSystem:
    """
    System for analyzing and evaluating candidate responses.
    """
    
    def __init__(self):
        """Initialize the evaluation system."""
        self.llm = get_chat_llm()
        
        # Initialize parsers
        self.detailed_eval_parser = PydanticOutputParser(pydantic_object=DetailedEvaluation)
        self.overall_eval_parser = PydanticOutputParser(pydantic_object=OverallEvaluation)
        
        # Initialize prompts
        self.detailed_eval_prompt = PromptTemplate(
            template=DETAILED_EVALUATION_PROMPT,
            input_variables=["question", "response"],
            partial_variables={"format_instructions": self.detailed_eval_parser.get_format_instructions()}
        )
        
        self.overall_eval_prompt = PromptTemplate(
            template=OVERALL_EVALUATION_PROMPT,
            input_variables=["scenario_title", "scenario_description", "final_summary", "detailed_evaluations"],
            partial_variables={"format_instructions": self.overall_eval_parser.get_format_instructions()}
        )
    
    async def evaluate_response(self, question: str, response: str) -> DetailedEvaluation:
        """
        Evaluate a single response to a question.
        
        Args:
            question: The question asked
            response: The candidate's response
            
        Returns:
            Detailed evaluation of the response
        """
        try:
            # Create the evaluation chain
            eval_chain = self.detailed_eval_prompt | self.llm | self.detailed_eval_parser
            
            # Evaluate the response
            evaluation = await eval_chain.ainvoke({
                "question": question,
                "response": response
            })
            
            logger.info(f"Evaluated response with overall score: {(evaluation.relevance_score + evaluation.completeness_score + evaluation.technical_accuracy_score) / 3:.1f}/10")
            return evaluation
        except Exception as e:
            logger.error(f"Error evaluating response: {str(e)}")
            raise
    
    async def evaluate_interview(
        self, 
        scenario_title: str, 
        scenario_description: str, 
        final_summary: str, 
        detailed_evaluations: List[DetailedEvaluation]
    ) -> OverallEvaluation:
        """
        Evaluate the entire interview based on all responses.
        
        Args:
            scenario_title: Title of the interview scenario
            scenario_description: Description of the scenario
            final_summary: Summary of the interview
            detailed_evaluations: List of detailed evaluations for each response
            
        Returns:
            Overall evaluation of the interview
        """
        try:
            # Format the detailed evaluations for the prompt
            formatted_evals = []
            for i, eval in enumerate(detailed_evaluations):
                eval_dict = eval.dict()
                eval_text = f"EVALUATION {i+1}:\n"
                eval_text += f"- Relevance: {eval_dict['relevance_score']}/10\n"
                eval_text += f"- Completeness: {eval_dict['completeness_score']}/10\n"
                eval_text += f"- Clarity: {eval_dict['clarity_score']}/10\n"
                eval_text += f"- Technical Accuracy: {eval_dict['technical_accuracy_score']}/10\n"
                eval_text += f"- Professional Tone: {eval_dict['professional_tone_score']}/10\n"
                eval_text += f"- Grammar: {eval_dict['grammar_score']}/10\n"
                eval_text += f"- Vocabulary: {eval_dict['vocabulary_score']}/10\n"
                eval_text += f"- Strengths: {', '.join(eval_dict['strengths'])}\n"
                eval_text += f"- Weaknesses: {', '.join(eval_dict['weaknesses'])}\n"
                
                formatted_evals.append(eval_text)
            
            # Create the evaluation chain
            eval_chain = self.overall_eval_prompt | self.llm | self.overall_eval_parser
            
            # Evaluate the interview
            overall_evaluation = await eval_chain.ainvoke({
                "scenario_title": scenario_title,
                "scenario_description": scenario_description,
                "final_summary": final_summary,
                "detailed_evaluations": "\n\n".join(formatted_evals)
            })
            
            logger.info(f"Completed overall interview evaluation with score: {overall_evaluation.overall_score}/10")
            return overall_evaluation
        except Exception as e:
            logger.error(f"Error evaluating interview: {str(e)}")
            raise
    
    async def generate_evaluation_report(
        self,
        scenario: Dict[str, Any],
        responses: Dict[str, str],
        final_summary: str
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive evaluation report for an interview.
        
        Args:
            scenario: The interview scenario
            responses: Dictionary mapping question IDs to responses
            final_summary: Summary of the interview
            
        Returns:
            Comprehensive evaluation report
        """
        try:
            # Evaluate each response
            detailed_evaluations = {}
            for question_id, response in responses.items():
                # Find the question text
                question_text = ""
                for q in scenario.get("questions", []):
                    if q.get("id") == question_id:
                        question_text = q.get("question", "")
                        break
                
                if not question_text:
                    logger.warning(f"Question with ID {question_id} not found in scenario")
                    continue
                
                # Evaluate the response
                evaluation = await self.evaluate_response(question_text, response)
                detailed_evaluations[question_id] = evaluation
            
            # Generate overall evaluation
            overall_evaluation = await self.evaluate_interview(
                scenario.get("title", ""),
                scenario.get("description", ""),
                final_summary,
                list(detailed_evaluations.values())
            )
            
            # Create the final report
            report = {
                "scenario": {
                    "id": scenario.get("id", ""),
                    "title": scenario.get("title", ""),
                    "description": scenario.get("description", ""),
                    "difficulty": scenario.get("difficulty", ""),
                    "topics": scenario.get("topics", [])
                },
                "timestamp": datetime.now().isoformat(),
                "final_summary": final_summary,
                "detailed_evaluations": {
                    q_id: eval.dict() for q_id, eval in detailed_evaluations.items()
                },
                "overall_evaluation": overall_evaluation.dict()
            }
            
            logger.info(f"Generated comprehensive evaluation report for scenario {scenario.get('id', '')}")
            return report
        except Exception as e:
            logger.error(f"Error generating evaluation report: {str(e)}")
            raise
    
    def calculate_metrics(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate aggregate metrics from an evaluation report.
        
        Args:
            report: The evaluation report
            
        Returns:
            Dictionary of metrics
        """
        try:
            # Extract detailed evaluations
            detailed_evals = report.get("detailed_evaluations", {})
            
            # Calculate average scores
            relevance_scores = []
            completeness_scores = []
            clarity_scores = []
            technical_scores = []
            professional_scores = []
            grammar_scores = []
            vocabulary_scores = []
            
            for eval_id, eval_data in detailed_evals.items():
                relevance_scores.append(eval_data.get("relevance_score", 0))
                completeness_scores.append(eval_data.get("completeness_score", 0))
                clarity_scores.append(eval_data.get("clarity_score", 0))
                technical_scores.append(eval_data.get("technical_accuracy_score", 0))
                professional_scores.append(eval_data.get("professional_tone_score", 0))
                grammar_scores.append(eval_data.get("grammar_score", 0))
                vocabulary_scores.append(eval_data.get("vocabulary_score", 0))
            
            # Calculate averages
            metrics = {
                "avg_relevance_score": sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0,
                "avg_completeness_score": sum(completeness_scores) / len(completeness_scores) if completeness_scores else 0,
                "avg_clarity_score": sum(clarity_scores) / len(clarity_scores) if clarity_scores else 0,
                "avg_technical_score": sum(technical_scores) / len(technical_scores) if technical_scores else 0,
                "avg_professional_score": sum(professional_scores) / len(professional_scores) if professional_scores else 0,
                "avg_grammar_score": sum(grammar_scores) / len(grammar_scores) if grammar_scores else 0,
                "avg_vocabulary_score": sum(vocabulary_scores) / len(vocabulary_scores) if vocabulary_scores else 0,
                "overall_score": report.get("overall_evaluation", {}).get("overall_score", 0),
                "hiring_recommendation": report.get("overall_evaluation", {}).get("hiring_recommendation", "")
            }
            
            return metrics
        except Exception as e:
            logger.error(f"Error calculating metrics: {str(e)}")
            return {}