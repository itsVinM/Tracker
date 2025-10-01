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

from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, GridUpdateCode

st.set_page_config(
      page_title="PRODUCT ENGINEERING - VALIDATION",
      layout="wide", 
      
      )

user = st.user

# Load database
database()

def project_tracker():
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

    for col in ["Datasheet", "Function", "EMC"]:
        if col in data.columns:
            data[col] = data[col].astype(bool)

    
    # Normalize Homologation column
    data['Homologation'] = data['Homologation'].fillna("").astype(str)

    # Prepare Request column for expansion (simulate nested grid)
    def format_request(row):
        request_items = str(row.get("Request", "")).split(";")  # assuming semicolon-separated
        return [{"Item": item.strip()} for item in request_items if item.strip()]

    data['RequestDetails'] = data.apply(lambda row: format_request(row), axis=1)

    # --- AGGRID CONFIGURATION ---
    gb = GridOptionsBuilder.from_dataframe(data)
    gb.configure_default_column(editable=True, groupable=True)

    # Conditional row styling based on Homologation status
    
    cell_style_jscode = JsCode("""
    function(params) {
        let status = params.data.Homologation;
        if (typeof status === 'string') {
            status = status.toLowerCase();
            if (status.includes("validation")) {
                return { 'backgroundColor': '#fff3cd' };  // Yellow
            } else if (status.includes("passed")) {
                return { 'backgroundColor': '#d4edda' };  // Green
            } else if (status.includes("failed")) {
                return { 'backgroundColor': '#f8d7da' };  // Red
            }
        }
        return {};
    }

    """)

    gb.configure_grid_options(getRowStyle=cell_style_jscode)
    grid_options = gb.build()

    grid_response = AgGrid(
        data,
        gridOptions=grid_options,
        enable_enterprise_modules=False,
        allow_unsafe_jscode=True,
        editable=True,
        height=600,
        fit_columns_on_grid_load=True
    )

    edited_data = grid_response['data']


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

                            generate_report(filtered_df[filtered_df.index == index], template_path, file_path_pdf)
            else:
                pass
    with but4:
            if st.button('💼 Single report'):
                pass
        
project_tracker()






