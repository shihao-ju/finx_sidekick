The Product Definition Brief (PDB)
The Core Problem: I need to track specific financial influencers (FinTwit) for "Alpha" (buy/sell signals, key analysis), but I cannot monitor the feed 24/7. The friction of scrolling through noise to find actionable opinions is too high, and I often miss critical updates or lose track of an analyst's evolving stance over time.

The Minimum Viable Product (MVP): A web application where I can maintain a list of Twitter accounts to watch. It features a "Manual Refresh" workflow that fetches the latest tweets from these accounts via twitterapi.io, compares them against the previous session's context, and uses an LLM to generate a "Catch-Up Summary." This summary highlights key financial events and buy/sell recommendations with relative timestamps.

The OKRs (Objectives & Key Results):

Objective: Efficient extraction of financial signal.

Key Result 1: The system must allow the user to add/remove Twitter handles via a simple search or list input.

Key Result 2: The capture and summarization process must be triggered by a single button click.

Objective: Context-aware intelligence (Rolling State).

Key Result 1: The summary must distinguish between "New Information" (last 60 mins) and "Previous Context."

Key Result 2: The output must identify specific Buy/Sell mentions or Key Events, citing the source handle.