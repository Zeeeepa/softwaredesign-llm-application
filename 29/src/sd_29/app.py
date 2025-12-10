"""
LangChain Middleware デモアプリケーション
"""

import streamlit as st
from dotenv import load_dotenv

from sd_29.pages import common, scenario1, scenario2, scenario3

load_dotenv()

st.set_page_config(
    page_title="LangChain Middleware デモ",
    layout="wide",
)

common.init_session_state()
scenario = common.render_sidebar()

if scenario == "scenario1":
    scenario1.render()
elif scenario == "scenario2":
    scenario2.render()
elif scenario == "scenario3":
    scenario3.render()
