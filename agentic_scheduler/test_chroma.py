import agents
import config
from data import get_data

techs = [{"id": "T001", "name": "Alex Roy", "skills": "electrical,HV", "zone": "Zone-3", "profile": "Expert."}]
wos = [{"id": "WO-101", "skill": "electrical", "zone": "Zone-3", "notes": "Transformer fix.", "priority": "High", "sla_hr": 2}]

print("Running schedule_agent...")
schedule = agents.schedule_agent(wos, techs, {}, "None")
print("Result:")
from pprint import pprint
pprint(schedule)
