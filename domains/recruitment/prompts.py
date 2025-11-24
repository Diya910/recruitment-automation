from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field


class ClarificationResponse(BaseModel):
    needs_clarification: bool = Field(description="Whether the response needs clarification")
    clarification_question: str = Field(description="Follow-up question to ask for clarification", default=None)
    reasoning: str = Field(description="Reasoning behind the decision")


class ResponseAnalysis(BaseModel):
    relevance_score: int = Field(description="How relevant the response is to the question (1-10)")
    completeness_score: int = Field(description="How completely the response answers the question (1-10)")
    clarity_score: int = Field(description="How clear and well-structured the response is (1-10)")
    technical_accuracy_score: int = Field(description="How technically accurate the response is (1-10)")
    professional_tone_score: int = Field(description="How professional the tone of the response is (1-10)")
    reasoning: str = Field(description="Reasoning behind the scores")


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

# ===== Summarization Prompts =====

SUMMARY_MAP_TEMPLATE = """
Analyze this interview Q&A:

{document}

Provide a comprehensive evaluation with the following sections:
1. Content Summary: Main experience, skills, and contributions mentioned
2. Grammar & Spelling: List specific issues found or "None found"
3. Confidence Level: Rate from 1-10 with brief justification
4. Directness: Rate from 1-10 how directly the answer addresses the question
5. Completeness: Rate from 1-10 how thoroughly the question was answered
6. Professional Language: Rate from 1-10 the level of professional terminology used
7. Emotional Tone: Describe the overall sentiment (positive, neutral, negative, confident, hesitant, etc.)
8. Clarity & Structure: Rate from 1-10 how well-organized and clear the response is
"""

REDUCE_TEMPLATE = """
Combine the following detailed interview Q&A evaluations into a comprehensive candidate assessment report:

{document}

Your report should include:
1. EXECUTIVE SUMMARY: A brief overview of the candidate's performance
2. TECHNICAL SKILLS ASSESSMENT: Synthesize the content summaries to evaluate technical competence
3. COMMUNICATION EVALUATION:
  - Overall Grammar & Spelling: Summarize all issues found across answers
  - Average Confidence Level: Calculate the average score
  - Average Directness: Calculate the average score
  - Average Completeness: Calculate the average score
  - Professional Language Usage: Calculate the average score
  - Dominant Emotional Tone: Identify patterns in emotional tone across answers
  - Average Clarity & Structure: Calculate the average score

4. STRENGTHS: List 3-5 key strengths based on the evaluation
5. OVERALL RATING: Provide a final score from 1-10 with brief justification

Format the report in a clear, structured manner with section headings.
"""

# ===== Evaluation Prompts =====

VALIDATION_TEMPLATE = """
Validate the quality and completeness of the following interview assessment report:

{summary}

Provide a detailed validation with the following criteria:
1. Comprehensiveness: Does the assessment cover all key aspects of candidate evaluation? (Yes/No with explanation)
2. Evidence-Based: Are the ratings and conclusions supported by specific examples from the interview? (Yes/No with explanation)
3. Consistency: Are the ratings consistent with the described strengths and weaknesses? (Yes/No with explanation)
4. Actionable Feedback: Does the assessment provide clear areas for improvement? (Yes/No with explanation)
5. Fairness: Is the assessment balanced and free from apparent bias? (Yes/No with explanation)
6. Overall Validity: Is this a valid and useful assessment report? (Yes/No with explanation)

Format your response with clear section headings.
{
    "comprehensiveness": "explanation",
    "evidence_based": "explanation",
    "consistency": "explanation",
    "actionable_feedback": "explanation",
    "fairness": "explanation",
    "overall_validity": "explanation"
}
"""

GRAMMAR_CHECK_TEMPLATE = """
Analyze the following text for grammar and spelling errors:

{text}

Provide a detailed list of all grammar and spelling issues found. 
If no issues are found, state "No grammar or spelling issues found."
"""

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

# ===== Master Agent Prompts =====

MASTER_AGENT_SYSTEM_PROMPT = """
You are an advanced AI Master Agent responsible for orchestrating a technical interview process.
Your role is to coordinate the interview flow, analyze responses, and generate comprehensive evaluations.

You have access to the following tools:
1. Conversation Engine: For managing the interview dialogue and processing candidate responses
2. Summarization Tool: For summarizing and analyzing the interview content
3. Grammar Check Tool: For evaluating the grammar and language quality of responses
4. Validation Tool: For validating the quality and completeness of assessments
5. Additional tools that may be added dynamically

Your responsibilities include:
- Deciding which questions to ask next based on the conversation flow
- Determining when clarification is needed for unclear responses
- Invoking appropriate analysis tools at the right time
- Generating comprehensive evaluation reports
- Adapting to different technical domains and interview scenarios

You should make decisions dynamically based on the state of the interview and the candidate's responses.
Always maintain a professional tone and ensure fair, unbiased evaluations.
"""

FINAL_REPORT_TEMPLATE = """
You are an HR professional reviewing a technical interview. Generate a comprehensive evaluation report based on the following information:

SCENARIO: {scenario_title}
DESCRIPTION: {scenario_description}

INTERVIEW SUMMARY:
{final_summary}

GRAMMAR EVALUATION:
{grammar_evaluation}

VALIDATION RESULT:
{validation_result}

DETAILED EVALUATIONS:
{detailed_evaluations}

Please provide a structured report with the following sections:
1. Executive Summary
2. Technical Skills Assessment
3. Communication Evaluation
4. Strengths and Areas for Improvement
5. Overall Rating (1-10) with Justification

Format the report in a clear, professional manner suitable for HR records.
"""

# ===== Prompt Initialization Functions =====

def initialize_clarification_prompt() -> PromptTemplate:
    """Initialize the clarification prompt with the PydanticOutputParser."""
    clarification_parser = PydanticOutputParser(pydantic_object=ClarificationResponse)
    return PromptTemplate(
        template=CLARIFICATION_PROMPT_TEMPLATE,
        input_variables=["question", "response"],
        partial_variables={"format_instructions": clarification_parser.get_format_instructions()}
    )

def initialize_response_analysis_prompt() -> PromptTemplate:
    """Initialize the response analysis prompt with the PydanticOutputParser."""
    response_analysis_parser = PydanticOutputParser(pydantic_object=ResponseAnalysis)
    return PromptTemplate(
        template=RESPONSE_ANALYSIS_PROMPT_TEMPLATE,
        input_variables=["question", "response"],
        partial_variables={"format_instructions": response_analysis_parser.get_format_instructions()}
    )

def initialize_next_question_prompt() -> PromptTemplate:
    """Initialize the next question prompt."""
    return PromptTemplate(
        template=NEXT_QUESTION_PROMPT_TEMPLATE,
        input_variables=["scenario_title", "scenario_description", "available_questions", "conversation_history"]
    )

def initialize_summary_map_prompt() -> PromptTemplate:
    """Initialize the summary map prompt."""
    return PromptTemplate(
        template=SUMMARY_MAP_TEMPLATE,
        input_variables=["document"],
        output_parser=StrOutputParser()
    )

def initialize_reduce_prompt() -> PromptTemplate:
    """Initialize the reduce prompt."""
    return PromptTemplate(
        template=REDUCE_TEMPLATE,
        input_variables=["document"],
        output_parser=StrOutputParser()
    )

def initialize_validation_prompt() -> PromptTemplate:
    """Initialize the validation prompt."""
    return PromptTemplate(
        template=VALIDATION_TEMPLATE,
        input_variables=["summary"],
        output_parser=JsonOutputParser()
    )

def initialize_grammar_check_prompt() -> PromptTemplate:
    """Initialize the grammar check prompt."""
    return PromptTemplate(
        template=GRAMMAR_CHECK_TEMPLATE,
        input_variables=["text"],
        output_parser=StrOutputParser()
    )

def initialize_detailed_evaluation_prompt() -> PromptTemplate:
    """Initialize the detailed evaluation prompt."""
    from domains.recruitment.evaluation import DetailedEvaluation
    detailed_eval_parser = PydanticOutputParser(pydantic_object=DetailedEvaluation)
    return PromptTemplate(
        template=DETAILED_EVALUATION_PROMPT,
        input_variables=["question", "response"],
        partial_variables={"format_instructions": detailed_eval_parser.get_format_instructions()}
    )

def initialize_overall_evaluation_prompt() -> PromptTemplate:
    """Initialize the overall evaluation prompt."""
    from domains.recruitment.evaluation import OverallEvaluation
    overall_eval_parser = PydanticOutputParser(pydantic_object=OverallEvaluation)
    return PromptTemplate(
        template=OVERALL_EVALUATION_PROMPT,
        input_variables=["scenario_title", "scenario_description", "final_summary", "detailed_evaluations"],
        partial_variables={"format_instructions": overall_eval_parser.get_format_instructions()}
    )

def initialize_final_report_prompt() -> PromptTemplate:
    """Initialize the final report prompt."""
    return PromptTemplate(
        template=FINAL_REPORT_TEMPLATE,
        input_variables=[
            "scenario_title", 
            "scenario_description", 
            "final_summary", 
            "grammar_evaluation", 
            "validation_result", 
            "detailed_evaluations"
        ],
        output_parser=StrOutputParser()
    )

def get_master_agent_system_prompt() -> str:
    """Get the master agent system prompt."""
    return MASTER_AGENT_SYSTEM_PROMPT