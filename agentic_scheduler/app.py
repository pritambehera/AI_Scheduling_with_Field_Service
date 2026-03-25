import streamlit as st
import pandas as pd
import json
from agents import schedule_agent, handle_disruption, predict_agent, DISRUPTION_TYPES

st.set_page_config(page_title="Field Service AI Scheduler", layout="wide", page_icon="⚡")

st.markdown("""
<style>
  /* Safe Custom Classes only - Streamlit base engine will handle global Theme matching natively */
  .metric-card { border-radius:10px; padding:18px; text-align:center; margin-bottom: 1rem; border: 1px solid rgba(128,128,128,0.2); box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
  .metric-num  { font-size:2.4rem; font-weight:800; color:#4D7C0F; } /* Core Olive */
  .metric-lbl  { font-size:.85rem; margin-top:2px; font-weight:600; text-transform:uppercase; letter-spacing:0.5px; opacity:0.8; }
  .score-high  { color:#15803D; font-weight:700; } 
  .score-low   { color:#B91C1C; font-weight:700; }
  .tag-critical{ background:#DC2626; color:#ffffff; padding:4px 10px; border-radius:4px; font-size:.75rem; font-weight:600;}
  .tag-high    { background:#D97706; color:#ffffff; padding:4px 10px; border-radius:4px; font-size:.75rem; font-weight:600;}
  .tag-medium  { background:#65A30D; color:#ffffff; padding:4px 10px; border-radius:4px; font-size:.75rem; font-weight:600;}
</style>
""", unsafe_allow_html=True)

st.title("⚡ Field Service AI Operations")

# --- NAVBAR ---
if "page" not in st.session_state: st.session_state.page = "Dashboard"

c1, c2, c3, c4 = st.columns(4)
with c1: 
    if st.button("Dashboard", width='stretch', type="primary" if st.session_state.page=="Dashboard" else "secondary"): 
        st.session_state.page = "Dashboard"
        st.rerun()
with c2:
    if st.button("Schedule", width='stretch', type="primary" if st.session_state.page=="Schedule" else "secondary"): 
        st.session_state.page = "Schedule"
        st.rerun()
with c3:
    if st.button("Predictions", width='stretch', type="primary" if st.session_state.page=="Predictions" else "secondary"): 
        st.session_state.page = "Predictions"
        st.rerun()
with c4:
    if st.button("Disruption Sim", width='stretch', type="primary" if st.session_state.page=="Disruption Sim" else "secondary"): 
        st.session_state.page = "Disruption Sim"
        st.rerun()

st.markdown("---")
page = st.session_state.page

# --- STATE INITIALIZATION FOR INCREMENTAL APPENEDS ---
if "processed_files" not in st.session_state: st.session_state.processed_files = set()
if "base_techs" not in st.session_state: st.session_state.base_techs = []
if "schedule" not in st.session_state: st.session_state.schedule = []
if "proactive" not in st.session_state: st.session_state.proactive = []
if "ext" not in st.session_state: st.session_state.ext = {"weather": {}, "traffic": {}, "asset_zones": {}}
if "assets" not in st.session_state: st.session_state.assets = []

# --- UPLOAD SIDEBAR ---
st.sidebar.markdown("### 📁 Core Logic Uploads")
up_assets = st.sidebar.file_uploader("Assets (CSV)", type="csv", key="up_assets")
up_techs  = st.sidebar.file_uploader("Technicians (CSV)", type="csv", key="up_techs")
up_ext    = st.sidebar.file_uploader("Conditions (JSON)", type="json", key="up_ext")

st.sidebar.markdown("---")
st.sidebar.markdown("### 📥 Append Work Orders (Live)")
with st.sidebar.form("append_wos_form", clear_on_submit=True):
    up_wos = st.file_uploader("Upload Work Orders (CSV)", type="csv", key="up_wos")
    submit_wos = st.form_submit_button("Append to Schedule")

if st.sidebar.button("🔄 Factory Reset System"):
    st.session_state.clear()
    st.rerun()

def parse_csv(f, has_skills=False):
    f.seek(0)
    df = pd.read_csv(f)
    if has_skills and "skills" in df.columns:
        df["skills"] = df["skills"].apply(lambda x: [s.strip() for s in x.split(",")] if pd.notna(x) else [])
    return df.to_dict("records")

# Processing logic (runs on any UI change silently)
if up_assets:
    fh = hash(up_assets.getvalue())
    if fh not in st.session_state.processed_files:
        st.session_state.assets = parse_csv(up_assets)
        st.session_state.processed_files.add(fh)
        # Compute proactive 
        st.session_state.proactive = predict_agent(st.session_state.assets)

if up_ext:
    fh = hash(up_ext.getvalue())
    if fh not in st.session_state.processed_files:
        ext_data = json.load(up_ext)
        if st.session_state.assets:
            ext_data["asset_zones"] = {a["id"]: a["zone"] for a in st.session_state.assets}
        st.session_state.ext = ext_data
        st.session_state.processed_files.add(fh)

if up_techs:
    fh = hash(up_techs.getvalue())
    if fh not in st.session_state.processed_files:
        t_data = parse_csv(up_techs, has_skills=True)
        for t in t_data:
            t["current_job"] = None
            t["upcoming_jobs"] = []
            if "available_from" not in t: t["available_from"] = ""
            if "status" not in t: t["status"] = "available"
        st.session_state.base_techs = t_data
        st.session_state.processed_files.add(fh)

# LIVE APPEND: If work orders are explicitly submitted via the form
if submit_wos and up_wos:
    if not st.session_state.base_techs:
        st.sidebar.error("⚠️ Upload Technicians & Ext first before assigning orders!")
    else:
        with st.spinner("Dynamically embedding and assigning new orders..."):
            new_wos = parse_csv(up_wos)
            
            import agents
            # Pre-calculate ADA Embeddings securely
            for t in st.session_state.base_techs:
                if "vector" not in t: 
                    t["vector"] = agents._get_embedding(f"{t.get('skills','')} {t.get('profile', '')}")
            
            import requests, copy
            payload = {
                "region": "System", "horizonHours": 24, "objective": "Routing",
                "constraints": {
                    "work_orders": new_wos,
                    "technicians": st.session_state.base_techs,
                    "external": st.session_state.ext,
                    "assets": st.session_state.assets
                }
            }
            try:
                resp = requests.post("http://localhost:8081/api/v1/schedules/propose", json=payload, timeout=60)
                if resp.status_code == 200:
                    java_sched = resp.json().get("assignments", [])
                    new_schedule = []
                    for w in new_wos:
                        a = next((x for x in java_sched if x.get("workOrderId") == w["id"]), None)
                        w_copy = copy.deepcopy(w)
                        if a:
                            w_copy["tech_id"] = a["technicianId"]
                            w_copy["reason"] = f"Java Proxy: {a['rationale']}"
                            t_name = next((t["name"] for t in st.session_state.base_techs if t["id"] == a["technicianId"]), "Unknown")
                            w_copy["assigned_to"] = t_name
                            w_copy["score"] = 95
                        else:
                            w_copy["tech_id"] = ""
                            w_copy["assigned_to"] = "UNASSIGNED"
                            w_copy["reason"] = "No suitable technician available via proxy."
                        w_copy["completed"] = False
                        new_schedule.append(w_copy)
                    st.session_state.schedule.extend(new_schedule)
                else:
                    st.sidebar.error(f"Java Proxy Error: {resp.status_code}")
            except Exception as e:
                st.sidebar.error(f"Java Integration Error: {e}")
        st.rerun()

# ALIASES FOR UI RENDERING
schedule = st.session_state.schedule
current_techs = st.session_state.base_techs
proactive = st.session_state.proactive
o_ext = st.session_state.ext

def priority_tag(p):
    cls = {"Critical":"tag-critical","High":"tag-high"}.get(p,"tag-medium")
    return f'<span class="{cls}">{p}</span>'

def score_color(s):
    cls = "score-high" if int(s)>=70 else "score-low"
    return f'<span class="{cls}">{s}</span>'

# --- VIEWS ---

if page == "Dashboard":
    st.title("Operations Dashboard")
    
    st.markdown("### 📋 Active Work Orders (Interactive)")
    df_sched = pd.DataFrame(schedule)
    if not df_sched.empty:
        if "completed" not in df_sched.columns: df_sched["completed"] = False
        active_wos = df_sched[df_sched["completed"] == False]
        
        if not active_wos.empty:
            display_cols = ["id", "assigned_to", "priority", "skill", "reason", "completed"]
            edited_df = st.data_editor(
                active_wos[display_cols],
                column_config={
                    "completed": st.column_config.CheckboxColumn("Done", default=False),
                    "id": "WO ID", "assigned_to": "Technician", "priority": "Priority", "reason": "Routing Reason"
                },
                disabled=["id", "assigned_to", "priority", "skill", "reason"],
                width='stretch',
                key="wo_table",
                hide_index=True
            )
            
            # Action completions
            changed = False
            for i, row in edited_df.iterrows():
                if row.get("completed", False):
                    wo_id = row["id"]
                    for s in st.session_state.schedule:
                        if s["id"] == wo_id and not s.get("completed"):
                            s["completed"] = True
                            changed = True
                            # Free up slot immediately
                            tid = s.get("tech_id")
                            if tid:
                                t = next((tx for tx in st.session_state.base_techs if tx["id"] == tid), None)
                                if t:
                                    if t.get("current_job") == wo_id:
                                        if t.get("upcoming_jobs"):
                                            t["current_job"] = t["upcoming_jobs"].pop(0)
                                        else:
                                            t["current_job"] = None
                                            t["status"] = "available"
                                            t["available_from"] = ""
                                    elif isinstance(t.get("upcoming_jobs"), list) and wo_id in t["upcoming_jobs"]:
                                        t["upcoming_jobs"].remove(wo_id)
            if changed:
                st.rerun()
        else:
            st.success("All Jobs completed successfully! 🎉")
    else:
        st.info("No work orders loaded. Awaiting file append...")

    st.markdown("### 👷 Live Technician Tracking")
    if current_techs:
        df_techs = pd.DataFrame(current_techs)[["name", "status", "current_job", "upcoming_jobs", "available_from", "skills"]]
        if "upcoming_jobs" in df_techs.columns:
            df_techs["upcoming_jobs"] = df_techs["upcoming_jobs"].apply(lambda x: ", ".join(x) if isinstance(x, list) else str(x))
        
        def color_status(val):
            color = '#15803D' if val == 'available' else ('#B91C1C' if val == 'busy' else '#D97706')
            return f'background-color: {color}; color: white; font-weight: bold;'
            
        st.dataframe(df_techs.style.map(color_status, subset=['status']), width='stretch')
    else:
        st.info("No Technicians Loaded.")
        
    st.markdown("---")
    c1,c2,c3 = st.columns(3)
    with c1: st.markdown(f'<div class="metric-card"><div class="metric-num">{len(schedule)}</div><div class="metric-lbl">Total Work Orders</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="metric-card"><div class="metric-num">{sum(1 for t in current_techs if t["status"]=="available")}</div><div class="metric-lbl">Available Techs</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="metric-card"><div class="metric-num">{len(proactive)}</div><div class="metric-lbl">Assets at Risk</div></div>', unsafe_allow_html=True)

elif page == "Schedule":
    st.markdown("### 📅 Extrapolated AI Schedule")
    if not schedule: st.info("Pipeline empty.")
    for i, row in enumerate(schedule):
        if row.get("completed"): continue
        label = f"{row['id']} — {row['type']} | {'🟢 Assigned' if row.get('tech_id') else '🔴 UNASSIGNED'} ({row.get('assigned_to')})"
        with st.expander(label):
            col1, col2, col3, col4 = st.columns(4)
            col1.markdown(f"**Priority:**<br>{priority_tag(row['priority'])}", unsafe_allow_html=True)
            col2.markdown(f"**Skill Required:**<br>{row['skill']}", unsafe_allow_html=True)
            col3.markdown(f"**SLA Limit:**<br>{row['sla_hr']} hrs", unsafe_allow_html=True)
            col4.markdown(f"**Metric Score:**<br>{score_color(row.get('score', 0))}/100<br>*(Semantic SIM: {row.get('semantic_match', 0)}%)*", unsafe_allow_html=True)
            
            st.markdown("---")
            st.info(f"**AI Reasoning:** {row.get('reason', 'Routing analysis unavailable.')}")

elif page == "Predictions":
    st.markdown("### 🔮 Predictive Maintenance Output")
    if not proactive: st.info("No assets evaluated or currently above risk threshold.")
    else:
        df = pd.DataFrame(proactive)[["id","asset_id","priority","risk_score","skill"]].rename(columns={"id":"Work Order","asset_id":"Asset"})
        st.dataframe(df.style.background_gradient(subset=["risk_score"],cmap="Reds"), width='stretch')

elif page == "Disruption Sim":
    st.markdown("### ⚡ Dynamic Disruption Simulator")
    st.info("Triggers scenario logic that instantly alters the `external.json` field conditionals (like forcing 'Storm Warning' into the Ext Weather dict) and re-evaluates algorithm limits for online technicians dynamically.")
    event = st.selectbox("Select disruption event", DISRUPTION_TYPES)
    if st.button("🚨 Simulate Event", type="primary"):
        import copy
        new_sched, log = handle_disruption(event, copy.deepcopy(schedule), st.session_state.base_techs, o_ext)
        if log:
            st.error(f"**{len(log)} algorithmic changes pushed:**")
            for entry in log: st.write(f"↳ {entry}")
            st.session_state.schedule = new_sched
            
            st.markdown("### 🔀 Updated Active Schedule")
            df_sched = pd.DataFrame(new_sched)
            if not df_sched.empty:
                active_wos = df_sched[df_sched.get("completed", False) == False]
                display_cols = ["id", "priority", "skill", "zone", "assigned_to", "reason"]
                cols_to_show = [c for c in display_cols if c in active_wos.columns]
                st.dataframe(active_wos[cols_to_show], width='stretch', hide_index=True)
        else:
            st.warning("No changes needed for this disruption.")