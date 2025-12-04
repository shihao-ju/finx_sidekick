# Tweet Processing Flow: How Tweets Are Fed to LLM

## Scenario: 3 Accounts, ~20 Tweets Each (Total ~60 Tweets)

### Step 1: Group Tweets by Account
- All ~60 tweets are grouped by account handle
- Example: `hhuang: 20 tweets`, `tig88411109: 20 tweets`, `lord_fed: 20 tweets`

### Step 2: Prioritize Tweets Per Account (Lines 404-439)
For each account:
1. **Categorize tweets by type:**
   - Original tweets (highest priority)
   - Retweets
   - Quote tweets
   - High-engagement replies (only if likes > 50 or RTs > 10)

2. **Take top 8 tweets per account** (prioritized by type, then by order)
   - This ensures we have a good selection from each account
   - Result: Up to 8 tweets × 3 accounts = 24 tweets

### Step 3: Final Selection with Representation Guarantee (Lines 441-464)
**Strategy: Ensure all accounts are represented**

1. **First Pass:** Take at least 2 tweets from each account
   - `tweets_per_account = max(2, 35 // 3) = max(2, 11) = 11`
   - So we take 11 tweets from each account = 33 tweets
   - This ensures `tig88411109` and other accounts are included

2. **Second Pass:** Fill remaining slots (up to 35 total)
   - Remaining slots = 35 - 33 = 2 slots
   - Collect remaining tweets from all accounts (beyond the 11 already taken)
   - Sort by engagement (likes + retweets)
   - Take top 2 highest-engagement tweets
   - Final: 33 + 2 = 35 tweets total

### Step 4: Format Tweets for LLM (Lines 468-524)
Each tweet is formatted as a text string with:
- **Type prefix:** `[ORIGINAL]`, `[RETWEET]`, `[QUOTE]`, or `[REPLY]`
- **Author:** `@username`
- **Content:** Full tweet text (or original tweet text for retweets)
- **Engagement:** `(Likes: X, RTs: Y)`
- **URL:** `[TWEET_URL:https://x.com/...]` (for source tags)

**Example formatted tweet:**
```
[ORIGINAL] @hhuang: Buy $CRDO at $50, target $75. Strong growth trajectory. (Likes: 150, RTs: 25) [TWEET_URL:https://x.com/hhuang/status/123456]
```

All formatted tweets are joined with `\n\n` (double newline) separator.

### Step 5: Extract Tickers (Lines 526-564)
- Extract all ticker symbols (`$SYMBOL`) from:
  - All new tweets (including retweeted/quoted content)
  - Previous summary (for context)
- Filter out placeholders (`$1`, `$2`, `$SYMBOL`)
- Create ticker list: `['$CRDO', '$NVDA', '$TSLA', ...]`

### Step 6: Construct LLM Prompt (Lines 581-665)
The prompt sent to the LLM contains:

```
You are a financial analyst creating actionable market intelligence summaries...

Monitored Accounts: @hhuang, @tig88411109, @lord_fed

Tickers Mentioned in Tweets: $CRDO, $NVDA, $TSLA, ...
CRITICAL INSTRUCTION: Use these EXACT ticker symbols. Do NOT use placeholders...

Previous Summary:
[Previous summary text or "No previous summary available."]

New Tweets (each tweet includes [TWEET_URL:url] at the end):
[ORIGINAL] @hhuang: Tweet 1... (Likes: 150, RTs: 25) [TWEET_URL:https://...]

[RETWEET] @tig88411109 retweeted @other_user: Original tweet text... (Likes: 50, RTs: 10) [TWEET_URL:https://...]

[QUOTE] @lord_fed: Quote tweet text | Quoted @quoted_user: Quoted text... (Likes: 200, RTs: 30) [TWEET_URL:https://...]

[... up to 25 tweets total ...]

INSTRUCTIONS:
[... detailed instructions for News and Trades sections ...]

Format the summary in Markdown with these EXACT sections:
## News
[...]

## Trades
[...]
```

### Step 7: Send to LLM API (Lines 667-690)
- **Model:** `grok-4-fast` (via AI Builder API)
- **System message:** "You are a financial analyst specializing in extracting actionable insights from social media posts."
- **User message:** The full prompt (containing all 25 formatted tweets)
- **Temperature:** 0.7
- **Max tokens:** 3000

### Step 8: Process LLM Response (Lines 692-800)
- Extract summary text from API response
- Check for placeholder tickers (`$1`, `$2`, `$SYMBOL`)
- Replace placeholders with actual tickers if found
- Return final summary

## Key Numbers Summary

| Stage | Count |
|-------|-------|
| **Input tweets** | ~60 (20 per account × 3 accounts) |
| **After per-account prioritization** | Up to 24 (8 per account × 3) |
| **Final tweets sent to LLM** | **35 tweets** (guaranteed representation: at least 11 per account) |
| **Prompt size** | ~7-20K characters (depending on tweet lengths) |
| **Estimated input tokens** | ~3.5K-5K tokens (well within model limits) |
| **Max output tokens** | 3000 |

## Why This Approach?

1. **Representation:** Ensures tweets from all accounts appear in summary
2. **Quality:** Prioritizes original tweets and high-engagement content
3. **Efficiency:** Limits to 25 tweets to stay within token limits while maintaining context
4. **Traceability:** Each tweet includes URL for source attribution

