import streamlit as st
from datetime import date

if 'history' not in st.session_state:
    st.session_state['history'] = []

st.set_page_config(
    page_title="智慧問診機器人",
    page_icon="🩺"
)

with st.sidebar:
    st.header("📋 基本資料填寫")

    name = st.text_input(
        "姓名",
        value=st.session_state.get("name", "")
    )

    id_number = st.text_input(
        "身分證字號",
        value=st.session_state.get("id_number", "")
    )

    birthday = st.date_input(
        "出生年月日",
        value=st.session_state.get("birthday", "today"),
        min_value="1900-01-01",
        max_value=date.today()
    )

    blood_type = st.selectbox(
        "血型",
        ["", "A", "B", "AB", "O"],
        index=["", "A", "B", "AB", "O"].index(
            st.session_state.get("blood_type", "")
        )
    )