"""
Test script to debug why AI is outputting $1 instead of actual ticker symbols.
"""
import json
import sys
import os
from dotenv import load_dotenv
from openai import OpenAI

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Load environment variables
load_dotenv(dotenv_path=".env", override=True)

# Import functions from main.py
from main import extract_tickers, generate_summary

def test_ticker_extraction():
    """Test ticker extraction function"""
    print("=" * 80)
    print("TEST 1: Ticker Extraction")
    print("=" * 80)
    
    test_cases = [
        "RT @EricJhonsa: selling off $NVDA on TPU fears",
        "$LITE $COHR CPO lasers for AI data centers",
        "Bullish on $GOOG $MSFT $AAPL",
        "No tickers here",
        "$1 $2 $SYMBOL",  # Should not match these
    ]
    
    for text in test_cases:
        tickers = extract_tickers(text)
        print(f"\nText: {text}")
        print(f"  Extracted tickers: {tickers}")
    
    print("\n" + "=" * 80)

def test_ticker_extraction_from_tweets():
    """Test ticker extraction from actual tweet data"""
    print("\n" + "=" * 80)
    print("TEST 2: Ticker Extraction from Tweet Data")
    print("=" * 80)
    
    # Sample tweet data similar to what we get from API
    sample_tweets = [
        {
            "text": "RT @EricJhonsa: selling off $NVDA on TPU fears reflects zero-sum thinking",
            "isReply": False,
            "retweeted_tweet": {
                "text": "Ironically, selling off $NVDA on TPU fears reflects the kind of zero-sum/pod-brain thinking that led $GOOG to sell off on OpenAI fears at a fraction of current levels.",
                "author": {"userName": "EricJhonsa"}
            },
            "author": {"userName": "hhuang"}
        },
        {
            "text": "$LITE $COHR I've shared a similar post about CPO lasers",
            "isReply": False,
            "author": {"userName": "hhuang"}
        },
        {
            "text": "@someone well said",
            "isReply": True,
            "author": {"userName": "hhuang"}
        }
    ]
    
    all_tickers = set()
    for tweet in sample_tweets:
        tweet_text = tweet.get("text", "")
        if tweet.get("retweeted_tweet"):
            retweet_text = tweet.get("retweeted_tweet", {}).get("text", "")
            all_tickers.update(extract_tickers(retweet_text))
        if tweet.get("quoted_tweet"):
            quote_text = tweet.get("quoted_tweet", {}).get("text", "")
            all_tickers.update(extract_tickers(quote_text))
        all_tickers.update(extract_tickers(tweet_text))
    
    tickers_list = sorted(all_tickers)
    print(f"\nExtracted tickers from sample tweets: {tickers_list}")
    print(f"Ticker context string: {', '.join(tickers_list) if tickers_list else 'None'}")
    print("\n" + "=" * 80)

def test_prompt_generation():
    """Test prompt generation with sample tweets"""
    print("\n" + "=" * 80)
    print("TEST 3: Prompt Generation")
    print("=" * 80)
    
    sample_tweets = [
        {
            "text": "RT @EricJhonsa: selling off $NVDA on TPU fears",
            "isReply": False,
            "retweeted_tweet": {
                "text": "Ironically, selling off $NVDA on TPU fears reflects the kind of zero-sum/pod-brain thinking that led $GOOG to sell off on OpenAI fears at a fraction of current levels.",
                "author": {"userName": "EricJhonsa"}
            },
            "author": {"userName": "hhuang"},
            "likeCount": 10,
            "retweetCount": 5
        },
        {
            "text": "$LITE $COHR CPO lasers for AI data centers",
            "isReply": False,
            "author": {"userName": "hhuang"},
            "likeCount": 20,
            "retweetCount": 10
        }
    ]
    
    # Extract tickers
    all_tickers = set()
    for tweet in sample_tweets:
        tweet_text = tweet.get("text", "")
        if tweet.get("retweeted_tweet"):
            retweet_text = tweet.get("retweeted_tweet", {}).get("text", "")
            all_tickers.update(extract_tickers(retweet_text))
        all_tickers.update(extract_tickers(tweet_text))
    
    tickers_list = sorted(all_tickers)
    tickers_context = ", ".join(tickers_list) if tickers_list else "None"
    
    ticker_instruction = ""
    if tickers_list:
        ticker_instruction = f"\n\nIMPORTANT: The following tickers are mentioned in the tweets: {', '.join(tickers_list)}. You MUST use these exact ticker symbols in your summary. Do NOT use placeholders like $1, $2, or $SYMBOL."
    
    print(f"\nTickers found: {tickers_list}")
    print(f"\nTicker instruction:\n{ticker_instruction}")
    
    # Format tweets
    formatted_tweets = []
    for tweet in sample_tweets:
        username = tweet.get("author", {}).get("userName", "unknown")
        tweet_text = tweet.get("text", "")
        likes = tweet.get("likeCount", 0)
        retweets = tweet.get("retweetCount", 0)
        
        if tweet.get("retweeted_tweet"):
            retweeted = tweet.get("retweeted_tweet", {})
            original_text = retweeted.get("text", "")
            original_author = retweeted.get("author", {}).get("userName", "unknown")
            formatted_tweets.append(f"[RETWEET] @{username} retweeted @{original_author}: {original_text} (Likes: {likes}, RTs: {retweets})")
        else:
            formatted_tweets.append(f"[ORIGINAL] @{username}: {tweet_text} (Likes: {likes}, RTs: {retweets})")
    
    tweets_text = "\n\n".join(formatted_tweets)
    
    print(f"\nFormatted tweets:\n{tweets_text}")
    
    # Show part of prompt
    prompt_snippet = f"""Tickers Mentioned in Tweets: {tickers_context}{ticker_instruction}

New Tweets:
{tweets_text[:200]}..."""
    
    print(f"\nPrompt snippet:\n{prompt_snippet}")
    print("\n" + "=" * 80)

def test_ai_model_directly():
    """Test AI model directly with a simple prompt"""
    print("\n" + "=" * 80)
    print("TEST 4: Direct AI Model Test")
    print("=" * 80)
    
    SECOND_MIND_API_KEY = os.getenv("SECOND_MIND_API_KEY")
    if not SECOND_MIND_API_KEY:
        print("ERROR: SECOND_MIND_API_KEY not found!")
        return
    
    openai_client = OpenAI(
        api_key=SECOND_MIND_API_KEY,
        base_url="https://space.ai-builders.com/backend/v1",
        timeout=120.0
    )
    
    # Simple test prompt
    test_prompt = """You are a financial analyst. Extract ticker symbols from the following tweets.

Tickers Mentioned in Tweets: $NVDA, $GOOG, $LITE, $COHR

IMPORTANT: The following tickers are mentioned in the tweets: $NVDA, $GOOG, $LITE, $COHR. You MUST use these exact ticker symbols in your summary. Do NOT use placeholders like $1, $2, or $SYMBOL.

New Tweets:
[RETWEET] @hhuang retweeted @EricJhonsa: Ironically, selling off $NVDA on TPU fears reflects the kind of zero-sum/pod-brain thinking that led $GOOG to sell off on OpenAI fears at a fraction of current levels. (Likes: 10, RTs: 5)
[ORIGINAL] @hhuang: $LITE $COHR CPO lasers for AI data centers (Likes: 20, RTs: 10)

Provide a summary mentioning the tickers. Use the EXACT ticker symbols: $NVDA, $GOOG, $LITE, $COHR. Do NOT use $1, $2, or any placeholders."""
    
    print(f"\nSending test prompt to AI model...")
    print(f"Prompt length: {len(test_prompt)} characters")
    
    try:
        response = openai_client.chat.completions.create(
            model="grok-4-fast",
            messages=[
                {"role": "system", "content": "You are a financial analyst specializing in extracting actionable insights from social media posts."},
                {"role": "user", "content": test_prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        if response.choices:
            content = response.choices[0].message.content
            print(f"\nAI Response:")
            print("-" * 80)
            print(content)
            print("-" * 80)
            
            # Check for placeholders
            if "$1" in content or "$2" in content:
                print("\n❌ PROBLEM: AI used placeholders $1 or $2!")
                print(f"   Found: {'$1' if '$1' in content else ''} {'$2' if '$2' in content else ''}")
            else:
                print("\n✅ GOOD: No $1 or $2 placeholders found")
            
            # Check for actual tickers
            found_tickers = []
            for ticker in ["$NVDA", "$GOOG", "$LITE", "$COHR"]:
                if ticker in content:
                    found_tickers.append(ticker)
            
            print(f"\nActual tickers found in response: {found_tickers}")
            
        else:
            print("ERROR: No choices in response")
            
    except Exception as e:
        print(f"ERROR calling AI model: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)

def test_with_real_data():
    """Test with actual data from test_tweets_data.json"""
    print("\n" + "=" * 80)
    print("TEST 5: Test with Real Tweet Data")
    print("=" * 80)
    
    try:
        with open("test_tweets_data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        
        print(f"\nLoaded data structure:")
        print(f"  Keys: {list(data.keys())}")
        
        if "accounts" in data:
            print(f"  Number of accounts: {len(data['accounts'])}")
            for account_data in data["accounts"]:
                handle = account_data.get("handle", "unknown")
                tweets = account_data.get("tweets", [])
                print(f"\n  Account: @{handle}")
                print(f"    Number of tweets: {len(tweets)}")
                
                # Extract tickers from this account's tweets
                all_tickers = set()
                for tweet in tweets[:5]:  # Check first 5 tweets
                    tweet_text = tweet.get("text", "")
                    if tweet.get("retweeted_tweet"):
                        retweet_text = tweet.get("retweeted_tweet", {}).get("text", "")
                        all_tickers.update(extract_tickers(retweet_text))
                    if tweet.get("quoted_tweet"):
                        quote_text = tweet.get("quoted_tweet", {}).get("text", "")
                        all_tickers.update(extract_tickers(quote_text))
                    all_tickers.update(extract_tickers(tweet_text))
                
                tickers_list = sorted(all_tickers)
                print(f"    Tickers found: {tickers_list}")
                
                if not tickers_list:
                    print(f"    ⚠️  WARNING: No tickers found in tweets!")
                    print(f"    Sample tweet text: {tweets[0].get('text', '')[:100] if tweets else 'No tweets'}")
        
    except FileNotFoundError:
        print("test_tweets_data.json not found - skipping real data test")
    except Exception as e:
        print(f"ERROR loading real data: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)

def test_no_tickers_scenario():
    """Test what happens when there are no tickers in tweets"""
    print("\n" + "=" * 80)
    print("TEST 5: No Tickers Scenario")
    print("=" * 80)
    
    # Test with tweets that have no tickers
    sample_tweets = [
        {
            "text": "Great analysis on the market today",
            "isReply": False,
            "author": {"userName": "hhuang"},
            "likeCount": 10,
            "retweetCount": 5
        },
        {
            "text": "Looking forward to earnings next week",
            "isReply": False,
            "author": {"userName": "hhuang"},
            "likeCount": 20,
            "retweetCount": 10
        }
    ]
    
    # Extract tickers
    all_tickers = set()
    for tweet in sample_tweets:
        tweet_text = tweet.get("text", "")
        all_tickers.update(extract_tickers(tweet_text))
    
    tickers_list = sorted(all_tickers)
    print(f"\nTickers found: {tickers_list}")
    print(f"Expected: [] (no tickers)")
    
    if not tickers_list:
        print("\n⚠️  Scenario: No tickers in current tweets")
        print("   This might cause AI to use $1 placeholders if it references")
        print("   tickers from previous summary or general knowledge")
    
    print("\n" + "=" * 80)

def test_previous_summary_with_tickers():
    """Test what happens when previous summary has tickers but new tweets don't"""
    print("\n" + "=" * 80)
    print("TEST 6: Previous Summary with Tickers, New Tweets Without")
    print("=" * 80)
    
    previous_summary = """## Actionable Insights
- Bullish on $NVDA and $GOOG for AI growth

## Tickers Mentioned
- $NVDA: NVIDIA Corp
- $GOOG: Alphabet Inc"""
    
    # New tweets with no tickers
    new_tweets = [
        {
            "text": "Great analysis on the market today",
            "isReply": False,
            "author": {"userName": "hhuang"},
            "likeCount": 10,
            "retweetCount": 5
        }
    ]
    
    print(f"\nPrevious summary contains: $NVDA, $GOOG")
    print(f"New tweets contain: (no tickers)")
    
    # Extract tickers from new tweets only
    all_tickers = set()
    for tweet in new_tweets:
        tweet_text = tweet.get("text", "")
        all_tickers.update(extract_tickers(tweet_text))
    
    tickers_list = sorted(all_tickers)
    print(f"\nTickers extracted from NEW tweets only: {tickers_list}")
    print(f"\n⚠️  Issue: If AI references previous tickers, it might use $1")
    print(f"   Solution: Extract tickers from previous summary too!")
    
    # Extract from previous summary
    prev_tickers = extract_tickers(previous_summary)
    print(f"\nTickers from previous summary: {prev_tickers}")
    print(f"Combined tickers: {sorted(set(tickers_list) | set(prev_tickers))}")
    
    print("\n" + "=" * 80)

def test_full_summary_generation():
    """Test full summary generation function"""
    print("\n" + "=" * 80)
    print("TEST 5: Full Summary Generation Test")
    print("=" * 80)
    
    sample_tweets = [
        {
            "text": "RT @EricJhonsa: selling off $NVDA on TPU fears",
            "isReply": False,
            "retweeted_tweet": {
                "text": "Ironically, selling off $NVDA on TPU fears reflects the kind of zero-sum/pod-brain thinking that led $GOOG to sell off on OpenAI fears at a fraction of current levels.",
                "author": {"userName": "EricJhonsa"}
            },
            "author": {"userName": "hhuang"},
            "likeCount": 10,
            "retweetCount": 5
        },
        {
            "text": "$LITE $COHR CPO lasers for AI data centers",
            "isReply": False,
            "author": {"userName": "hhuang"},
            "likeCount": 20,
            "retweetCount": 10
        }
    ]
    
    print(f"\nTesting generate_summary with {len(sample_tweets)} tweets...")
    print("Tickers in tweets: $NVDA, $GOOG, $LITE, $COHR")
    
    try:
        summary = generate_summary("", sample_tweets, ["hhuang"])
        
        print(f"\nGenerated Summary:")
        print("-" * 80)
        print(summary)
        print("-" * 80)
        
        # Check for placeholders
        if "$1" in summary or "$2" in summary:
            print("\n❌ PROBLEM: Summary contains $1 or $2 placeholders!")
        else:
            print("\n✅ GOOD: No $1 or $2 placeholders in summary")
        
        # Check for actual tickers
        expected_tickers = ["$NVDA", "$GOOG", "$LITE", "$COHR"]
        found_tickers = [t for t in expected_tickers if t in summary]
        print(f"\nExpected tickers: {expected_tickers}")
        print(f"Found tickers in summary: {found_tickers}")
        
    except Exception as e:
        print(f"ERROR generating summary: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("TICKER PLACEHOLDER DEBUG TEST")
    print("=" * 80)
    
    # Run all tests
    test_ticker_extraction()
    test_ticker_extraction_from_tweets()
    test_prompt_generation()
    test_ai_model_directly()
    test_with_real_data()
    test_no_tickers_scenario()
    test_previous_summary_with_tickers()
    test_full_summary_generation()
    
    print("\n" + "=" * 80)
    print("ALL TESTS COMPLETE")
    print("=" * 80)

