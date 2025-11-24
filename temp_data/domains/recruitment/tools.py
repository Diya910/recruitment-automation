from loguru import logger
from langchain_core.output_parsers import StrOutputParser
from langchain.prompts import PromptTemplate

from domains.utils import get_chat_llm
from domains.recruitment.utils import get_attribute
from domains.stategraph import OverallState, InterviewAnalysisState
from domains.recruitment.summary import create_summarization_graph
from domains.recruitment.prompts import initialize_validation_prompt


async def summarize_interview_history(
        state: InterviewAnalysisState,
) -> InterviewAnalysisState:

    interview_contents = state.get("contents", [])

    if not interview_contents:
        logger.warning("No interview contents found for summarization.")
        raise ValueError("No interview contents found for summarization.")

    summary_state = OverallState(
        contents=interview_contents,
        summaries=[],
        collapsed_summaries=[],
        final_summary="",
    )

    contents = summary_state.get("contents", [])
    # Create the summarization graph by calling the function
    summarization_graph = create_summarization_graph()

    try:
        final_state = None
        async for step in summarization_graph.ainvoke(
                {"contents": contents},
                {"recursion_limit": 10},
        ):
            final_state = step

        if final_state is None:
            logger.error("Summarization graph did not return a final state.")
            raise ValueError("Summarization failed: No final state returned.")

        final_summary = get_attribute(final_state, "final_summary")
        state["final_summary"] = final_summary

    except Exception as e:
        logger.error(f"Error running summarization graph: {str(e)}")
        raise

    return state


def grammar_check(
        state: InterviewAnalysisState,
) -> str:

    final_summary = get_attribute(state, "final_summary")

    try:
        llm = get_chat_llm()
        grammar_prompt = PromptTemplate(
            template="""
            Analyze the following text for grammar and spelling errors:
            
            {text}
            
            Provide a detailed list of all grammar and spelling issues found. 
            If no issues are found, state "No grammar or spelling issues found."
            """,
            input_variables=["text"]
        )
        
        chain = grammar_prompt | llm | StrOutputParser()
        response = chain.invoke({"text": final_summary})

        if hasattr(response, 'content'):
            result = response.content.strip()
        else:
            result = str(response).strip()
        logger.success("Grammar check completed.")
        return result
    except Exception as e:
        logger.error(f"Grammar checker failed: {e}")
        raise


def validation_tool(
        state: InterviewAnalysisState
) -> InterviewAnalysisState:
    try:
        logger.info("Checking assessment report quality and completeness...")
        validation_prompt = initialize_validation_prompt()
        llm = get_chat_llm()
        
        final_summary = get_attribute(state, "final_summary", "")
        
        chain = validation_prompt | llm | StrOutputParser()
        response = chain.invoke({"summary": final_summary})

        if hasattr(response, 'content'):
            validation_result = response.content.strip()
        else:
            validation_result = str(response).strip()
            
        # Store validation result in state
        state["validation_result"] = validation_result
        logger.success("Validation completed successfully.")
        
        return state

    except Exception as e:
        logger.error(f"Validation failed: {e}")
        raise e

