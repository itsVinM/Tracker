import streamlit as st
import pandas as pd
from docx import Document
import os
from datetime import datetime
import re, shutil
import plotly
import plotly.figure_factory as ff
import json
import sqlite3
import sqlalchemy, sqlite3
from sqlalchemy import create_engine
from io import BytesIO
from libraries import *


st.set_page_config(
      page_title="PRODUCT ENGINEERING - VALIDATION",
      page_icon=":electronics",
      layout="wide", 
      
      )

user = st.user

# Load database
database()
   

def project_tracker():

    uploaded_file = st.file_uploader("Choose an Excel file", type="xlsx")
    but1, but2, but3, but4 = st.columns(4)
    if uploaded_file:
        fill_database(uploaded_file)
        st.success("Database has been populated successfully.")

    query = "SELECT * FROM ProjectTracker" # WHERE user_email= '{user.email}"
    data = get_data_from_db(query)
    data['Day'] = pd.to_datetime(data['Day'], errors='coerce')

    tab1, tab2 =st.tabs(["Validation","Database"])
    with tab1:
        pass

    with tab2:

        sel1, sel2 = st.columns(2)
        with sel1:
            selected_day = st.date_input("Filter by 'Day'", value="2025-09-01")

        if selected_day:
            data = data[data['Day'] >= pd.to_datetime(selected_day)]

        edited_data = st.data_editor(
                data, 
                num_rows="dynamic", 
                use_container_width=True,
                column_config={
                    "Datasheet": st.column_config.CheckboxColumn(),
                    "Function": st.column_config.CheckboxColumn(),
                    "EMC": st.column_config.CheckboxColumn()
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
            if st.button('Generate Report'):
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
        
project_tracker()






