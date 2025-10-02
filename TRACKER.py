import os, re, shutil, json, sqlite3, plotly
import pandas as pd
import streamlit as st
from io import BytesIO
from datetime import datetime
from sqlalchemy import create_engine
from typing import List, Dict
import plotly.figure_factory as ff
import plotly.graph_objects as go
import plotly.express as px
from docx import Document

import serial, can
import time

 
from database import *  
from validation import *
from todomanager import *
from commtool import * 

st.set_page_config(
    page_title="PRODUCT ENGINEERING - VALIDATION",
    layout="wide",
)


def project_tracker():
    with st.sidebar:
        st.markdown("📊 Validation tracker by Vincentiu")
        uploaded_file = st.file_uploader("Choose an Excel file", type="xlsx")
        debug_mode = st.checkbox("🔧 Developer Mode", value=False)
        if uploaded_file:
            fill_database(uploaded_file)
            st.success("Database has been populated successfully.")

    tab1, tab2, tab3 = st.tabs(["📊 Validation request", "📥Todo!", "💼CLI"])

    with tab1:
        tracker = ValidationTracker()
        but1, but2, but3, but4 = st.columns(4, gap="small")
        st.text("MOS, Diodes and all resonant components need EMC & Functionality test")
        edited_data = tracker.display_editor()
        tracker.display_charts()
        with but1:
            if st.button("💾 Save Changes"):
                tracker.save_changes(edited_data)
        with but2:
            tracker.download_backup(edited_data)
        if debug_mode:
            with but3:
                if st.button("📥 High volume reports"):
                    tracker.generate_reports(edited_data)
            with but4:
                if st.button("💼 Single report"):
                    st.info("Single report generation logic goes here.")

    with tab2:
        todo = TodoManager()
        with st.expander("Add task"):
            todo.add_task()
        todo.display_calendar()

    with tab3:
        st.subheader("💼 RS232 / CAN Command Interface")
        comm = CommTool()
        comm.run_streamlit()

project_tracker()