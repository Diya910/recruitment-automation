from domains.utils import get_chat_llm

from typing import List, Literal

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser

from langgraph.graph import StateGraph, START, END
from langgraph.constants import Send

from domains.recruitment.utils import get_attribute
from domains.stategraph import OverallState, SummaryState
from domains.settings import config_settings

from langchain.chains.combine_documents.reduce import (
    acollapse_docs,
    split_list_of_docs,
)
from domains.recruitment.prompts import (
    initialize_summary_map_prompt,
    initialize_reduce_prompt
)


def create_summarization_graph():
    llm = get_chat_llm()

    map_prompt = initialize_summary_map_prompt() | llm | StrOutputParser()
    map_chain = map_prompt | llm | StrOutputParser()

    reduce_chain = initialize_reduce_prompt() | llm | StrOutputParser()

    def length_function(documents: List[Document]) -> int:
        return sum(llm.get_num_tokens(doc.page_content) for doc in documents)

    async def generate_summary(state: SummaryState):
        content = get_attribute(state, "content", "")
        response = await map_chain.ainvoke({"context": content})
        return {"summaries": [response]}

    def map_summaries(state: OverallState):
        contents = get_attribute(state, "contents", [])
        return [
            Send("generate_summary", {"content": content}) for content in contents
        ]

    def collect_summaries(state: OverallState):
        summaries = get_attribute(state, "summaries", [])
        return {
            "collapsed_summaries": [Document(page_content=summary) for summary in summaries]
        }

    async def collapse_summaries(state: OverallState):
        collapsed_summaries = get_attribute(state, "collapsed_summaries", [])
        doc_lists = split_list_of_docs(
            collapsed_summaries, length_function, config_settings.SUMMARIZATION_CHUNK_SIZE,
        )
        results = []
        for doc_list in doc_lists:
            results.append(await acollapse_docs(doc_list, reduce_chain.ainvoke))

        return {"collapsed_summaries": results}

    def should_collapse(
            state: OverallState,
    ) -> Literal["collapse_summaries", "generate_final_summary"]:
        collapsed_summaries = get_attribute(state, "collapsed_summaries", [])
        num_tokens = length_function(collapsed_summaries)
        if num_tokens > config_settings.SUMMARIZATION_CHUNK_SIZE:
            return "collapse_summaries"
        else:
            return "generate_final_summary"

    async def generate_final_summary(state: OverallState):
        collapsed_summaries = get_attribute(state, "collapsed_summaries", [])
        docs_text = "\n\n".join([doc.page_content for doc in collapsed_summaries])
        response = await reduce_chain.ainvoke({"docs": docs_text})
        return {"final_summary": response}

    # Nodes:
    graph = StateGraph(OverallState)
    graph.add_node("generate_summary", generate_summary)
    graph.add_node("collect_summaries", collect_summaries)
    graph.add_node("collapse_summaries", collapse_summaries)
    graph.add_node("generate_final_summary", generate_final_summary)

    # Edges:
    graph.add_conditional_edges(START, map_summaries, ["generate_summary"])
    graph.add_edge("generate_summary", "collect_summaries")
    graph.add_conditional_edges("collect_summaries", should_collapse)
    graph.add_conditional_edges("collapse_summaries", should_collapse)
    graph.add_edge("generate_final_summary", END)

    return graph.compile()