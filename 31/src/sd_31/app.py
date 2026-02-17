"""
LangChain Middleware デモアプリケーション
"""

import streamlit as st
from dotenv import load_dotenv

from sd_31.pages import common, scenario1, scenario2, scenario3

load_dotenv()

st.set_page_config(
    page_title="Software Design誌 第31回 デモアプリケーション",
    layout="wide",
)

common.init_session_state()

pages = [
    st.Page(
        scenario1.render,
        title="【シナリオ1】メール処理",
        url_path="scenario1",
        default=True,
    ),
    st.Page(
        scenario2.render,
        title="【シナリオ2】レジリエンス",
        url_path="scenario2",
    ),
    st.Page(
        scenario3.render,
        title="【シナリオ3】動的ツール選択",
        url_path="scenario3",
    ),
]

current_page = st.navigation(pages, position="sidebar")
current_page.run()
