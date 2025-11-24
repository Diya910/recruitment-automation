from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser

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
6. OVERALL RATING: Provide a final score from 1-10 with brief justification

Format the report in a clear, structured manner with section headings.
"""


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
{{
    "comprehensiveness": "explanation",
    "evidence_based": "explanation",
    "consistency": "explanation",
    "actionable_feedback": "explanation",
    "fairness": "explanation",
    "overall_validity": "explanation"
}}
"""


def initialize_summary_map_prompt() -> PromptTemplate:
    return PromptTemplate(
        template=SUMMARY_MAP_TEMPLATE,
        input_variables=["document"],
        output_parser=StrOutputParser()
    )


def initialize_validation_prompt() -> PromptTemplate:
    return PromptTemplate(
        template=VALIDATION_TEMPLATE,
        input_variables=["summary"],
        output_parser=JsonOutputParser()
    )

def initialize_reduce_prompt() -> PromptTemplate:
    return PromptTemplate(
        template=REDUCE_TEMPLATE,
        input_variables=["document"],
        output_parser=StrOutputParser()
    )

