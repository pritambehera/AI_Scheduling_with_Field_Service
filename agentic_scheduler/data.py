# data.py — ALL data lives here. Swap with real DB calls later without touching other files.
# OUTPUT CONTRACT: get_data() always returns (assets, technicians, work_orders, external)

import pandas as pd
import json
import os
import copy

def get_data(uploaded_assets=None, uploaded_techs=None, uploaded_wos=None, uploaded_ext=None):
    """
    Returns deep copies of uploaded data. If any are missing, returns None for that category.
    """
    return (
        copy.deepcopy(uploaded_assets) if uploaded_assets is not None else None,
        copy.deepcopy(uploaded_techs) if uploaded_techs is not None else None,
        copy.deepcopy(uploaded_wos) if uploaded_wos is not None else None,
        copy.deepcopy(uploaded_ext) if uploaded_ext is not None else None,
    )
