#!/usr/bin/env python
"""
Open LangSmith Dashboard in the browser.
This script helps users quickly access their LangSmith project dashboard.
"""

import webbrowser
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

def open_langsmith_dashboard():
    """Open the LangSmith dashboard in the default browser."""

    # Get project name from environment or use default
    project_name = os.getenv('LANGSMITH_PROJECT', 'derivatives-gpt')

    # Check if LangSmith is enabled
    langsmith_enabled = os.getenv('ENABLE_LANGSMITH', 'false').lower() == 'true'

    if not langsmith_enabled:
        print("⚠️  LangSmith is not enabled in your .env file")
        print("    Set ENABLE_LANGSMITH=true to enable observability")
        response = input("\nWould you like to open the dashboard anyway? (y/n): ")
        if response.lower() != 'y':
            return

    # Check if API key is set
    api_key = os.getenv('LANGSMITH_API_KEY')
    if not api_key or api_key == 'your_langsmith_api_key_here':
        print("⚠️  LANGSMITH_API_KEY is not configured in .env")
        print("    Get your API key from: https://smith.langchain.com/settings")
        print("\nOpening LangSmith homepage...")
        webbrowser.open('https://smith.langchain.com')
    else:
        # Open project-specific dashboard
        dashboard_url = f'https://smith.langchain.com/o/default/projects/p/{project_name}'
        print(f"✅ Opening LangSmith dashboard for project: {project_name}")
        print(f"   URL: {dashboard_url}")
        webbrowser.open(dashboard_url)

        print("\n📊 Dashboard Features:")
        print("   • View real-time traces of agent interactions")
        print("   • Monitor latency and token usage")
        print("   • Debug decision paths and errors")
        print("   • Analyze feedback and performance metrics")

if __name__ == "__main__":
    open_langsmith_dashboard()