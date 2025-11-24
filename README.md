# Recruitment Bot

A production-oriented Recruitment Bot that automates scenario-based technical interviews using LangChain and LangGraph with AWS Bedrock inference. It generates dynamic scenario questions, tracks candidate behavior (including per-question response time), evaluates answers with AI, detects cheating-risk patterns, and produces a final recommendation and detailed scoring. A Streamlit dashboard lets reviewers inspect past interviews with visual insights and graphs.

## Demo

Click the image or the link below to open the demo on YouTube.

[![Demo Video](https://img.youtube.com/vi/H-Z2-6TiKBs/0.jpg)](https://youtu.be/H-Z2-6TiKBs)

Direct link: https://youtu.be/H-Z2-6TiKBs

## Why this project
- Automates interview workflows while preserving scenario realism.
- Tracks behavioral signals (answer time, hesitation) to flag suspicious patterns.
- Produces per-question AI evaluations and an overall recommendation to speed hiring decisions.
- Includes a review dashboard with graphs for trend analysis across interviews.

## Key features
- Scenario-based question generation tuned by role and difficulty.
- Customizable number of questions per interview.
- Smart hints (configurable) when a candidate struggles on a question.
- Per-question answer-time tracking and analytics.
- Cheating-risk analysis using response patterns and timing anomalies.
- Automatic evaluation of each Q&A with feedback and score breakdown.
- Final AI-generated summary & recommendation (hire / no-hire / further review).
- Streamlit dashboard to review past interviews and view visual insights/graphs.
- Built with Streamlit, LangChain, LangGraph, and AWS Bedrock for model inference.

## Quick start (local)
1. Clone the repo
   git clone <your-repo-url>
   cd recruitment_bot
2. Create a virtual environment and install deps
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   pip install -r requirements.txt
3. Configure credentials (see below)
4. Run the app (adjust entrypoint if different)
   streamlit run app.py

## Configuration (required)
- AWS Bedrock credentials (used by LangChain/LangGraph backends)
  - AWS_ACCESS_KEY_ID
  - AWS_SECRET_ACCESS_KEY
  - AWS_REGION
- Optionally, create a `.env` file in the project root:
  AWS_ACCESS_KEY_ID=...
  AWS_SECRET_ACCESS_KEY=...
  AWS_REGION=us-west-2

## Notes
- The exact Streamlit entrypoint may be `app.py` or `src/main.py` depending on repo layout—use the project entrypoint if different.
- Tune question-generation prompts and evaluation thresholds in the LangChain/LangGraph prompt files to match your hiring bar.
- For production, secure credentials with a secrets manager (avoid committing them to source control).

## Project structure (typical)
- app.py — Streamlit entrypoint (interviews & dashboard)
- src/ — implementation: question generation, timing, evaluation, persistence
- models/ — prompt templates and LangChain/LangGraph flows
- requirements.txt — Python dependencies
- README.md — this file

## Contributing
- Open issues or PRs for bug fixes, prompt improvements, analytics, or UI polish.

## License
- Add your license information here.
