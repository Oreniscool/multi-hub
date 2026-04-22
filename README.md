---
title: MultiHub
emoji: 🚀
colorFrom: blue
colorTo: green
sdk: streamlit
sdk_version: "1.32.0"
python_version: "3.10"
app_file: app.py
pinned: false
---

# MultiHub Dashboard

Unified Streamlit interface that aggregates all business hubs (Case, Simulation, Course, Marketing, Intelligence, Vectorisation, Classification) into a single app. The dashboard lets you switch between hubs via a simple radio selector.

## Apps Included

- Case Study Generator
- MBA Simulation Engine
- AI Course Generator
- Marketing Content & Analytics Hub
- Intelligence Command Center (Market/Competitive/News/SWOT)
- Vectorisation & Embeddings Toolkit
- Text Classification Hub

## Local Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

### Prompt Builder

The Prompt Builder now runs inside this Streamlit app using a modular architecture:

- `app.py` for UI orchestration
- `agents.py` for Planner/Critic/Interviewer flow
- `tools.py` for OAuth, persistence, and runtime helpers
- `prompts.py` for the prompt library

To enable login + Google Sheets saves, configure OAuth environment variables (`GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `OAUTH_REDIRECT_URI`).
For Prompt Builder AI responses, configure a server-side Groq key with `GROQ_API_KEY` (optional model override: `PROMPT_MODEL`).

## Deploy to Streamlit Community Cloud

1. Fork/clone this repository to your GitHub account.
2. On https://share.streamlit.io click "New app".
3. Select the repo, branch (main) and set `app.py` as the entry point.
4. (Optional) Configure environment variables or secrets as needed.

## Repository Structure

```
app.py
agents.py
tools.py
prompts.py
requirements.txt
CaseHub/
ClassificationHub/
CourseHub/
IntelligenceHub/
MarketingHub/
SimulationHub/
VectorisationHub/
```

Each hub folder retains its original Streamlit application files. The dashboard dynamically loads the selected hub while sharing a single Streamlit session.
