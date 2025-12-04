"""
Parse summaries to extract individual news and trades items with timestamps.
"""
import re
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from tweet_utils import extract_tweet_ids_from_summary, get_tweet_timestamp, get_latest_tweet_timestamp, format_relative_time


def parse_news_items(summary_text: str, tweet_ids: List[str], generation_timestamp: str, tweets_data: Optional[Dict] = None) -> List[Dict]:
    """
    Parse news section from summary and extract individual news items with timestamps.
    
    Args:
        summary_text: The full summary markdown text
        tweet_ids: List of tweet IDs used in this summary
        generation_timestamp: ISO timestamp when summary was generated
        tweets_data: Optional tweets data for timestamp lookup
    
    Returns:
        List of news items with title, content, source_tags, and timestamp
    """
    news_items = []
    
    # Extract News section
    news_match = re.search(r'##\s*News\s*\n([\s\S]*?)(?=##|$)', summary_text, re.IGNORECASE)
    if not news_match:
        return news_items
    
    news_section = news_match.group(1).strip()
    
    # Split by lines
    lines = news_section.split('\n')
    current_item = None
    
    for line in lines:
        line = line.strip()
        if not line:
            # Empty line - save current item if exists
            if current_item:
                news_items.append(current_item)
                current_item = None
            continue
        
        # Check if this is a new news item
        title_match = None
        content = None
        
        # Pattern 1: Starts with bullet point: - **Title**: content
        # Note: Must have space after bullet to avoid matching lines starting with **
        bullet_match = re.match(r'^[-*]\s+(.+)$', line)
        if bullet_match:
            # Save previous item if exists
            if current_item:
                news_items.append(current_item)
            
            content = bullet_match.group(1).strip()
            # Extract title and content (format: **Title**: content or **Title**: content)
            # Handle titles that may contain **$TICKER** patterns inside
            title_match = None
            if content.startswith('**'):
                # Try to find **: pattern first (standard format)
                last_bold_colon = content.rfind('**:')
                if last_bold_colon > 0:
                    title_part = content[:last_bold_colon+3]  # Include **:
                    content_part = content[last_bold_colon+3:].lstrip()
                    if len(content_part) > 10:  # Ensure we have content
                        # Extract title (remove leading ** and trailing **:)
                        title = title_part[2:-3].strip()  # Remove ** at start and **: at end
                        # Create a mock match object
                        class MockMatch:
                            def group(self, n):
                                return [None, title, content_part][n]
                        title_match = MockMatch()
                else:
                    # Fallback: find colon followed by space (format: **Title**: content)
                    colon_pos = content.find(': ')
                    if colon_pos > 0:
                        title_part = content[:colon_pos]
                        content_part = content[colon_pos+2:].lstrip()  # Skip ': '
                        if len(content_part) > 10:  # Ensure we have content
                            # Extract title (remove leading ** and clean up internal ** markers)
                            title = title_part[2:].strip() if title_part.startswith('**') else title_part.strip()
                            # Remove all ** markers from title (e.g., **$CRDO** -> $CRDO)
                            title = title.replace('**', '')
                            # Create a mock match object
                            class MockMatch:
                                def group(self, n):
                                    return [None, title, content_part][n]
                            title_match = MockMatch()
        # Pattern 2: Starts directly with **Title**: (no bullet point)
        else:
            # Handle titles that may contain **$TICKER** patterns inside
            title_match = None
            if line.startswith('**'):
                # Try to find **: pattern first (standard format)
                last_bold_colon = line.rfind('**:')
                if last_bold_colon > 0:
                    title_part = line[:last_bold_colon+3]  # Include **:
                    content_part = line[last_bold_colon+3:].lstrip()
                    if len(content_part) > 10:  # Ensure we have content
                        # Extract title (remove leading ** and trailing **:)
                        title = title_part[2:-3].strip()  # Remove ** at start and **: at end
                        # Save previous item if exists
                        if current_item:
                            news_items.append(current_item)
                        content = line
                        # Create a mock match object
                        class MockMatch:
                            def group(self, n):
                                return [None, title, content_part][n]
                        title_match = MockMatch()
                else:
                    # Fallback: find colon followed by space (format: **Title**: content)
                    colon_pos = line.find(': ')
                    if colon_pos > 0:
                        title_part = line[:colon_pos]
                        content_part = line[colon_pos+2:].lstrip()  # Skip ': '
                        if len(content_part) > 10:  # Ensure we have content
                            # Extract title (remove leading ** and clean up internal ** markers)
                            title = title_part[2:].strip() if title_part.startswith('**') else title_part.strip()
                            # Remove all ** markers from title (e.g., **$CRDO** -> $CRDO)
                            title = title.replace('**', '')
                            # Save previous item if exists
                            if current_item:
                                news_items.append(current_item)
                            content = line
                            # Create a mock match object
                            class MockMatch:
                                def group(self, n):
                                    return [None, title, content_part][n]
                            title_match = MockMatch()
            
            if not title_match:
                # Continuation of current item
                if current_item:
                    current_item["content"] += "\n" + line
                    continue
                else:
                    # No current item and doesn't match patterns - skip
                    continue
        
        # Process the matched item
        # title_match should be set here if Pattern 1 or Pattern 2 matched
        if title_match:
            try:
                content_length = len(title_match.group(2).strip())
                if content_length > 10:
                    title = title_match.group(1).strip()
                    content_text = title_match.group(2).strip()
                    
                    # Extract source tags and tweet IDs BEFORE removing them from content
                    source_tags = []
                    source_tag_regex = r'\[Source:\s*([^\]]+)\]\((https?://[^\s\)]+)\)'
                    for match in re.finditer(source_tag_regex, content_text):
                        handles = [h.strip().replace('@', '') for h in match.group(1).split(',')]
                        url = match.group(2)
                        for handle in handles:
                            source_tags.append({"handle": handle, "url": url})
                    
                    # Extract tweet IDs from source URLs (before removing source tags)
                    item_tweet_ids = extract_tweet_ids_from_summary(content_text)
                    
                    # Remove source tags from content text (both markdown and plain text formats)
                    # Remove markdown format: [Source: @handle](url)
                    content_text = re.sub(r'\[Source:\s*[^\]]+\]\(https?://[^\s\)]+\)', '', content_text)
                    # Remove plain text format: Source: @handle (with optional spacing)
                    content_text = re.sub(r'Source:\s*@\w+', '', content_text, flags=re.IGNORECASE)
                    # Clean up extra whitespace and newlines
                    content_text = re.sub(r'\s+', ' ', content_text)
                    content_text = re.sub(r'\n\s*\n', '\n\n', content_text)
                    content_text = content_text.strip()
                    
                    # Get earliest timestamp from tweet IDs (represents when the news actually happened)
                    # Use earliest instead of latest to show when the news first appeared
                    timestamp = None
                    if item_tweet_ids:
                        # Try to get tweet timestamps
                        timestamps = []
                        for tweet_id in item_tweet_ids:
                            ts = get_tweet_timestamp(tweet_id, tweets_data)
                            if ts:
                                timestamps.append(ts)
                        
                        if timestamps:
                            # Use earliest timestamp (when news first appeared)
                            timestamp = min(timestamps)
                    
                    # Fallback to generation timestamp if no tweet timestamp found
                    # But only use it if it's reasonable (not in the future)
                    if not timestamp:
                        try:
                            gen_ts = datetime.fromisoformat(generation_timestamp.replace('Z', '+00:00'))
                            # Only use generation timestamp if it's not too recent (more than 1 hour ago)
                            # This prevents showing old news as "just now" when summaries are updated
                            now = datetime.now(gen_ts.tzinfo) if gen_ts.tzinfo else datetime.now()
                            if (now - gen_ts).total_seconds() > 3600:  # More than 1 hour old
                                timestamp = gen_ts
                            else:
                                # Generation timestamp is too recent, use a conservative fallback
                                # Use 24 hours before generation time as a safe fallback
                                timestamp = gen_ts - timedelta(hours=24)
                        except:
                            # Last resort: use 24 hours ago
                            timestamp = datetime.now() - timedelta(hours=24)
                    
                    current_item = {
                        "title": title,
                        "content": content_text,
                        "source_tags": source_tags,
                        "timestamp": timestamp.isoformat(),
                        "tweet_ids": item_tweet_ids
                    }
                else:
                    # Content too short, use entire line as title
                    title = content.replace('**', '').strip() if content else line.replace('**', '').strip()
                    current_item = {
                        "title": title,
                        "content": "",
                        "source_tags": [],
                        "timestamp": datetime.fromisoformat(generation_timestamp.replace('Z', '+00:00')).isoformat() if generation_timestamp else datetime.now().isoformat(),
                        "tweet_ids": []
                    }
            except Exception as e:
                # Error processing, use entire line as title
                title = content.replace('**', '').strip() if content else line.replace('**', '').strip()
                current_item = {
                    "title": title,
                    "content": "",
                    "source_tags": [],
                    "timestamp": datetime.fromisoformat(generation_timestamp.replace('Z', '+00:00')).isoformat() if generation_timestamp else datetime.now().isoformat(),
                    "tweet_ids": []
                }
        else:
            # No colon format or invalid match, use entire line as title
            # This should rarely happen if regex is working correctly
            title = content.replace('**', '').strip() if content else line.replace('**', '').strip()
            current_item = {
                "title": title,
                "content": "",
                "source_tags": [],
                "timestamp": datetime.fromisoformat(generation_timestamp.replace('Z', '+00:00')).isoformat() if generation_timestamp else datetime.now().isoformat(),
                "tweet_ids": []
            }
    
    # Add last item
    if current_item:
        news_items.append(current_item)
    
    return news_items


def parse_trades_items(summary_text: str, tweet_ids: List[str], generation_timestamp: str, tweets_data: Optional[Dict] = None) -> List[Dict]:
    """
    Parse trades section from summary and extract individual trade items with timestamps.
    Same logic as parse_news_items but for trades section.
    """
    trades_items = []
    
    # Extract Trades section
    trades_match = re.search(r'##\s*Trades\s*\n([\s\S]*?)(?=##|$)', summary_text, re.IGNORECASE)
    if not trades_match:
        return trades_items
    
    trades_section = trades_match.group(1).strip()
    
    # Split by lines
    lines = trades_section.split('\n')
    current_item = None
    
    for line in lines:
        line = line.strip()
        if not line:
            # Empty line - save current item if exists
            if current_item:
                trades_items.append(current_item)
                current_item = None
            continue
        
        # Check if this is a new trade item
        title_match = None
        content = None
        
        # Pattern 1: Starts with bullet point: - **Title**: content
        # Note: Must have space after bullet to avoid matching lines starting with **
        bullet_match = re.match(r'^[-*]\s+(.+)$', line)
        if bullet_match:
            # Save previous item if exists
            if current_item:
                trades_items.append(current_item)
            
            content = bullet_match.group(1).strip()
            # Extract title and content (format: **Title**: content)
            # Handle titles that may contain **$TICKER** patterns inside
            # Find the LAST **: pattern to separate title from content
            title_match = None
            if content.startswith('**'):
                last_bold_colon = content.rfind('**:')
                if last_bold_colon > 0:
                    title_part = content[:last_bold_colon+3]  # Include **:
                    content_part = content[last_bold_colon+3:].lstrip()
                    if len(content_part) > 10:  # Ensure we have content
                        # Extract title (remove leading ** and trailing **:)
                        title = title_part[2:-3].strip()  # Remove ** at start and **: at end
                        # Create a mock match object
                        class MockMatch:
                            def group(self, n):
                                return [None, title, content_part][n]
                        title_match = MockMatch()
        # Pattern 2: Starts directly with **Title**: (no bullet point)
        else:
            # Handle titles that may contain **$TICKER** patterns inside
            # Find the LAST **: pattern to separate title from content
            title_match = None
            if line.startswith('**'):
                last_bold_colon = line.rfind('**:')
                if last_bold_colon > 0:
                    title_part = line[:last_bold_colon+3]  # Include **:
                    content_part = line[last_bold_colon+3:].lstrip()
                    if len(content_part) > 10:  # Ensure we have content
                        # Extract title (remove leading ** and trailing **:)
                        title = title_part[2:-3].strip()  # Remove ** at start and **: at end
                        # Save previous item if exists
                        if current_item:
                            news_items.append(current_item)
                        content = line
                        # Create a mock match object
                        class MockMatch:
                            def group(self, n):
                                return [None, title, content_part][n]
                        title_match = MockMatch()
            
            if not title_match:
                # Continuation of current item
                if current_item:
                    current_item["content"] += "\n" + line
                    continue
                else:
                    # No current item and doesn't match patterns - skip
                    continue
            if title_match:
                # Save previous item if exists
                if current_item:
                    trades_items.append(current_item)
                content = line
            else:
                # Continuation of current item
                if current_item:
                    current_item["content"] += "\n" + line
                    continue
                else:
                    # No current item and doesn't match patterns - skip
                    continue
        
        # Process the matched item
        if title_match and len(title_match.group(2).strip()) > 10:
            title = title_match.group(1).strip()
            content_text = title_match.group(2).strip()
            
            # Extract source tags and tweet IDs BEFORE removing them from content
            source_tags = []
            source_tag_regex = r'\[Source:\s*([^\]]+)\]\((https?://[^\s\)]+)\)'
            for match in re.finditer(source_tag_regex, content_text):
                handles = [h.strip().replace('@', '') for h in match.group(1).split(',')]
                url = match.group(2)
                for handle in handles:
                    source_tags.append({"handle": handle, "url": url})
            
            # Extract tweet IDs from source URLs (before removing source tags)
            item_tweet_ids = extract_tweet_ids_from_summary(content_text)
            
            # Remove source tags from content text (both markdown and plain text formats)
            # Remove markdown format: [Source: @handle](url)
            content_text = re.sub(r'\[Source:\s*[^\]]+\]\(https?://[^\s\)]+\)', '', content_text)
            # Remove plain text format: Source: @handle (with optional spacing)
            content_text = re.sub(r'Source:\s*@\w+', '', content_text, flags=re.IGNORECASE)
            # Clean up extra whitespace and newlines
            content_text = re.sub(r'\s+', ' ', content_text)
            content_text = re.sub(r'\n\s*\n', '\n\n', content_text)
            content_text = content_text.strip()
            
            # Get earliest timestamp from tweet IDs (represents when the trade actually happened)
            timestamp = None
            if item_tweet_ids:
                # Try to get tweet timestamps
                timestamps = []
                for tweet_id in item_tweet_ids:
                    ts = get_tweet_timestamp(tweet_id, tweets_data)
                    if ts:
                        timestamps.append(ts)
                
                if timestamps:
                    # Use earliest timestamp (when trade first appeared)
                    timestamp = min(timestamps)
            
            # Fallback to generation timestamp if no tweet timestamp found
            # But only use it if it's reasonable (not in the future)
            if not timestamp:
                try:
                    gen_ts = datetime.fromisoformat(generation_timestamp.replace('Z', '+00:00'))
                    # Only use generation timestamp if it's not too recent (more than 1 hour ago)
                    # This prevents showing old trades as "just now" when summaries are updated
                    now = datetime.now(gen_ts.tzinfo) if gen_ts.tzinfo else datetime.now()
                    if (now - gen_ts).total_seconds() > 3600:  # More than 1 hour old
                        timestamp = gen_ts
                    else:
                        # Generation timestamp is too recent, use a conservative fallback
                        # Use 24 hours before generation time as a safe fallback
                        timestamp = gen_ts - timedelta(hours=24)
                except:
                    # Last resort: use 24 hours ago
                    timestamp = datetime.now() - timedelta(hours=24)
            
            current_item = {
                "title": title,
                "content": content_text,
                "source_tags": source_tags,
                "timestamp": timestamp.isoformat(),
                "tweet_ids": item_tweet_ids
            }
        else:
            # No colon format or invalid match, use entire line as title
            # This should rarely happen if regex is working correctly
            title = content.replace('**', '').strip() if content else line.replace('**', '').strip()
            current_item = {
                "title": title,
                "content": "",
                "source_tags": [],
                "timestamp": datetime.fromisoformat(generation_timestamp.replace('Z', '+00:00')).isoformat() if generation_timestamp else datetime.now().isoformat(),
                "tweet_ids": []
            }
    
    # Add last item
    if current_item:
        trades_items.append(current_item)
    
    return trades_items
