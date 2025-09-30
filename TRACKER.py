import re, shutil, json, sqlite3, plotly, os

import streamlit as st
import pandas as pd
from docx import Document
from datetime import datetime
import plotly.figure_factory as ff
from sqlalchemy import create_engine
from io import BytesIO

from libraries import *
from database import *


st.set_page_config(
      page_title="PRODUCT ENGINEERING - VALIDATION",
      layout="wide", 
      
      )

user = st.user

# Load database
database()

def highlight_step(row):
    if row["Step"] == "Passed":
        return ["background-color: #1b5e20; color: white"] * len(row)
    elif row["Step"] == "Failed":
        return ["background-color: #b71c1c; color: white"] * len(row)
    elif row["Step"] == "Validation":
        return ["background-color: #f57f17; color: black"] * len(row)
    else:
        return [""] * len(row)


def project_tracker():
    # --- Layout definition -- 
    with st.sidebar:
        st.markdown("""
                    Project tracker developed for Validation by Vincentiu
                     """)

        uploaded_file = st.file_uploader("Choose an Excel file", type="xlsx")
    but1, but2, but3, but4 = st.columns(4, gap="small")

    if uploaded_file:
        fill_database(uploaded_file)
        st.success("Database has been populated successfully.")

    query = "SELECT * FROM ProjectTracker" # WHERE user_email= '{user.email}"
    data = get_data_from_db(query)
    data['Day'] = pd.to_datetime(data['Day'], errors='coerce')
    
    tab1, tab2 =st.tabs(["Database", "Verification"])
       

# ---------- DATABASE WITH ALL INFORMATIONS -----------------
    with tab1:

        sel1, sel2 = st.columns(2)
        with sel1:
            selected_day = st.date_input("Day started", value=None, min_value="2025-09-01")

        if selected_day:
            data = data[data['Day'] >= pd.to_datetime(selected_day)]

        
        for col in ["Datasheet", "Function", "EMC"]:
            if col in data.columns:
                data[col] = data[col].astype(bool)
        styled_data = data.style.apply(highlight_step(data["Step"]), axis=1)

        edited_data = st.data_editor(
                data, 
                num_rows="dynamic", 
                styler=styled_data,
                column_config={
                    "Datasheet": st.column_config.CheckboxColumn(default=None),
                    "Function": st.column_config.CheckboxColumn(default=None),
                    "EMC": st.column_config.CheckboxColumn(default=None)
                })


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
            # Button to generate the report
            if st.button(' 📥 High volume reports'):
                # Apply the custom filter based on "REPORTS" status
                filtered_df = data[
                    ~data['REPORTS'].str.strip().str.upper().isin(['OK', 'NA'])
                ]

                # Iterate over each row in the filtered DataFrame
                for index, row in filtered_df.iterrows():
                    test_value = row['Test Choice']
                    dut_name = row['DUT SN']

                    if test_value and dut_name:
                        # Load template automatically based on the "TEST" column value
                        template_path = load_template(test_value)

                        if template_path:
                            # Generate different reports based on "REPORTS" status and "TEST" column
                            current_dir = os.path.dirname(os.path.abspath(__file__))
                            # Construct the full path to the template directory
                            report_dir = os.path.join(current_dir, "REPORTS")
                            file_path_pdf = os.path.join(report_dir, f"Report_DCDC_{dut_name}_{test_value}.docx").strip()

                            generate_report(filtered_df[filtered_df.index == index], template_path, file_path_pdf, test_engineer)
            else:
                pass
        with but4:
            if st.button('💼 Single report'):
                pass
        
project_tracker()






