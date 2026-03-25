from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import pandas as pd
import json
import os
import copy
from data import get_data
from agents import schedule_agent, predict_agent

app = FastAPI(title="Agentic Scheduler Orchestrator")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

def load_csv(filename, has_skills=False):
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        return []
    df = pd.read_csv(filepath)
    if has_skills and "skills" in df.columns:
        df["skills"] = df["skills"].apply(lambda x: [s.strip() for s in x.split(",")] if pd.notna(x) else [])
    return df.to_dict("records")

def load_json(filename):
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        return {}
    with open(filepath, "r") as f:
        return json.load(f)

# Pre-load data once so the API responds quickly
default_assets = load_csv("assets.csv")
default_techs = load_csv("technicians.csv", has_skills=True)
default_wos = load_csv("work_orders.csv")
default_ext = load_json("external.json")

class ScheduleRequest(BaseModel):
    region: Optional[str] = None
    horizonHours: Optional[int] = 24
    objective: Optional[str] = None
    constraints: Optional[Dict[str, Any]] = None


@app.get("/")
def root():
    return {"message": "Agentic Scheduler Running 🚀"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/api/v1/orchestrate")
def orchestrate(request: ScheduleRequest):
    # Try retrieving data from incoming Java proxy payload constraints
    c = request.constraints or {}
    
    # If UI passes data through Java, use it, otherwise fallback to local defaults
    assets = copy.deepcopy(c.get("assets")) if c.get("assets") is not None else copy.deepcopy(default_assets)
    techs = copy.deepcopy(c.get("technicians")) if c.get("technicians") is not None else copy.deepcopy(default_techs)
    wos = copy.deepcopy(c.get("work_orders")) if c.get("work_orders") is not None else copy.deepcopy(default_wos)
    ext = copy.deepcopy(c.get("external")) if c.get("external") is not None else copy.deepcopy(default_ext)

    # Prepare technician states
    for t in techs:
        t["current_job"] = None
        t["upcoming_jobs"] = []
        if "available_from" not in t: t["available_from"] = ""
        if "status" not in t: t["status"] = "available"

    if assets:
        ext["asset_zones"] = {a["id"]: a["zone"] for a in assets}

    # If region is specified, we might filter wos and techs, 
    # but the AI is smart enough to handle zones via 'ext' and 'vector similarity'.
    # We will just pass them into the agent.
    schedule = schedule_agent(wos, techs, ext)

    # Format output for Java backend ScheduleDto
    assignments = []
    total_score = 0.0
    count = 0
    
    for row in schedule:
        t_id = row.get("tech_id")
        # Ignore unassigned tasks
        if t_id and t_id != "UNASSIGNED":
            assignments.append({
                "technicianId": t_id,
                "workOrderId": row.get("id"),
                "start": "2026-03-26T08:00:00", # Placeholder start
                "end": "2026-03-26T10:00:00",   # Placeholder end
                "travel": {"km": 5.0, "etaMin": 15},
                "rationale": row.get("reason", "AI optimization assignment")
            })
            total_score += float(row.get("score", 0))
            count += 1
            
    avg_score = total_score / count if count > 0 else 0.0

    return {
        "id": "SCH-AI-ORCH",
        "score": avg_score,
        "assignments": assignments
    }
