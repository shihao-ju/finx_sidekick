"""
Test script to show what the summary output looks like in HTML format.
This helps visualize the $1 placeholder issue.
"""
import json
import sys
from datetime import datetime

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Sample summary with $1 placeholders (what the AI is currently outputting)
sample_summary_with_placeholders = """## Actionable Insights
- Sell Signal on $1: Take partial profits at $330 and fully exit at $360 in the short term due to tactical profit-taking amid AI narrative shifts; plan to re-enter long next year if AI revenue drives exponential EPS growth, indicating disciplined risk management in volatile tech.

- Buy Signal on AI Ecosystem: Bullish on OpenAI's growth re-acceleration, projecting 220 million paid ChatGPT subscribers by 2030 (surpassing Netflix soon), supported by hiring "growth savages" and execution—actionable for indirect exposure via ecosystem players like $1; view TPU competition fears against $1 as overblown zero-sum thinking, suggesting dips as buying opportunities.

- Buy Signal on Optics and Hardware: Positive on $1 and $1 for CPO (co-packaged optics) lasers in AI data center transitions, reinforcing infrastructure plays; extend to "Google family" stocks ($1, $1, $1) as portfolio drivers.

## Tickers Mentioned
- $1: Brief context and key insight about each ticker
- $2: Another ticker mentioned
- $SYMBOL: Generic placeholder

## Trading Strategies
- Strategy type: Details, positions, results, and educational explanation

## Market Context
- Background information, market sentiment, and broader context"""

# Sample summary with actual tickers (what it SHOULD look like)
sample_summary_correct = """## Actionable Insights
- Sell Signal on $NVDA: Take partial profits at $330 and fully exit at $360 in the short term due to tactical profit-taking amid AI narrative shifts; plan to re-enter long next year if AI revenue drives exponential EPS growth, indicating disciplined risk management in volatile tech.

- Buy Signal on AI Ecosystem: Bullish on OpenAI's growth re-acceleration, projecting 220 million paid ChatGPT subscribers by 2030 (surpassing Netflix soon), supported by hiring "growth savages" and execution—actionable for indirect exposure via ecosystem players like $NVDA; view TPU competition fears against $NVDA as overblown zero-sum thinking, suggesting dips as buying opportunities.

- Buy Signal on Optics and Hardware: Positive on $LITE and $COHR for CPO (co-packaged optics) lasers in AI data center transitions, reinforcing infrastructure plays; extend to "Google family" stocks ($GOOG, $MSFT, $AAPL) as portfolio drivers.

## Tickers Mentioned
- $NVDA: NVIDIA Corp - Dominant AI GPU provider, trading at mid-to-high teens multiple for 2027 estimates
- $LITE: Lumentum Holdings - CPO laser provider for AI data centers
- $COHR: Coherent Corp - Laser and optics technology for AI infrastructure
- $GOOG: Alphabet Inc - Google parent, AI and cloud divisions
- $MSFT: Microsoft Corp - AI and cloud infrastructure
- $AAPL: Apple Inc - Consumer tech with AI integration

## Trading Strategies
- Strategy type: Details, positions, results, and educational explanation

## Market Context
- Background information, market sentiment, and broader context"""

def generate_html_preview(summary_text, title, filename):
    """Generate HTML preview of summary"""
    from html import escape
    import re
    
    # Convert markdown to HTML (simplified version)
    html = summary_text
    
    # Convert headers
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
    
    # Wrap lists
    html = re.sub(r'(<li>.*?</li>)', r'<ul>\1</ul>', html, flags=re.DOTALL)
    
    # Highlight ticker symbols
    html = re.sub(r'\$([A-Z]{1,5})\b', r'<span class="ticker-badge">$\1</span>', html)
    
    # Highlight problematic placeholders
    html = re.sub(r'\$([0-9]+)\b', r'<span class="placeholder-badge">$\1</span>', html)
    html = html.replace('$SYMBOL', '<span class="placeholder-badge">$SYMBOL</span>')
    
    # Add section styling
    html = html.replace('<h2>Actionable Insights</h2>', '<div class="actionable-section"><h2>Actionable Insights</h2>')
    html = html.replace('<h2>Tickers Mentioned</h2>', '</div><div class="ticker-section"><h2>Tickers Mentioned</h2>')
    html = html.replace('<h2>Trading Strategies</h2>', '</div><div class="trading-strategy-section"><h2>Trading Strategies</h2>')
    html = html.replace('<h2>Market Context</h2>', '</div><div class="market-context-section"><h2>Market Context</h2>')
    html += '</div>'
    
    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
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
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .header {{
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #e0e0e0;
        }}
        .header h1 {{
            color: #667eea;
            margin-bottom: 10px;
        }}
        .summary-content {{
            line-height: 1.8;
            color: #333;
        }}
        .summary-content h2 {{
            margin-top: 24px;
            margin-bottom: 12px;
            color: #667eea;
            border-bottom: 2px solid #667eea;
            padding-bottom: 8px;
        }}
        .summary-content ul {{
            margin-left: 24px;
            margin-bottom: 12px;
        }}
        .summary-content li {{
            margin-bottom: 8px;
        }}
        .ticker-badge {{
            background: #667eea;
            color: white;
            padding: 3px 10px;
            border-radius: 4px;
            font-weight: bold;
            display: inline-block;
            margin: 0 2px;
            font-size: 0.95em;
        }}
        .placeholder-badge {{
            background: #ff4444;
            color: white;
            padding: 3px 10px;
            border-radius: 4px;
            font-weight: bold;
            display: inline-block;
            margin: 0 2px;
            font-size: 0.95em;
            border: 2px solid #cc0000;
        }}
        .actionable-section {{
            background: #f0f8ff;
            border-left: 4px solid #667eea;
            padding: 15px;
            margin: 15px 0;
            border-radius: 5px;
        }}
        .ticker-section {{
            background: #f5f5f5;
            border-left: 4px solid #667eea;
            padding: 15px;
            margin: 15px 0;
            border-radius: 5px;
        }}
        .trading-strategy-section {{
            background: #fff3e0;
            border-left: 4px solid #ff9800;
            padding: 15px;
            margin: 15px 0;
            border-radius: 5px;
        }}
        .market-context-section {{
            background: #f5f5f5;
            border-left: 4px solid #999;
            padding: 15px;
            margin: 15px 0;
            border-radius: 5px;
        }}
        .warning {{
            background: #fff3e0;
            border-left: 4px solid #ff9800;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
        }}
        .warning strong {{
            color: #ff4444;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{title}</h1>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="summary-content">
            {html}
        </div>
        
        <div class="warning">
            <strong>Legend:</strong><br>
            <span class="ticker-badge">$NVDA</span> = Correct ticker symbol (blue badge)<br>
            <span class="placeholder-badge">$1</span> = Placeholder that needs to be fixed (red badge)
        </div>
    </div>
</body>
</html>"""
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(full_html)
    
    print(f"✅ Generated HTML preview: {filename}")

if __name__ == "__main__":
    print("=" * 80)
    print("GENERATING HTML PREVIEWS OF SUMMARY OUTPUT")
    print("=" * 80)
    
    # Generate preview with placeholders (current issue)
    print("\n1. Generating preview with $1 placeholders (CURRENT ISSUE)...")
    generate_html_preview(
        sample_summary_with_placeholders,
        "Summary with $1 Placeholders (CURRENT ISSUE)",
        "summary_with_placeholders.html"
    )
    
    # Generate preview with correct tickers (what it should be)
    print("\n2. Generating preview with correct tickers (SHOULD BE)...")
    generate_html_preview(
        sample_summary_correct,
        "Summary with Correct Tickers (SHOULD BE)",
        "summary_correct.html"
    )
    
    print("\n" + "=" * 80)
    print("COMPLETE!")
    print("=" * 80)
    print("\nOpen these files in your browser:")
    print("  - summary_with_placeholders.html (shows the $1 issue)")
    print("  - summary_correct.html (shows what it should look like)")
    print("\nRed badges = Placeholders that need fixing")
    print("Blue badges = Correct ticker symbols")

