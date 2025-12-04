"""
Tweet Data Viewer - Clean and display tweets from test_tweets_data.json in HTML format.
Shows original posts, retweets, replies, and quote tweets with clear visual distinction.
"""
import json
import sys
from datetime import datetime
from html import escape

# Fix Windows console encoding for Unicode characters
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')


def parse_twitter_date(date_str):
    """Parse Twitter date format: 'Wed Nov 26 03:34:05 +0000 2025'"""
    try:
        # Format: "Wed Nov 26 03:34:05 +0000 2025"
        dt = datetime.strptime(date_str, "%a %b %d %H:%M:%S %z %Y")
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except:
        return date_str


def get_tweet_type(tweet):
    """Determine the type of tweet: Original, Retweet, Reply, Quote, or Reply+Quote"""
    is_reply = tweet.get("isReply", False)
    has_retweet = tweet.get("retweeted_tweet") is not None
    has_quote = tweet.get("quoted_tweet") is not None
    
    if has_retweet:
        if is_reply:
            return "Reply+Retweet"
        return "Retweet"
    elif has_quote:
        if is_reply:
            return "Reply+Quote"
        return "Quote Tweet"
    elif is_reply:
        return "Reply"
    else:
        return "Original"


def get_tweet_content(tweet):
    """Extract the main tweet content, handling retweets and quotes"""
    text = tweet.get("text", "")
    
    # For retweets, the text usually starts with "RT @username:"
    # We'll show both the retweeter's text (if any) and the original
    retweeted = tweet.get("retweeted_tweet")
    quoted = tweet.get("quoted_tweet")
    
    return text, retweeted, quoted


def format_tweet_html(tweet, account_handle, tweet_num):
    """Format a single tweet as HTML"""
    tweet_type = get_tweet_type(tweet)
    text, retweeted, quoted = get_tweet_content(tweet)
    
    # Get tweet metadata
    tweet_id = tweet.get("id", "N/A")
    created_at = parse_twitter_date(tweet.get("createdAt", ""))
    author = tweet.get("author", {})
    author_name = author.get("name", "Unknown")
    author_username = author.get("userName", account_handle)
    
    # Engagement metrics
    likes = tweet.get("likeCount", 0)
    retweets = tweet.get("retweetCount", 0)
    replies = tweet.get("replyCount", 0)
    views = tweet.get("viewCount", 0)
    
    # Determine CSS class based on tweet type
    type_class = tweet_type.lower().replace("+", "-")
    
    # Build HTML
    html = f"""
    <div class="tweet tweet-{type_class}">
        <div class="tweet-header">
            <span class="tweet-number">#{tweet_num}</span>
            <span class="tweet-type type-{type_class}">{tweet_type}</span>
            <span class="tweet-date">{created_at}</span>
        </div>
        <div class="tweet-author">
            <strong>{escape(author_name)}</strong> (@{escape(author_username)})
        </div>
        <div class="tweet-content">
            <p>{escape(text)}</p>
        </div>
    """
    
    # Add retweeted content if present
    if retweeted:
        rt_author = retweeted.get("author", {})
        rt_username = rt_author.get("userName", "Unknown")
        rt_text = retweeted.get("text", "")
        rt_date = parse_twitter_date(retweeted.get("createdAt", ""))
        html += f"""
        <div class="retweeted-content">
            <div class="retweeted-header">Retweeted from @{escape(rt_username)} ({rt_date})</div>
            <div class="retweeted-text">{escape(rt_text)}</div>
        </div>
        """
    
    # Add quoted tweet if present
    if quoted:
        qt_author = quoted.get("author", {})
        qt_username = qt_author.get("userName", "Unknown")
        qt_text = quoted.get("text", "")
        qt_date = parse_twitter_date(quoted.get("createdAt", ""))
        html += f"""
        <div class="quoted-content">
            <div class="quoted-header">Quoted tweet from @{escape(qt_username)} ({qt_date})</div>
            <div class="quoted-text">{escape(qt_text[:500])}{"..." if len(qt_text) > 500 else ""}</div>
        </div>
        """
    
    # Add reply info if it's a reply
    if tweet.get("isReply", False):
        in_reply_to = tweet.get("inReplyToUsername")
        if in_reply_to:
            html += f"""
        <div class="reply-info">
            ↳ Replying to @{escape(in_reply_to)}
        </div>
        """
    
    # Add engagement metrics
    html += f"""
        <div class="tweet-metrics">
            <span class="metric">❤️ {likes:,}</span>
            <span class="metric">🔄 {retweets:,}</span>
            <span class="metric">💬 {replies:,}</span>
            <span class="metric">👁️ {views:,}</span>
        </div>
        <div class="tweet-footer">
            <a href="{tweet.get('url', '#')}" target="_blank">View on Twitter</a>
            <span class="tweet-id">ID: {tweet_id}</span>
        </div>
    </div>
    """
    
    return html


def generate_html(data):
    """Generate complete HTML document from tweet data"""
    fetch_timestamp = data.get("fetch_timestamp", "")
    total_accounts = data.get("total_accounts", 0)
    accounts = data.get("accounts", [])
    
    # Count tweet types across all accounts
    type_counts = {}
    total_tweets = 0
    
    for account_data in accounts:
        tweets = account_data.get("tweets", [])
        total_tweets += len(tweets)
        for tweet in tweets:
            tweet_type = get_tweet_type(tweet)
            type_counts[tweet_type] = type_counts.get(tweet_type, 0) + 1
    
    # Generate HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tweet Data Viewer</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #f5f5f5;
            padding: 20px;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .header {{
            background: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .header h1 {{
            color: #1da1f2;
            margin-bottom: 10px;
        }}
        .stats {{
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
            margin-top: 20px;
        }}
        .stat-item {{
            background: #f0f8ff;
            padding: 10px 15px;
            border-radius: 5px;
            border-left: 4px solid #1da1f2;
        }}
        .account-section {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .account-header {{
            border-bottom: 2px solid #e1e8ed;
            padding-bottom: 15px;
            margin-bottom: 20px;
        }}
        .account-header h2 {{
            color: #14171a;
            margin-bottom: 5px;
        }}
        .account-meta {{
            color: #657786;
            font-size: 0.9em;
        }}
        .tweet {{
            border: 1px solid #e1e8ed;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            background: white;
            transition: box-shadow 0.2s;
        }}
        .tweet:hover {{
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }}
        .tweet-header {{
            display: flex;
            gap: 10px;
            align-items: center;
            margin-bottom: 10px;
            flex-wrap: wrap;
        }}
        .tweet-number {{
            background: #1da1f2;
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            font-weight: bold;
            font-size: 0.85em;
        }}
        .tweet-type {{
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 0.85em;
            font-weight: bold;
        }}
        .type-original {{
            background: #e8f5e9;
            color: #2e7d32;
        }}
        .type-retweet {{
            background: #e3f2fd;
            color: #1565c0;
        }}
        .type-reply {{
            background: #fff3e0;
            color: #e65100;
        }}
        .type-quote-tweet {{
            background: #f3e5f5;
            color: #6a1b9a;
        }}
        .type-reply-quote {{
            background: #fce4ec;
            color: #c2185b;
        }}
        .type-reply-retweet {{
            background: #e0f2f1;
            color: #00695c;
        }}
        .tweet-date {{
            color: #657786;
            font-size: 0.9em;
            margin-left: auto;
        }}
        .tweet-author {{
            margin-bottom: 10px;
            color: #14171a;
        }}
        .tweet-content {{
            margin-bottom: 15px;
            color: #14171a;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        .retweeted-content {{
            background: #f0f8ff;
            border-left: 4px solid #1da1f2;
            padding: 15px;
            margin: 15px 0;
            border-radius: 5px;
        }}
        .retweeted-header {{
            color: #1da1f2;
            font-weight: bold;
            margin-bottom: 8px;
            font-size: 0.9em;
        }}
        .retweeted-text {{
            color: #14171a;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        .quoted-content {{
            background: #f5f5f5;
            border-left: 4px solid #6a1b9a;
            padding: 15px;
            margin: 15px 0;
            border-radius: 5px;
        }}
        .quoted-header {{
            color: #6a1b9a;
            font-weight: bold;
            margin-bottom: 8px;
            font-size: 0.9em;
        }}
        .quoted-text {{
            color: #14171a;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        .reply-info {{
            color: #657786;
            font-size: 0.9em;
            margin: 10px 0;
            font-style: italic;
        }}
        .tweet-metrics {{
            display: flex;
            gap: 20px;
            margin: 15px 0;
            padding-top: 15px;
            border-top: 1px solid #e1e8ed;
            flex-wrap: wrap;
        }}
        .metric {{
            color: #657786;
            font-size: 0.9em;
        }}
        .tweet-footer {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #e1e8ed;
        }}
        .tweet-footer a {{
            color: #1da1f2;
            text-decoration: none;
        }}
        .tweet-footer a:hover {{
            text-decoration: underline;
        }}
        .tweet-id {{
            color: #657786;
            font-size: 0.8em;
            font-family: monospace;
        }}
        .legend {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .legend h3 {{
            margin-bottom: 15px;
            color: #14171a;
        }}
        .legend-items {{
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🐦 Tweet Data Viewer</h1>
            <p>Fetched at: {fetch_timestamp}</p>
            <div class="stats">
                <div class="stat-item">
                    <strong>Total Accounts:</strong> {total_accounts}
                </div>
                <div class="stat-item">
                    <strong>Total Tweets:</strong> {total_tweets}
                </div>
"""
    
    # Add type counts to stats
    for tweet_type, count in sorted(type_counts.items()):
        html += f"""
                <div class="stat-item">
                    <strong>{tweet_type}:</strong> {count}
                </div>
"""
    
    html += """
            </div>
        </div>
        
        <div class="legend">
            <h3>Legend</h3>
            <div class="legend-items">
                <div class="legend-item">
                    <span class="tweet-type type-original">Original</span>
                    <span>Original post</span>
                </div>
                <div class="legend-item">
                    <span class="tweet-type type-retweet">Retweet</span>
                    <span>Retweeted content</span>
                </div>
                <div class="legend-item">
                    <span class="tweet-type type-reply">Reply</span>
                    <span>Reply to another tweet</span>
                </div>
                <div class="legend-item">
                    <span class="tweet-type type-quote-tweet">Quote Tweet</span>
                    <span>Quote tweet with comment</span>
                </div>
                <div class="legend-item">
                    <span class="tweet-type type-reply-quote">Reply+Quote</span>
                    <span>Reply that quotes a tweet</span>
                </div>
            </div>
        </div>
"""
    
    # Generate HTML for each account
    for account_data in accounts:
        handle = account_data.get("handle", "Unknown")
        fetch_time = account_data.get("fetch_timestamp", "")
        tweet_count = account_data.get("tweet_count", 0)
        had_previous_summary = account_data.get("had_previous_summary", False)
        since_id = account_data.get("since_id_used_for_filtering")
        tweets = account_data.get("tweets", [])
        
        html += f"""
        <div class="account-section">
            <div class="account-header">
                <h2>@{escape(handle)}</h2>
                <div class="account-meta">
                    Fetched: {fetch_time} | 
                    Tweets: {tweet_count} | 
                    Previous Summary: {'Yes' if had_previous_summary else 'No'} | 
                    Since ID: {since_id if since_id else 'None (first fetch)'}
                </div>
            </div>
"""
        
        # Generate HTML for each tweet
        for idx, tweet in enumerate(tweets, 1):
            html += format_tweet_html(tweet, handle, idx)
        
        html += """
        </div>
"""
    
    html += """
    </div>
</body>
</html>
"""
    
    return html


def main():
    """Main function to load data and generate HTML"""
    input_file = "test_tweets_data.json"
    output_file = "tweets_viewer.html"
    
    try:
        print(f"Loading data from {input_file}...")
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print("Generating HTML...")
        html = generate_html(data)
        
        print(f"Writing HTML to {output_file}...")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"\n✅ Success! HTML file generated: {output_file}")
        print(f"   Open it in your browser to view the tweets.")
        
        # Print summary
        accounts = data.get("accounts", [])
        total_tweets = sum(acc.get("tweet_count", 0) for acc in accounts)
        print(f"\nSummary:")
        print(f"  - Accounts: {len(accounts)}")
        print(f"  - Total tweets: {total_tweets}")
        
        # Count types
        type_counts = {}
        for account_data in accounts:
            for tweet in account_data.get("tweets", []):
                tweet_type = get_tweet_type(tweet)
                type_counts[tweet_type] = type_counts.get(tweet_type, 0) + 1
        
        print(f"\nTweet types:")
        for tweet_type, count in sorted(type_counts.items()):
            print(f"  - {tweet_type}: {count}")
        
    except FileNotFoundError:
        print(f"❌ Error: {input_file} not found!")
        print("   Make sure you've fetched tweets first using /refresh-brief endpoint.")
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in {input_file}")
        print(f"   {e}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

