"""
Test script for supermind-agent-v1 model without Twitter API calls.
"""
import os
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv(dotenv_path=".env", override=True)

# Initialize OpenAI client for AI Builder API
openai_client = OpenAI(
    api_key=os.getenv("SECOND_MIND_API_KEY"),
    base_url="https://space.ai-builders.com/backend/v1"
)

print("Testing supermind-agent-v1 model...")
print(f"API Key loaded: {'Yes' if os.getenv('SECOND_MIND_API_KEY') else 'No'}")
print(f"Base URL: {openai_client.base_url}")
print()

# Test prompt similar to what we'd use for financial analysis
test_prompt = """You are a financial analyst. Analyze the following tweet and extract any buy/sell signals or key financial insights:

Tweet: "@testuser: Just bought more $TSLA at $250. Bullish on EV sector long-term. Also watching $NVDA for entry point."

Please provide:
1. Any buy/sell signals mentioned
2. Key financial insights
3. Market sentiment
4. Source attribution

Format your response in Markdown."""

try:
    print("Sending test request to supermind-agent-v1...")
    print("-" * 60)
    
    response = openai_client.chat.completions.create(
        model="supermind-agent-v1",
        messages=[
            {"role": "system", "content": "You are a financial analyst specializing in extracting actionable insights from social media posts."},
            {"role": "user", "content": test_prompt}
        ],
        temperature=0.7,
        max_tokens=500  # Smaller for testing
    )
    
    print("[OK] Request successful!")
    print("-" * 60)
    print("Response:")
    print(response.choices[0].message.content)
    print("-" * 60)
    print(f"\nModel used: {response.model}")
    print(f"Tokens used: {response.usage.total_tokens} (prompt: {response.usage.prompt_tokens}, completion: {response.usage.completion_tokens})")
    print("\n[OK] Test completed successfully!")
    
except Exception as e:
    print(f"[ERROR] Error occurred: {e}")
    print(f"Error type: {type(e).__name__}")
    if hasattr(e, 'response'):
        print(f"Response status: {e.response.status_code if hasattr(e.response, 'status_code') else 'N/A'}")
        try:
            print(f"Response body: {e.response.json()}")
        except:
            print(f"Response text: {e.response.text if hasattr(e.response, 'text') else 'N/A'}")

