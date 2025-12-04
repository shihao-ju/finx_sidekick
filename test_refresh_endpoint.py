"""
Test the refresh-brief endpoint to see why summary is empty
"""
import httpx
import json

def test_refresh_brief():
    """Test the refresh-brief endpoint"""
    url = "http://localhost:8001/refresh-brief"
    
    print("="*70)
    print("Testing /refresh-brief endpoint")
    print("="*70 + "\n")
    
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, json={})
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
        if response.status_code == 200:
            data = response.json()
            summary = data.get("summary", "")
            print(f"\nSummary length: {len(summary)}")
            if summary:
                print(f"Summary preview: {summary[:200]}...")
            else:
                print("Summary is EMPTY!")
                
                # Check test data file
                try:
                    with open("test_tweets_data.json", 'r') as f:
                        test_data = json.load(f)
                    print(f"\nTest data file shows:")
                    print(f"  Tweet count: {test_data.get('tweet_count', 0)}")
                    print(f"  Had previous summary: {test_data.get('had_previous_summary', 'N/A')}")
                    print(f"  Since ID used: {test_data.get('since_id_used_for_filtering', 'N/A')}")
                except Exception as e:
                    print(f"Could not read test data file: {e}")
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"Error calling endpoint: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_refresh_brief()

