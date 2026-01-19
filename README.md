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

The Prompt Builder now runs inside Streamlit with optional Google Sheets logging. Set `google_service_account` (Streamlit secrets) or `GOOGLE_SHEETS_CREDS` (env var) with your service account JSON to enable saves.

## Deploy to Streamlit Community Cloud

1. Fork/clone this repository to your GitHub account.
2. On https://share.streamlit.io click "New app".
3. Select the repo, branch (main) and set `app.py` as the entry point.
4. (Optional) Configure environment variables or secrets as needed.

## Repository Structure

```
app.py
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

### Prompt Builder (Next.js) inside MultiHub

- The radio menu now includes **PromptBuilder**; selecting it embeds the Next.js prompt builder via iframe.
- Configure the target URL with `PROMPT_BUILDER_URL` (defaults to `http://localhost:3000`).
