import streamlit as st
import pandas as pd
from docx import Document
import os
from datetime import datetime
import re, shutil
from libraries import *
import plotly
import plotly.figure_factory as ff
import json
import sqlite3
import sqlalchemy, sqlite3
from sqlalchemy import create_engine
from io import BytesIO



st.set_page_config(
      page_title="PROJECT MANAGEMENT",
      page_icon=":airplane",
      layout="wide"
      )



# Load database
database()
   

def project_tracker():
    # Streamlit file uploader
    uploaded_file = st.file_uploader("Choose an Excel file", type="xlsx")

    ################################
    # PROCESS DATABASE
    ################################
    if uploaded_file is not None:
        fill_database(uploaded_file)
        st.success("Database has been populated successfully.")
    query = "SELECT * FROM ProjectTracker"
    data = get_data_from_db(query)
    data = pd.DataFrame(data)
    
    # Convert the 'Date' columns to datetime
    date_columns = ['START DATE', 'END DATE']
    for col in date_columns:
        data[col] = pd.to_datetime(data[col], errors='coerce')
    
    tab1, tab2= st.tabs(["DATA VIEW", "DAILY & UNIT HISTORY"])

    with tab1:
        ##########
        # FILTERS
        ##########
        st.header('UNIT DATABASE TABLE')

        # Convert date columns to datetime
        data['START DATE'] = pd.to_datetime(data['START DATE'], errors='coerce')
        data['END DATE'] = pd.to_datetime(data['END DATE'], errors='coerce')

        

        sel1, sel2, sel3, sel4, sel5, sel6 = st.columns(6)
        with sel1:
            test_engineer = st.text_input("TEST ENGINEER")
        with sel2:
            selected_version = st.multiselect('Select project id to display', data['PROJECT ID'].unique())
        with sel4:
            start_month = st.date_input("START DATE")
        with sel5:
            end_month = st.date_input("END DATE")
        with sel6:
            select_end=st.radio("END N/A", ("YES", "NO"))
        
        if selected_version:
            data = data[data['VERSION'].isin(selected_version)]
        else:
            data=data
        if start_month:
            data = data[data['START DATE'] >= pd.to_datetime(start_month)]
        else:
            data=data
        if end_month:
            if select_end == "NO":
                data = data[data['END DATE'] <= pd.to_datetime(end_month)]
            else:
                pass
        else:
            data=data

        
        #####################
        # EDITABLE DATAFRAME
        #####################
        edited_data = st.data_editor(data, num_rows="dynamic", use_container_width=True)
        

        but1, but2, but3, but4= st.columns(4)
        with but1:
            if st.button('Save Changes'):
                engine = create_engine('sqlite:///project_tracker.db')
                edited_data.to_sql('ProjectTracker', engine, if_exists='replace', index=False)
                st.success("Changes saved successfully.")
        data = edited_data

        #########################
        # DOWNLOAD TO EXCEL
        #########################
        # Sort the data by 'DUT SN'
        sorted_data = data.sort_values(by='PROJECT ID')
        today = datetime.today().strftime("%d%m%Y")
        
        
        # Create an Excel file with subsheets for each DUT SN
        output = BytesIO()
        
        with pd.ExcelWriter(output) as writer:
            workbook = writer.book
            
            for project in sorted_data['PROJECT ID'].unique():
                dut_data = sorted_data[sorted_data['PROJECT ID'] == project]
                dut_data = dut_data.sort_values(by='START DATE')
                previous_sn = None
                startrow = 0
                for index, row in dut_data.iterrows():
                    if previous_sn and row['PROJECT ID'] != previous_sn:
                        # Add two empty rows
                        empty_df = pd.DataFrame([[''] * len(dut_data.columns)] * 2, columns=dut_data.columns)
                        empty_df.to_excel(writer, sheet_name=dut_version, index=False, header=False, startrow=startrow)
                        
                    # Write the row data
                    row_df = pd.DataFrame([row])
                    row_df.to_excel(writer, sheet_name=project, index=False, header=(startrow == 0), startrow=startrow)
                    startrow += 1
                    previous_sn = row['PROJECT ID']

            # Ensure at least one sheet is visible before saving
            if not any(sheet.sheet_state == 'visible' for sheet in workbook.worksheets):
                workbook.active.sheet_state = 'visible'

            # Explicitly close the writer
            writer.close()
       
        

        with but2:
            # Add a button to download the Excel file with subsheets
            st.download_button(
                label="Download Daily .xlsx",
                data=output,
                file_name=f'Project_tracker.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        # Second file
        with but3:
            backup = BytesIO()

            with pd.ExcelWriter(backup) as new_database_backup:
                workbook = new_database_backup.book
                edited_data.to_excel(new_database_backup, index=False, header=True)

            # Streamlit download button
            st.download_button(
                label="Download Backup",
                data=backup.getvalue(),
                file_name=f'Backup_DATABSE_{today}.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
                        
        with but4:
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
        
        unit_data=data[['PROJECT ID', 'INFO', 'START DATE', 'END DATE', 'REPORTS']]
        
        if unit_data['PROJECT ID'].empty:
                st.warning("Please select a unit to displat UNIT CHART & HISTORY")
        else:
                gantt_chart_json = create_dut_chart(unit_data, 'Unit Chart')
                if gantt_chart_json:
                    st.plotly_chart(json.loads(gantt_chart_json))
    with tab2:
        st.header("CURRENT DAILY")
        current_data=data[data['END DATE'].isna()]
        current_data = current_data[['PROJECT ID',  'INFO','START DATE', 'END DATE', 'REPORTS']]
        st.dataframe(current_data, use_container_width=True)

        
        
        


project_tracker()






