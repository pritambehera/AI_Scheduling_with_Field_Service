# Agentic AI Field Service Scheduler

## File Map (connection points are explicit)

```
config.py          ← ALL settings, API key, model name, zone/skill constants
data.py            ← ALL synthetic data (assets, technicians, work orders, weather)
agents.py          ← ALL 4 agents (predict, schedule, disrupt, explain) — uses config + data
app.py             ← Streamlit UI — calls agents.py ONLY, never touches data.py directly
```

## To swap parts:
- Change **frontend**: edit only `app.py`
- Change **AI model / prompts**: edit only `agents.py`
- Change **data source** (real DB later): edit only `data.py`
- Change **constants / API key**: edit only `config.py`

## Run the Integrated Solution (FastAPI + Streamlit):
The AI scheduler no longer just runs Streamlit; it now simultaneously serves a `FastAPI` orchestrator for the Java Spring Boot service.

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Start the AI Orchestrator and UI:
```bash
chmod +x start.sh
./start.sh
```

*(This will launch the `FastAPI` endpoint on port `8080`, and the `Streamlit` UI on port `8501`. Your Java service can then be started independently on port `8081`.)*
