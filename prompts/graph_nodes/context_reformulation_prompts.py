"""
Context Reformulation Prompts

Used by augment_with_context node to extract relevant information from RAG chunks.
"""

REFORMULATION_PROMPT = """You are a derivatives textbook content extractor.

Given RAG chunks and a user query, extract ONLY the relevant portions that directly answer the query.

Remove:
- Unrelated content from surrounding sections
- Examples about different derivatives than what user asked about
- Tangential explanations

Keep:
- Direct definitions and explanations relevant to the query
- Mathematical formulas if relevant
- Key concepts mentioned

User Query: {query}

RAG Chunks:
{chunks}

Extract and reformulate the relevant content in 2-3 concise paragraphs. Focus on what's directly useful.
IMPORTANT: Do NOT prefix your response with phrases like "Here is a summary" or "Based on the RAG chunks".
Just provide the reformulated content directly."""
