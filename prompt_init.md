I want to build a web-based MVP for a "Financial Signal Aggregator." You can find the Product Definition Brief in product_definition_brief.md.
This is a full-stack application using FastAPI (Python) for the backend and a simple HTML/JS frontend.
1. Data & State Management: Create a simple file-based storage system (e.g., state.json or database.db). It needs to store:
Monitored Accounts: A list of Twitter handles (e.g., @ElonMusk, @JimCramer).
Session Context: Store the text of the previous summary and the last_tweet_id processed for each account. This is crucial to avoid re-reading old data.
2. Technology & Tools:
Twitter Data: You must use the twitterapi.io API (or a compatible alternative like Apify) to fetch tweets. Assume I have an API Key provided in a .env file.
AI Processing: You must interact with the AI Builder Student Portal API. The OpenAPI specification is at https://space.ai-builders.com/backend/openapi.json. The API Key is in a .env file as SECOND_MIND_API_KEY. All AI calls must use the openai SDK, point to the correct base URL (https://space.ai-builders.com/backend/v1), and use the model secondmind-agent-v1.
3. Backend Implementation (FastAPI):
Endpoint 1: /manage-accounts (POST/GET): Allow the frontend to add or remove Twitter handles from the Monitored Accounts list.
Endpoint 2: /refresh-brief (POST): This is the core logic. When called:
Fetch: Iterate through the Monitored Accounts. Call the Twitter API to get only new tweets published since the last_tweet_id.
Load Context: Read the previous_summary from your state file.
LLM Call: Construct a prompt that includes the Previous Summary and the New Tweets.
Instruction to AI: "You are a financial analyst. Update the 'Previous Summary' based on the 'New Tweets'. Focus on buy/sell signals, key events, and market sentiment. Use relative time (e.g., '10 mins ago'). If new tweets contradict the previous summary, note the change. If no new tweets exist, maintain the old summary."
Update State: Overwrite previous_summary with the new result and update last_tweet_id.
Return: Return the new summary to the frontend.
4. Front-End Implementation (HTML/JS): Create a clean index.html.
Sidebar/Top Bar: A simple input field to type a Twitter handle and an "Add" button to update the list.
Main Action: A large "Refresh Market Intel" button.
Display Area: A distinct panel that renders the Markdown summary returned by the backend. It should clearly separate "Latest Updates" from "Background Context."