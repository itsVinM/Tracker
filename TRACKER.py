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
      page_title="DCDC UNIT MANAGEMENT",
      page_icon=":battery",
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
    date_columns = ['Test Start Date', 'Test End Date', 'Planned Start Date', 'Planned End Date']
    for col in date_columns:
        data[col] = pd.to_datetime(data[col], errors='coerce')
    
    tab1, tab2, tab3= st.tabs(["DATA VIEW", "DAILY & UNIT HISTORY", "FOLDER & PHOTOS"])

    with tab1:
        ##########
        # FILTERS
        ##########
        st.header('UNIT DATABASE TABLE')

        # Convert date columns to datetime
        data['Test Start Date'] = pd.to_datetime(data['Test Start Date'], errors='coerce')
        data['Test End Date'] = pd.to_datetime(data['Test End Date'], errors='coerce')

        

        sel1, sel2, sel3, sel4, sel5, sel6 = st.columns(6)
        with sel1:
            test_engineer = st.text_input("TEST ENGINEER")
        with sel2:
            selected_version = st.multiselect('Select DUT Version to Display', data['Version'].unique())
        with sel3:
            selected_leg = st.multiselect('Select DUT LEG to Display', data['DUT LEG'].unique())
        with sel4:
            start_month = st.date_input("Test Start Date")
        with sel5:
            end_month = st.date_input("Test End Date")
        with sel6:
            select_end=st.radio("END N/A", ("YES", "NO"))
        
        if selected_version:
            data = data[data['Version'].isin(selected_version)]
        else:
            data=data
        if selected_leg:
            data = data[data['DUT LEG'].isin(selected_leg)]
        else:
            data=data
        if start_month:
            data = data[data['Test Start Date'] >= pd.to_datetime(start_month)]
        else:
            data=data
        if end_month:
            if select_end == "NO":
                data = data[data['Test End Date'] <= pd.to_datetime(end_month)]
            else:
                pass
        else:
            data=data

        
        #####################
        # EDITABLE DATAFRAME
        #####################
        edited_data = st.data_editor(data, num_rows="dynamic")
        

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
        sorted_data = data.sort_values(by='DUT SN')
        today = datetime.today().strftime("%d%m%Y")
        columns_to_exclude = ['VMD Order', 'Orderer', 'Planned Start Date', 'Planned End Date', 'Photo', 'MF4']
        # Drop the columns
        sorted_data = sorted_data.drop(columns=columns_to_exclude)

        # Create an Excel file with subsheets for each DUT SN
        output = BytesIO()
        
        with pd.ExcelWriter(output) as writer:
            workbook = writer.book
            for dut_version in sorted_data['Version'].unique():
                dut_data = sorted_data[sorted_data['Version'] == dut_version]
                # Sort the data by 'Test Start Date' within each version
                dut_data = dut_data.sort_values(by='Test Start Date')
                previous_sn = None
                startrow = 0
                for index, row in dut_data.iterrows():
                    if previous_sn and row['DUT SN'] != previous_sn:
                        # Add two empty rows
                        empty_df = pd.DataFrame([[''] * len(dut_data.columns)] * 2, columns=dut_data.columns)
                        empty_df.to_excel(writer, sheet_name=dut_version, index=False, header=False, startrow=startrow)
                        
                    # Write the row data
                    row_df = pd.DataFrame([row])
                    row_df.to_excel(writer, sheet_name=dut_version, index=False, header=(startrow == 0), startrow=startrow)
                    startrow += 1
                    previous_sn = row['DUT SN']

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
                file_name=f'DCDC_Project_tracker.xlsx',
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
                file_name=f'Backup_DCDC_DATABSE_{today}.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
                        
        with but4:
            # Button to generate the report
            if st.button('Generate Report'):
                # Apply the custom filter based on "REPORTS" status
                filtered_df = data[
                    ~data['REPORTS'].str.strip().str.upper().isin(['OK', 'NA', 'INCIDENT REPORT', 'COMMISSIONING'])
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
        
        gantt_chart_json = create_leg_chart(data, 'Project Gantt Chart')
        if gantt_chart_json:
            st.plotly_chart(json.loads(gantt_chart_json))
        
    with tab2:
        st.header("CURRENT DAILY")
        current_data=data[data['Test End Date'].isna()]
        current_data = current_data[['DUT SN', 'Version', 'DUT LEG', 'Test bench', 'Test Choice', 'Test Start Date', 'Comment']]
        st.dataframe(current_data, use_container_width=True)

        st.header("UNIT HISTORY")
        unit_col1, unit_col2=st.columns(2)
        
        unit_data=data[['DUT SN', 'Version', 'DUT LEG', 'Test bench', 'Test Choice', 'Test Start Date', 'Test End Date', 'Comment']]
        with unit_col1:
            unit_history = st.multiselect('Select DUT LEG to Display', data['DUT SN'].unique())
            unit_data = unit_data[unit_data['DUT SN'].isin(unit_history)]
            st.dataframe(unit_data, use_container_width=True)
        with unit_col2:
            if unit_data['DUT SN'].empty:
                st.warning("Please select a unit to displat UNIT CHART & HISTORY")
            else:
                gantt_chart_json = create_dut_chart(unit_data, 'Unit Chart')
                if gantt_chart_json:
                    st.plotly_chart(json.loads(gantt_chart_json))
    with tab3:
         change_name(data)


            


def change_name(data):
    st.title("FOLDER OR PHOTO HANDLER")
    
    col1, col2, col3, col4=st.columns(4)
    with col1:
        selected_dut = st.multiselect('Select DUT to Display', data['DUT SN'])
        if selected_dut:
            label = data[data['DUT SN'].isin(selected_dut)]
    with col2:
        p_ea=st.radio("Was the test P-EA?", ("Yes", "No"))
    with col3:
        mount=st.radio("Mounting?", ("Yes", "No"))
    with col4:
        image=st.radio("Images?", ("Yes", "No"))
    if st.button('EDIT FHOTO & GENERATE FOLDERS'):
        current_dir = os.path.dirname(os.path.abspath(__file__))
         # Construct the full path to the template directory
        
        directory = os.path.join(current_dir, "IMAGES")

        files=os.listdir(directory)
        image_files = [f for f in files]
        test_folder=os.path.join(current_dir, "TEST_FOLDER")    
        ##################################
        #GENERATE ALL FOLDERS FOR THE TEST
        ##################################
        if image == "Yes":
            

            if mount == "Yes":
                os.makedirs(os.path.join(directory, "01_Commissioning"))
                os.makedirs(os.path.join(directory, "02_XML_Header"))
                os.makedirs(os.path.join(directory, "03_Protocol"))
                os.makedirs(os.path.join(directory, "04_Stops"))
                os.makedirs(os.path.join(directory, "05_Pictures"))
                os.makedirs(os.path.join(directory, "06_Test_Data"))
                os.makedirs(os.path.join(directory, "07_CheckList"))
                os.makedirs(os.path.join(directory, "08_Test_Information"))
                os.makedirs(os.path.join(directory, "09_Test_Program"))

            photos=os.path.join(directory, "05_Pictures")
            if p_ea == "Yes":
                    os.makedirs(os.path.join(photos, "01_Mech_Check"))
                    os.makedirs(os.path.join(photos, "02_Elec_Strength"))
                    os.makedirs(os.path.join(photos, "03_Equipot_Bond"))
                    os.makedirs(os.path.join(photos, "04_Electrical_Tests"))
            else:
                    os.makedirs(os.path.join(photos, "01_Assembly"))
                    os.makedirs(os.path.join(photos, "02_Disassembly"))

            ###################################################
            #CHANGE PHOTO NAME AND PUT IT IN THE CORRECT FOLDER
            ###################################################   
            for index, filename in enumerate(image_files):
                # Get the file extension
                file_extension = os.path.splitext(filename)[1]
                
                # Create the new name
                new_name = f"{label}_{index + 1}{file_extension}"
                
                # Get the full path for the old and new names
                old_path = os.path.join(directory, filename)
                new_path = os.path.join(photos, new_name)
                
                # Rename the file
                #os.rename(old_path, new_path)
                shutil.move(old_path, new_path)   
        else:
            pass
        
        folders = [f for f in os.listdir(directory) if os.path.isdir(os.path.join(directory, f))]
        test_folder_specific=os.path.join(test_folder, f"{label}")
        os.makedirs(test_folder_specific, exist_ok=True)
        # Move each folder to the destination directory
        for folder in folders:
                shutil.move(os.path.join(directory, folder), os.path.join(test_folder_specific, folder))
       
        

def upload_folder():
    J_drive=os.path.basename("\\IDIADA\ES\HQ\KP02H_Powertrain\TREBALLS\BMW\LME2210047 Penthouse\05. Testing\2_KULnew")
    source_report=os.path.join(os.path.dirname(os.path.abspath(__file__)), "REPORTS")
    source_images=os.path.join(os.path.dirname(os.path.abspath(__file__)), "TEST_FOLDER")
    if not os.path.exists(J_drive):
        # If the folder doesn't exist, copy the entire folder
            shutil.copytree(source_images, J_drive)
    else:
            # Merge fodler if it exists
            for item in os.listdir(source_images):
                source_item = os.path.join(source_images, item)
                destination_item = os.path.join(J_drive, item)
                
                if os.path.isdir(source_item):
                    # Recursively merge folders
                    if not os.path.exists(destination_item):
                        shutil.copytree(source_item, destination_item)
                    else:
                        upload_folder(source_item, J_drive)
                else:
                    # Copy files
                    shutil.copy2(source_item, destination_item)

project_tracker()






