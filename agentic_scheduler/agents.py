# agents.py — AI-First Scheduler with Vector Embeddings
import requests, json, math
import chromadb
import config
from data import get_data

chroma_client = chromadb.PersistentClient(path="./chroma_db")

def _get_embedding(text: str) -> list[float]:
    if not text: return [0.0] * 1536
    url = "https://aicafe.hcl.com/AICafeService/api/v1/subscription/openai/deployments/ada/embeddings?api-version=2023-05-15"
    headers = {
        "api-key": config.OPENAI_API_KEY,
        "Subscription-Key": config.OPENAI_API_KEY,
        "Ocp-Apim-Subscription-Key": config.OPENAI_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {"input": [text]}
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        return response.json()["data"][0]["embedding"]
    except Exception as e:
        print(f"Embedding error: {e}")
        return [0.0] * 1536

def _cosine_similarity(v1: list[float], v2: list[float]) -> float:
    dot = sum(a*b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a*a for a in v1))
    norm2 = math.sqrt(sum(b*b for b in v2))
    return dot / (norm1 * norm2) if norm1 and norm2 else 0.0

def _ask_llm(prompt: str, max_tokens: int = 2500, json_mode: bool = False) -> str:
    url = f"https://aicafe.hcl.com/AICafeService/api/v1/subscription/openai/deployments/{config.MODEL}/chat/completions?api-version=2024-12-01-preview"
    headers = {"api-key": config.OPENAI_API_KEY, "Content-Type": "application/json"}
    sys_prompt = "You are an intelligent Field Service Management AI."
    if json_mode: sys_prompt += " Output strict JSON format."
    payload = {
        "model": config.MODEL,
        "messages": [{"role": "system", "content": sys_prompt}, {"role": "user", "content": prompt}],
        "maxTokens": max_tokens,
        "temperature": 0.2
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"LLM Error: {e}")
        return "[]" if json_mode else ""

def predict_agent(assets: list) -> list:
    if not assets: return []
    prompt = f"""
    Evaluate assets: {json.dumps(assets)}. Generate proactive preventive maintenance work orders for assets with high fail_prob >0.5 or days > 90. Output A STRICT JSON ARRAY ONLY of work orders. Do not include any other conversational text.
    [{{ "id": "WO-P...", "type": "Preventive", "asset_id": "...", "priority": "High", "sla_hr": 4, "effort_hr": 2, "skill": "...", "notes": "...", "risk_score": 0.85 }}]
    """
    res = _ask_llm(prompt, 1500, True)
    
    if not res or res == "[]":
        fallback_wos = []
        for idx, a in enumerate(assets):
            prob = float(a.get("fail_prob", 0)) if "fail_prob" in a else 0.0
            days = int(a.get("days_since_inspect", 0)) if "days_since_inspect" in a else 0
            if prob > 0.5 or days > 90:
                fallback_wos.append({
                    "id": f"WO-P{idx+1000}",
                    "type": "Preventive",
                    "asset_id": a.get("id", f"A{idx}"),
                    "priority": "High" if prob > 0.7 else "Medium",
                    "sla_hr": 4 if prob > 0.7 else 24,
                    "effort_hr": 2,
                    "skill": a.get("req_skill", "electrical"),
                    "notes": f"Fallback AI generator: Risk evaluated at {(prob*100):.1f}% | Days Active: {days}",
                    "risk_score": prob,
                    "zone": a.get("zone", "TBD")
                })
        return fallback_wos

    try:
        import re
        match = re.search(r"\[.*\]", res, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return json.loads(res.replace("```json","").replace("```","").strip())
    except Exception as e:
        print("Predict Agent JSON Parse Error:", e)
        return []

def schedule_agent(work_orders: list, technicians: list, ext: dict, event: str = None) -> list:
    """Uses LLM to assign WO based on vector semantic match and availability constraints."""
    if not work_orders or not technicians: return work_orders
    
    # Use ChromaDB for semantic match vector storage and metric calculation
    try:
        collection = chroma_client.get_or_create_collection(
            name="technicians_vectors",
            metadata={"hnsw:space": "cosine"}
        )
        
        tech_ids = []
        tech_embeddings = []
        tech_metadatas = []
        
        for t in technicians:
            if "vector" not in t: t["vector"] = _get_embedding(f"{t.get('skills')} | {t.get('profile')}")
            tech_ids.append(t["id"])
            tech_embeddings.append(t["vector"])
            tech_metadatas.append({"name": t.get("name", ""), "zone": t.get("zone", "")})
            
        collection.upsert(
            ids=tech_ids,
            embeddings=tech_embeddings,
            metadatas=tech_metadatas
        )
        
        semantic_metrics = {}
        for wo in work_orders:
            wo_vec = _get_embedding(f"{wo.get('skill')} | {wo.get('zone', '')} | {wo.get('notes')}")
            semantic_metrics[wo["id"]] = {}
            
            results = collection.query(
                query_embeddings=[wo_vec],
                n_results=len(technicians)
            )
            
            for t_id, distance in zip(results["ids"][0], results["distances"][0]):
                similarity = max(0.0, 1.0 - distance)
                semantic_metrics[wo["id"]][t_id] = round(similarity * 100, 1)
                
    except Exception as e:
        print(f"Chroma DB Error: {e}")
        semantic_metrics = {}
        for wo in work_orders: semantic_metrics[wo["id"]] = {t["id"]: 0 for t in technicians}

    prompt = f"""
    You are an AI Scheduler optimizing production operations. Assign the best technician dynamically.
    
    Work Orders: {json.dumps([{k:v for k,v in w.items() if k!="vector"} for w in work_orders])}
    Technicians: {json.dumps([{k:v for k,v in t.items() if k!="vector"} for t in technicians])}
    External Conditions: {json.dumps(ext)}
    Pre-Calculated Semantic Vector Match (%) between WOs & Techs: {json.dumps(semantic_metrics)}
    Disruption Active: {event if isinstance(event, str) else 'None'}
    
    Rules:
    1. Assign jobs in priority order from high to low first and only assign to 'available' techs. If a disruption marks someone 'offline', leave them alone.
    2. Keep zone as the primary function for technician selection, balancing it perfectly with Semantic Score, Priority, and SLA. Sometimes you can choose people from another zone if availability or semantic match is optimal.
    3. Let Semantic Score heavily guide routing alongside Zone.
    4. You MAY assign MULTIPLE Work Orders to the SAME technician in rare case when no other related skill technician is available and job is low priority.
    5. Provide the technician's new status -> "busy". Give a projected "tech_available_from" string indicating projected finish times stacked up.
    6. Output the concise objective "reason" detailing why they were chosen computationally.
    
    Output exactly this JSON array:
    [
        {{
            "wo_id": "...",
            "tech_id": "...",
            "assigned_to": "...",
            "score": <0-100 overall fitness int>,
            "reason": "...",
            "semantic_match": <float>,
            "tech_new_status": "busy",
            "tech_available_from": "<projected end time>"
        }}
    ]
    """
    res = _ask_llm(prompt, max_tokens=3000, json_mode=True)
    schedule = []
    try:
        assignments = json.loads(res.replace("```json","").replace("```","").strip())
        assign_map = {a.get("wo_id"): a for a in assignments if isinstance(a, dict)}
        
        techs_ref = {t["id"]: t for t in technicians}
        
        # Build queue per tech
        tech_queue = {}
        for a in assignments:
            if isinstance(a, dict):
                tid = a.get("tech_id")
                if tid:
                    if tid not in tech_queue:
                        tech_queue[tid] = []
                    tech_queue[tid].append(a.get("wo_id"))
                    
        priority_map = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
        wo_prio = {w["id"]: w.get("priority", "Low") for w in work_orders}
        for tid, queue in tech_queue.items():
            queue.sort(key=lambda wid: priority_map.get(wo_prio.get(wid, "Low"), 0), reverse=True)
        
        for wo in work_orders:
            match = assign_map.get(wo["id"], {})
            t_id = match.get("tech_id", "")
            
            if t_id and t_id in techs_ref:
                techs_ref[t_id]["status"] = match.get("tech_new_status", "busy")
                techs_ref[t_id]["available_from"] = match.get("tech_available_from", "busy")
                queue = tech_queue.get(t_id, [])
                if queue:
                    techs_ref[t_id]["current_job"] = queue[0]
                    techs_ref[t_id]["upcoming_jobs"] = queue[1:] if len(queue)>1 else []
            
            schedule.append({
                **wo,
                "assigned_to": match.get("assigned_to", "UNASSIGNED"),
                "tech_id": t_id,
                "score": match.get("score", 0),
                "semantic_match": match.get("semantic_match", semantic_metrics.get(wo["id"], {}).get(t_id, 0)),
                "reason": match.get("reason", "No suitable technician available."),
                "completed": False
            })
    except Exception as e:
        print("LLM Assignment Error:", e)
        for wo in work_orders:
             schedule.append({**wo, "assigned_to": "UNASSIGNED", "tech_id": "", "score": 0, "semantic_match": 0, "reason": "System JSON parser timeout.", "completed": False})
             
    priority_map = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
    schedule.sort(key=lambda x: priority_map.get(x.get("priority", "Low"), 0), reverse=True)
                
    return schedule

DISRUPTION_TYPES = ["Storm Alert Zone-3", "Technician Offline", "New Critical Emergency", "SLA Breach Warning"]

def run_pipeline(assets, techs, wos, ext) -> tuple[list, list]:
    if not assets or not techs or not wos or not ext: return [], []
    ext["asset_zones"] = {a["id"]: a["zone"] for a in assets}
    proactive = predict_agent(assets)
    return schedule_agent(wos + proactive, techs, ext), proactive

def handle_disruption(event: str, schedule: list, techs: list, ext: dict) -> tuple[list, list]:
    if not techs or not schedule: return schedule, []
    
    freed_wos = []
    
    if "Storm" in event:
        ext.setdefault("weather", {})["Zone-3"] = "Storm Warning"
        ext.setdefault("traffic", {})["Zone-3"] = "Severe Roadblocks"
        for row in schedule:
            if row.get("completed"): continue
            t = next((tx for tx in techs if tx["id"]==row.get("tech_id")), None)
            if t and t.get("zone") == "Zone-3":
                t["status"] = "offline"
                t["available_from"] = "Tomorrow"
                # Unassign from the tech so LLM is forced to re-route
                row["tech_id"] = ""
                row["assigned_to"] = "UNASSIGNED"
                freed_wos.append(row)
                
    elif "Offline" in event:
        offline_id = next((t["id"] for t in techs if t["zone"] == "Zone-3" and t["status"] != "offline"), None)
        if offline_id:
            for row in schedule:
                if row.get("completed"): continue
                if row.get("tech_id") == offline_id:
                    t = next((tx for tx in techs if tx["id"]==offline_id), None)
                    if t: t["status"] = "offline"
                    row["tech_id"] = ""
                    row["assigned_to"] = "UNASSIGNED"
                    freed_wos.append(row)
                
    elif "Emergency" in event:
        new_wo = {"id":"WO-911","type":"Emergency","asset_id":"A001", "priority":"Critical","sla_hr":1,"effort_hr":2,"skill":"electrical", "zone": "Zone-3"}
        freed_wos.append(new_wo)
        
    elif "SLA" in event:
        for row in schedule:
            if not row.get("completed") and int(row.get("sla_hr", 99)) <= 4:
                # Elevate priority of near-breach jobs to force re-evaluation
                if row.get("priority") != "Critical":
                    row["priority"] = "Critical"
                    freed_wos.append(row)
        
    if freed_wos:
        new_sched_partial = schedule_agent(freed_wos, techs, ext, event=event)
        
        log = [f"Disruption '{event}' fully processed by LLM."]
        for new_row in new_sched_partial:
            found = False
            for s in schedule:
                if s["id"] == new_row["id"]:
                    s.update(new_row)
                    found = True
                    break
            if not found:
                schedule.insert(0, new_row)
        return schedule, log
    else:
        return schedule, ["Event logged. No jobs structurally orphaned."]
