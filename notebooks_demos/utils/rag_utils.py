"""Utilities for RAG comparison notebook."""

from typing import Dict, List
from derivatives_gpt_core.rag.hybrid_retriever import HybridRAGRetriever
from derivatives_gpt_core.llm_provider import get_classification_llm

def get_rag_sources(query: str) -> List[Dict]:
    """Retrieve sources using hybrid RAG."""
    try:
        retriever = HybridRAGRetriever()
        sources = retriever.retrieve(query)
        return sources[:3]  # Top 3 sources
    except Exception as e:
        print(f"RAG retrieval failed: {e}")
        return []

async def get_llm_response(query: str, with_context: str = None) -> str:
    """Get LLM response with or without context."""
    llm = get_classification_llm()

    if with_context:
        prompt = f"Based on this context:\n{with_context}\n\nAnswer: {query}"
    else:
        prompt = f"Answer: {query}"

    response = await llm.ainvoke(prompt)
    return str(response.content if hasattr(response, 'content') else response)

async def compare_responses(query: str) -> Dict:
    """Compare RAG-augmented vs pure LLM responses."""

    # Get RAG sources
    sources = get_rag_sources(query)

    # Build context from sources
    context = ""
    if sources:
        context = "\n---\n".join([s['text'][:500] for s in sources])

    # Get both responses
    rag_response = await get_llm_response(query, with_context=context)
    pure_response = await get_llm_response(query)

    return {
        'query': query,
        'sources_found': len(sources),
        'source_metadata': [{'book': s.get('book', 'Unknown'),
                            'page': s.get('page', 'N/A'),
                            'score': s.get('score', 0)} for s in sources],
        'rag_response': rag_response,
        'pure_response': pure_response
    }