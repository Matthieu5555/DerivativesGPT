# DerivativesGPT

An intelligent financial derivatives pricing and educational system powered by LangGraph and LLMs.

## Features

- **Multi-Agent Architecture**: Specialized agents for pricing, education, and market analysis
- **Advanced Pricing Models**: Support for vanilla, American, Asian, digital, and barrier options
- **Educational Assistant**: Interactive explanations of derivatives concepts with adaptive learning
- **Real-time Market Data**: Integration with market data providers
- **LangSmith Observability**: Full tracing and monitoring of agent interactions

## Prerequisites

- Python 3.11 or higher
- UV package manager (recommended) or pip
- API keys for your chosen LLM provider (OpenAI, Google Gemini, or OpenRouter)
- (Optional) LangSmith API key for observability
- (Optional) Tavily API key for web search capabilities

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/DerivativesGPT.git
cd DerivativesGPT
```

### 2. Install UV Package Manager

UV is a fast Python package installer and resolver. Install it using:

```bash
# On macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or using pip
pip install uv
```

### 3. Set Up Environment Variables

Copy the example environment file and configure it with your API keys:

```bash
cp .env.example .env
```

Edit `.env` with your preferred text editor and configure the following:

#### Essential Configuration

```bash
# Choose your LLM provider: "openai", "gemini", or "openrouter"
LLM_PROVIDER=openai

# Configure your chosen provider's API key
OPENAI_API_KEY=your_actual_openai_api_key_here  # Get from https://platform.openai.com/api-keys
# OR
GEMINI_API_KEY=your_actual_gemini_api_key_here  # Get from https://makersuite.google.com/app/apikey
# OR
OPENROUTER_API_KEY=your_actual_openrouter_key_here  # Get from https://openrouter.ai/keys
```

#### LangSmith Configuration (Highly Recommended)

LangSmith provides invaluable observability into your agent's decision-making process:

```bash
# Get your API key from https://smith.langchain.com/settings
LANGSMITH_API_KEY=your_langsmith_api_key_here
LANGSMITH_PROJECT=derivatives-gpt  # Or your custom project name
ENABLE_LANGSMITH=true
```

#### Optional Features

```bash
# Web Search (for real-time market information)
ENABLE_WEB_SEARCH=true
TAVILY_API_KEY=your_tavily_api_key_here  # Get from https://tavily.com/

# RAG (Retrieval-Augmented Generation)
RAG_ENABLED=true  # Enable educational content retrieval
```

### 4. Install Dependencies

Using UV (recommended):

```bash
# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv sync

# Or in one command (UV handles the venv automatically)
uv sync
```

Using pip (alternative):

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 5. Launch the Application

Start the Chainlit web interface:

```bash
# Make sure your virtual environment is activated
python chainlit_application_launcher.py
```

The application will start and open in your browser at `http://localhost:8000`

### 6. Monitor with LangSmith Dashboard (Optional)

If you've configured LangSmith, you can monitor your application in real-time:

1. **Open LangSmith Dashboard**:
   ```bash
   # Use the provided helper script
   python open_langsmith_dashboard.py

   # Or manually open in browser
   python -c "import webbrowser; webbrowser.open('https://smith.langchain.com')"
   ```

2. **Navigate to your project**:
   - Click on your project name (default: "derivatives-gpt")
   - View traces, latency metrics, and token usage
   - Debug agent decision paths

3. **Using the LangSmith CLI** (if installed):
   ```bash
   # Install LangSmith CLI
   pip install langsmith

   # View recent runs
   langsmith runs list --project derivatives-gpt

   # Open dashboard for specific project
   langsmith dashboard --project derivatives-gpt
   ```

## Usage Examples

Once the application is running, you can interact with different agents:

### Pricing Agent
```
"Price a call option on AAPL with strike 150, expiry in 30 days"
"Calculate the price of an iron condor on SPY"
"What's the value of an American put option on MSFT, strike 280?"
```

### Educational Agent
```
"Explain what a call option is"
"How does implied volatility affect option prices?"
"What's the difference between European and American options?"
```

### Strategy Analysis
```
"Analyze a bull call spread on NVDA"
"What's the risk profile of a straddle?"
"Compare covered call vs cash-secured put strategies"
```

## Project Structure

```
DerivativesGPT/
├── .env.example                 # Environment variables template
├── .env                        # Your configuration (create from .env.example)
├── chainlit_application_launcher.py  # Main entry point
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
├── prompts/                   # LLM prompt templates
├── tests/                     # Test suite
└── docs/                      # Documentation
```

## Troubleshooting

### Common Issues

1. **"API key not found" error**
   - Ensure your `.env` file is in the project root
   - Verify API keys are correctly set without quotes
   - Check that you've selected the correct `LLM_PROVIDER`

2. **"Module not found" errors**
   - Make sure your virtual environment is activated
   - Run `uv sync` or `pip install -r requirements.txt` again
   - Verify Python version is 3.11 or higher: `python --version`

3. **LangSmith not showing traces**
   - Verify `ENABLE_LANGSMITH=true` in `.env`
   - Check API key is valid at https://smith.langchain.com/settings
   - Ensure `LANGSMITH_PROJECT` name doesn't contain special characters

4. **Application won't start**
   - Check if port 8000 is available: `lsof -i :8000` (Linux/Mac)
   - Try a different port: `python chainlit_application_launcher.py --port 8001`
   - Check logs for specific error messages

### Getting Help

- **Issues**: Report bugs at [GitHub Issues](https://github.com/yourusername/DerivativesGPT/issues)
- **Documentation**: Check the `docs/` directory for detailed guides
- **LangSmith Docs**: https://docs.smith.langchain.com/

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_pricing_capabilities.py

# Run with coverage
pytest --cov=derivatives_gpt_core
```

### Code Quality

```bash
# Format code
black derivatives_gpt_core/

# Type checking
mypy derivatives_gpt_core/

# Linting
ruff check derivatives_gpt_core/
```

## Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [LangGraph](https://github.com/langchain-ai/langgraph) and [LangChain](https://github.com/langchain-ai/langchain)
- UI powered by [Chainlit](https://github.com/Chainlit/chainlit)
- Observability by [LangSmith](https://smith.langchain.com)