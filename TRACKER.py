import os
import re
import json
import shutil
import sqlite3
import pandas as pd
import streamlit as st
from io import BytesIO
from datetime import datetime
from docx import Document
from sqlalchemy import create_engine

from libraries import *
from database import *

st.set_page_config(
    page_title="PRODUCT ENGINEERING - VALIDATION",
    layout="wide",
)

user = st.user

# Load database
database()

def project_tracker():
    # --- Layout definition ---
    with st.sidebar:
        st.markdown("Validation tracker by Vincentiu")
        uploaded_file = st.file_uploader("Choose an Excel file", type="xlsx")
        sel1, sel2 = st.columns(2)
    but1, but2, but3, but4 = st.columns(4, gap="small")

    if uploaded_file:
        fill_database(uploaded_file)
        st.success("Database has been populated successfully.")

    query = "SELECT * FROM ProjectTracker"
    data = get_data_from_db(query)
    data['Day'] = pd.to_datetime(data['Day'], errors='coerce')

    with sel1:
        selected_day = st.date_input("Day started", value=None, min_value=datetime(2025, 9, 1))

    if selected_day:
        data = data[data['Day'] >= pd.to_datetime(selected_day)]

    # Convert booleans
    for col in ["Datasheet", "Function", "EMC"]:
        if col in data.columns:
            data[col] = data[col].astype(bool)

    # Add progress column
    
    data["Progress"] = data.apply(
        lambda row: 0 if row["Homologated"] in ["Passed", "Failed"] else (pd.Timestamp.now() - row["Day"]).days,
        axis=1
    )

    # Define column configs
    column_config = {
        "Datasheet": st.column_config.CheckboxColumn("Datasheet", default=False),
        "Function": st.column_config.CheckboxColumn("Function", default=False),
        "EMC": st.column_config.CheckboxColumn("EMC", default=False),
        "Progress": st.column_config.ProgressColumn(
            "Progress",
            min_value=0,
            max_value=100,
            format="%.0f days"
        ),
        "Homologated": st.column_config.TextColumn(
            "Homologated",
            help="Status of validation",
            validate=".*",
            required=False
        )
    }

    # Apply conditional formatting manually (via styling hints)
    def highlight_row(row):
        color = ""
        if row["Homologated"] == "Validation":
            color = "#FFC107"  # amber
        elif row["Homologated"] == "Failed":
            color = "#8B0000"  # dark red
        elif row["Homologated"] == "Passed":
            color = "#006400"  # dark green
        elif row["Homologated"] == "Datasheet":
            color = "#FFFFFF"  # white
        return [f"background-color: {color}; color: white;" if col == "Homologated" else "" for col in row.index]

    styled_data = data.style.apply(highlight_row, axis=1)

    # Display editable table
    edited_data = st.data_editor(
        data,
        hide_index=True,
        num_rows="dynamic",
        column_config=column_config
    )

    with but1:
        if st.button("💾 Save Changes"):
            engine = create_engine('sqlite:///project_tracker.db')
            edited_data.to_sql('ProjectTracker', con=engine, if_exists='replace', index=False)
            st.success("Changes saved successfully.")

    with but2:
        backup = BytesIO()
        with pd.ExcelWriter(backup) as writer:
            edited_data.to_excel(writer, index=False)
        today = datetime.today().strftime("%d%m%Y")
        st.download_button(
            label="🗂️ Download Backup",
            data=backup.getvalue(),
            file_name=f"Backup_Project_Tracker_{today}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    with but3:
        if st.button('📥 High volume reports'):
            filtered_df = data[
                ~data['REPORTS'].str.strip().str.upper().isin(['OK', 'NA'])
            ]
            for index, row in filtered_df.iterrows():
                test_value = row['Test Choice']
                dut_name = row['DUT SN']
                if test_value and dut_name:
                    template_path = load_template(test_value)
                    if template_path:
                        current_dir = os.path.dirname(os.path.abspath(__file__))
                        report_dir = os.path.join(current_dir, "REPORTS")
                        file_path_pdf = os.path.join(report_dir, f"Report_DCDC_{dut_name}_{test_value}.docx").strip()
                        generate_report(filtered_df[filtered_df.index == index], template_path, file_path_pdf)

    with but4:
        if st.button('💼 Single report'):
            pass

project_tracker()
