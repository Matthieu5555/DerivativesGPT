# DerivativesGPT

A financial derivatives assistant that both explains complex concepts and prices options in real time. It runs on LangGraph with multiple specialized AI agents — a pricing engine, an educational tutor, and a strategy analyzer — that collaborate behind a single conversational interface.

**Live demo:** [matthieu-separt.site](https://matthieu-separt.site/)

## Getting started

Clone the repo and install dependencies. The project uses [uv](https://docs.astral.sh/uv/) for fast, reproducible package management, though pip works too.

```bash
git clone https://github.com/Matthieu5555/DerivativesGPT.git
cd DerivativesGPT
```

With uv (recommended):

```bash
uv sync
```

Or with pip:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Configuration

Copy the environment template, then fill in whichever LLM provider you prefer — only one is required.

```bash
cp .env.example .env
```

At minimum, set `LLM_PROVIDER` and the corresponding API key:

```bash
LLM_PROVIDER=openai          # or "gemini" or "openrouter"
OPENAI_API_KEY=sk-...        # https://platform.openai.com/api-keys
GEMINI_API_KEY=...           # https://makersuite.google.com/app/apikey
OPENROUTER_API_KEY=...       # https://openrouter.ai/keys
```

The RAG vectorstore ships with the repo, so retrieval-augmented educational responses work out of the box. LangSmith tracing is optional but highly recommended for inspecting agent behavior — set `ENABLE_LANGSMITH=true` and add your API key. See `.env.example` for every available setting.

## Running the app

```bash
uv run chainlit run main.py    # or: python main.py
```

This starts the Chainlit web UI at `http://localhost:8000`.

## What you can ask

The system routes your query to the right agent automatically, so just ask naturally.

- **Pricing:** "Price a call on AAPL with strike 150, expiring in 30 days" — handles vanilla, American, Asian, digital, and barrier options as well as multi-leg strategies like straddles, spreads, and butterflies.
- **Education:** "How does implied volatility affect option prices?" — explains derivatives concepts with textbook citations from the built-in RAG index.
- **Strategy:** "Analyze a bull call spread on NVDA" — breaks down risk profiles and payoff structures.

## Project layout

```
derivatives_gpt_core/
├── agents/           # Multi-agent orchestration (pricing, educational, shared)
├── features/         # Pricing models: vanilla, american, asian, digital, barrier
├── core/             # LangGraph graph definitions and routing
├── rag/              # Hybrid BM25 + FAISS retrieval
├── data/             # Market data providers and database access
└── workflow/         # Task execution and planning
databases/
└── vectorstore/      # Pre-built FAISS index + metadata (ships with repo)
prompts/              # LLM prompt templates
tests/                # Test suite
```

## Development

Run the test suite with:

```bash
uv run pytest
```

Code quality:

```bash
uv run black derivatives_gpt_core/
uv run ruff check derivatives_gpt_core/
uv run mypy derivatives_gpt_core/
```

## Troubleshooting

| Problem | Fix |
|---|---|
| "API key not found" | Check `.env` exists at the project root and `LLM_PROVIDER` matches the key you set. |
| "Module not found" | Activate your venv (look for `(.venv)` in your prompt), then re-run `uv sync`. |
| Port 8000 in use | `lsof -i :8000` to find the culprit, or pass `--port 8001`. |
| LangSmith traces missing | Verify `ENABLE_LANGSMITH=true` and that your key works at [smith.langchain.com](https://smith.langchain.com/settings). |

## Built with

[LangGraph](https://github.com/langchain-ai/langgraph) and [LangChain](https://github.com/langchain-ai/langchain) for agent orchestration, [Chainlit](https://github.com/Chainlit/chainlit) for the web UI, [LangSmith](https://smith.langchain.com) for observability, and [FAISS](https://github.com/facebookresearch/faiss) + BM25 for hybrid retrieval.

## License

MIT
