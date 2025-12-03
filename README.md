# Financial Signal Aggregator

A web-based MVP for tracking financial influencers on Twitter and generating AI-powered summaries of their market insights.

## Features

- **Account Management**: Add/remove Twitter handles to monitor
- **Intelligent Summarization**: AI-powered summaries that distinguish between latest updates and background context
- **State Management**: Tracks previous summaries and last processed tweet IDs to avoid duplicates
- **Clean UI**: Modern, responsive interface with Markdown rendering

## Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment variables**:
   - Copy `.env.example` to `.env`
   - Add your `TWITTER_API_KEY` (from twitterapi.io)
   - Add your `SECOND_MIND_API_KEY` (from AI Builder Student Portal)

3. **Run the application**:
   ```bash
   python main.py
   ```
   Or using uvicorn directly:
   ```bash
   uvicorn main:app --reload
   ```

4. **Access the application**:
   - Open your browser to `http://localhost:8000`

## API Endpoints

- `GET /` - Serves the frontend HTML
- `GET /manage-accounts` - Get list of monitored accounts
- `POST /manage-accounts` - Add a Twitter handle
- `DELETE /manage-accounts/{handle}` - Remove a Twitter handle
- `POST /refresh-brief` - Fetch new tweets and generate summary

## Data Storage

The application uses `state.json` to store:
- List of monitored Twitter handles
- Session context (previous summaries and last tweet IDs) for each account

## Technology Stack

- **Backend**: FastAPI (Python)
- **Frontend**: HTML/CSS/JavaScript with Marked.js for Markdown rendering
- **Twitter API**: twitterapi.io
- **AI Processing**: AI Builder Student Portal API (secondmind-agent-v1 model)

