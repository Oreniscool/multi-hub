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
streamlit run dashboard.py
```

## Deploy to Streamlit Community Cloud

1. Fork/clone this repository to your GitHub account.
2. On https://share.streamlit.io click "New app".
3. Select the repo, branch (main) and set `dashboard.py` as the entry point.
4. (Optional) Configure environment variables or secrets as needed.

## Repository Structure

```
dashboard.py
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
