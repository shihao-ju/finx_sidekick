"""
View current state including previous summaries stored in state.json
"""
import json
import sys
from datetime import datetime

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

def view_state():
    """Display the current state.json contents"""
    try:
        with open("state.json", "r", encoding="utf-8") as f:
            state = json.load(f)
        
        print("=" * 80)
        print("CURRENT STATE (state.json)")
        print("=" * 80)
        
        print(f"\nMonitored Accounts: {state.get('monitored_accounts', [])}")
        print(f"\nNumber of accounts: {len(state.get('monitored_accounts', []))}")
        
        print("\n" + "=" * 80)
        print("SESSION CONTEXT (Previous Summaries & Last Tweet IDs)")
        print("=" * 80)
        
        session_context = state.get("session_context", {})
        
        if not session_context:
            print("\nNo session context found (no previous summaries)")
        else:
            for handle, context in session_context.items():
                print(f"\n{'='*80}")
                print(f"Account: @{handle}")
                print(f"{'='*80}")
                
                last_tweet_id = context.get("last_tweet_id")
                previous_summary = context.get("previous_summary", "")
                
                print(f"\nLast Tweet ID: {last_tweet_id}")
                print(f"\nPrevious Summary Length: {len(previous_summary)} characters")
                
                if previous_summary:
                    print(f"\nPrevious Summary:")
                    print("-" * 80)
                    print(previous_summary)
                    print("-" * 80)
                    
                    # Check for placeholder tickers
                    if "$1" in previous_summary or "$2" in previous_summary or "$SYMBOL" in previous_summary:
                        print("\n⚠️  WARNING: Previous summary contains placeholder tickers ($1, $2, or $SYMBOL)")
                        print("   This is why the AI keeps using $1 - it's referencing the old summary!")
                else:
                    print("\n(No previous summary - this is the first fetch for this account)")
        
        print("\n" + "=" * 80)
        print("END OF STATE")
        print("=" * 80)
        
    except FileNotFoundError:
        print("ERROR: state.json not found!")
        print("The application hasn't been run yet or state file doesn't exist.")
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in state.json: {e}")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    view_state()

