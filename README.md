# DerivativesGPT

Ever wish you had a derivatives expert in your pocket? This is a financial derivatives assistant that can both explain complex concepts and actually price options for you. It's built on LangGraph with multiple specialized AI agents working together.

**Quick demo:** Try it out at [matthieu-separt.site](https://matthieu-separt.site/)

## What it does

Think of it as having three experts at your disposal:
- A **pricing specialist** who can value vanilla options, American options, exotics (Asian, digital, barrier) - pretty much anything you throw at it
- An **educational tutor** that explains derivatives concepts in plain English and adapts to your level of understanding
- A **strategist** who can analyze multi-leg option strategies and their risk profiles

Plus it can pull real-time market data when needed, so you're not working with stale numbers.

## What you'll need

- Python 3.11+ (check with `python --version`)
- API key from OpenAI, Google Gemini, or OpenRouter - pick your favorite
- UV package manager makes life easier, but regular pip works too
- (Optional but recommended) LangSmith API key if you want to peek under the hood and see what the agents are thinking
- (Optional) Tavily API key for web search features

## Getting Started

### 1. Grab the code

```bash
git clone https://github.com/yourusername/DerivativesGPT.git
cd DerivativesGPT
```

### 2. Install UV (recommended but not required)

UV is blazing fast for managing Python packages. If you want it:

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or just use pip if you prefer
pip install uv
```

Don't want UV? No worries, regular pip works fine too.

### 3. Configure your API keys

Copy the example file and add your keys:

```bash
cp .env.example .env
```

Now open `.env` in your editor and set these up:

#### The essentials

```bash
# Pick your LLM provider
LLM_PROVIDER=openai  # or "gemini" or "openrouter"

# Add the matching API key
OPENAI_API_KEY=sk-your-key-here  # Get yours at https://platform.openai.com/api-keys
# OR
GEMINI_API_KEY=your-key-here  # From https://makersuite.google.com/app/apikey
# OR
OPENROUTER_API_KEY=your-key-here  # From https://openrouter.ai/keys
```

#### LangSmith (seriously, get this)

This lets you watch your agents think in real-time. It's incredibly useful:

```bash
LANGSMITH_API_KEY=your-key-here  # Grab from https://smith.langchain.com/settings
LANGSMITH_PROJECT=derivatives-gpt  # Name it whatever you want
ENABLE_LANGSMITH=true
```

#### Extra features

```bash
# Web search for live market data
ENABLE_WEB_SEARCH=true
TAVILY_API_KEY=your-key-here  # Get from https://tavily.com/

# RAG for better educational responses
RAG_ENABLED=true
```

### 4. Install everything

**If you installed UV:**

```bash
uv sync  # That's it! UV handles the venv automatically
```

**If you're using regular pip:**

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 5. Fire it up

```bash
python chainlit_application_launcher.py
```

Your browser should open to `http://localhost:8000` and you're off to the races!

### 6. Watch your agents work (if you set up LangSmith)

This part is optional but super cool if you're curious how the system makes decisions:

**Quick way:**
```bash
python open_langsmith_dashboard.py
```

Then navigate to your project and you'll see:
- Every decision your agents make
- How long each step takes
- Token usage and costs
- The full conversation flow

It's like having X-ray vision into the AI's brain.

## Try asking it stuff

Once you're up and running, here are some things you can try:

**Pricing questions:**
- "Price a call option on AAPL with strike 150, expiry in 30 days"
- "Calculate the price of an iron condor on SPY"
- "What's the value of an American put option on MSFT, strike 280?"

**Learning mode:**
- "Explain what a call option is"
- "How does implied volatility affect option prices?"
- "What's the difference between European and American options?"

**Strategy analysis:**
- "Analyze a bull call spread on NVDA"
- "What's the risk profile of a straddle?"
- "Compare covered call vs cash-secured put strategies"

The system figures out which agent to use based on what you're asking, so just ask naturally.

## Project Structure

```
DerivativesGPT/
├── .env.example                 # Environment variables template
├── .env                        # Your configuration (create from .env.example)
├── chainlit_application_launcher.py  # Main entry point (what you run)
├── derivatives_gpt_core/       # Core application logic
│   ├── agents/                # Multi-agent implementations
│   │   ├── educational/       # Educational agent
│   │   ├── pricing/          # Pricing agent
│   │   └── shared/           # Shared agent utilities
│   ├── features/              # Option pricing models
│   │   ├── vanilla/          # European options
│   │   ├── american/         # American options
│   │   ├── asian/           # Asian options
│   │   ├── digital/         # Digital options
│   │   └── barrier/         # Barrier options
│   ├── core/                 # Core graph and routing logic
│   └── data/                 # Market data providers
├── langgraph/                 # LangGraph deployment configs (optional)
├── prompts/                   # LLM prompt templates
├── tests/                     # Test suite
└── docs/                      # Documentation
```

## When things go wrong

**"API key not found"**
- Double-check your `.env` file is in the project root
- Make sure you didn't add quotes around your API keys
- Verify you set `LLM_PROVIDER` to match whichever key you're using

**"Module not found"**
- Is your virtual environment activated? Look for `(.venv)` in your terminal
- Try reinstalling: `uv sync` or `pip install -r requirements.txt`
- Check your Python version with `python --version` - needs to be 3.11+

**LangSmith traces aren't showing up**
- Make sure `ENABLE_LANGSMITH=true` in your `.env`
- Verify your API key works at https://smith.langchain.com/settings
- Keep your project name simple (no weird characters)

**App won't start**
- Port 8000 might be busy. Try `lsof -i :8000` to check (Mac/Linux)
- Use a different port: `python chainlit_application_launcher.py --port 8001`
- Read the error message carefully - it usually tells you what's wrong

**Still stuck?**
- Check the `docs/` folder for more detailed guides
- Open an issue on GitHub if you think it's a bug
- LangSmith docs are at https://docs.smith.langchain.com/

## For developers

**Running tests:**
```bash
pytest                                    # Run everything
pytest tests/test_pricing_capabilities.py # Just one file
pytest --cov=derivatives_gpt_core        # With coverage report
```

**Code quality tools:**
```bash
black derivatives_gpt_core/      # Format code
mypy derivatives_gpt_core/       # Type checking
ruff check derivatives_gpt_core/ # Linting
```

## LangGraph deployment (optional)

The `langgraph/` folder contains configuration files for LangGraph's deployment tools. You only need these if you want to:

- Use **LangGraph Studio** for visual debugging and development
- Run the **LangGraph dev server** (`langgraph dev`)
- Deploy to **LangGraph Cloud**

If you're just running the Chainlit app (which is the normal way), you can ignore this folder completely.

**To use LangGraph tooling:**
```bash
cd langgraph
langgraph dev  # Starts the LangGraph dev server
```

Then open LangGraph Studio and connect to the local server. You'll get a visual interface showing how your agents make decisions.

## Want to contribute?

Pull requests are welcome! If you're planning something big, open an issue first so we can discuss it.

## Built with

- [LangGraph](https://github.com/langchain-ai/langgraph) and [LangChain](https://github.com/langchain-ai/langchain) for the agent framework
- [Chainlit](https://github.com/Chainlit/chainlit) for the web UI
- [LangSmith](https://smith.langchain.com) for observability

## License

MIT - see the [LICENSE](LICENSE) file