"""
Simple test to verify LangSmith is working correctly.
Run this first before using the judge scripts.
"""

import os
from langsmith import Client
from dotenv import load_dotenv

load_dotenv()

print("="*80)
print("LANGSMITH CONNECTION TEST")
print("="*80)

# Get config from .env
api_key = os.getenv("LANGSMITH_API_KEY")
endpoint = os.getenv("LANGSMITH_ENDPOINT")
project = os.getenv("LANGSMITH_PROJECT")

print(f"\nConfiguration:")
print(f"  API Key: {api_key[:20] if api_key else 'NOT SET'}...")
print(f"  Endpoint: {endpoint or 'NOT SET'}")
print(f"  Project: {project or 'NOT SET'}")

# Create client with EU endpoint
print(f"\nConnecting to LangSmith...")
try:
    client = Client(api_url=endpoint, api_key=api_key)

    # Test 1: List projects
    print(f"\nTest 1: List Projects")
    projects = list(client.list_projects(limit=5))
    print(f"  ✓ Found {len(projects)} projects:")
    for p in projects:
        print(f"    - {p.name}")

    # Test 2: Check runs
    print(f"\nTest 2: Check Runs")
    runs = list(client.list_runs(project_name=project, limit=5))
    print(f"  ✓ Found {len(runs)} runs in '{project}'")

    if runs:
        print(f"\n  Latest run:")
        r = runs[0]
        print(f"    ID: {r.id}")
        print(f"    Time: {r.start_time}")
        print(f"    Status: {r.status}")
    else:
        print(f"\n  No runs yet. Generate some by:")
        print(f"    1. Using the Chainlit app")
        print(f"    2. Running integration tests")

    print(f"\n{'='*80}")
    print(f"✓ LANGSMITH CONNECTION SUCCESSFUL!")
    print(f"{'='*80}\n")

except Exception as e:
    print(f"\n✗ Connection failed: {e}")
    print(f"\nTroubleshooting:")
    print(f"  1. Check your API key at: https://smith.langchain.com/settings")
    print(f"  2. Verify .env file has correct LANGSMITH_ENDPOINT")
    print(f"  3. Make sure LANGSMITH_API_KEY is valid")
