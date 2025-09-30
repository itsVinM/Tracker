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

import re, shutil, json, sqlite3, plotly, os

import streamlit as st
import pandas as pd
from docx import Document
from datetime import datetime
import plotly.figure_factory as ff
from sqlalchemy import create_engine
from io import BytesIO
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

from libraries import *
from database import *

st.set_page_config(
      page_title="PRODUCT ENGINEERING - VALIDATION",
      page_icon=":battery",
      layout="wide", 
      
      )

user = st.user

# Load database
database()
   
def project_tracker():
    # --- Layout definition -- 
    with st.sidebar:
        st.markdown("""
                    ✈️ Project tracker developed for Validation by Vincentiu
                     """)

        uploaded_file = st.file_uploader("Choose an Excel file", type="xlsx")
    but1, but2, but3, but4 = st.columns(4, gap="small")

    if uploaded_file:
        fill_database(uploaded_file)
        st.success("Database has been populated successfully.")

    query = "SELECT * FROM ProjectTracker"
    data = get_data_from_db(query)
    data['Day'] = pd.to_datetime(data['Day'], errors='coerce')

     
    row_style = JsCode("""
    function(params) {
        if (params.data.Step === 'Failed') {
            return { 'backgroundColor': '#b71c1c', 'color': 'white' };  // dark red
        } else if (params.data.Step === 'Validation') {
            return { 'backgroundColor': '#f57f17', 'color': 'black' };  // dark amber
        } else if (params.data.Step === 'Passed') {
            return { 'backgroundColor': '#1b5e20', 'color': 'white' };  // dark green
        } else {
            return {};
        }
    }
    """)


    # ---------- DATABASE WITH ALL INFORMATIONS -----------------
 
    sel1, sel2 = st.columns(2)
    with sel1:
            selected_day = st.date_input("Day started", value=None, min_value=datetime(2025, 9, 1))

    if selected_day:
            data = data[data['Day'] >= pd.to_datetime(selected_day)]

        # Ensure checkbox columns are boolean
    for col in ["Datasheet", "Function", "EMC"]:
            if col in data.columns:
                data[col] = data[col].astype(bool)
    
    # --- AgGrid Setup ---
    gb = GridOptionsBuilder.from_dataframe(data)
    gb.configure_default_column(editable=True)
    gb.configure_grid_options(getRowStyle=row_style)

    # Configure checkbox columns
    for col in ["Datasheet", "Function", "EMC"]:
            gb.configure_column(col, cellEditor='agCheckboxCellEditor', editable=True)

    grid_options = gb.build()
    
    # Create a pinned top row with empty values
    pinned_row = {col: "" for col in data.columns}

    if "Datasheet" in pinned_row:
        pinned_row["Datasheet"] = False
    if "Function" in pinned_row:
        pinned_row["Function"] = False
    if "EMC" in pinned_row:
        pinned_row["EMC"] = False

    # Add pinned row to grid options
    grid_options['pinnedTopRowData'] = [pinned_row]

    grid_response = AgGrid(
            data,
            gridOptions=grid_options,
            update_mode=GridUpdateMode.VALUE_CHANGED,
            fit_columns_on_grid_load=True,
            allow_unsafe_jscode=True
        )

    edited_data = pd.DataFrame(grid_response["data"])

    with but1:
            if st.button("💾 Save Changes"):
                
                # Extract the pinned row (first row)
                edited_data = pd.DataFrame(grid_response["data"])
                new_row = edited_data.iloc[0]

                # Check if the pinned row has meaningful data
                if any(str(val).strip() for val in new_row.values):
                    # Append the new row to the rest of the data (excluding pinned row)
                    updated_data = pd.concat([data, pd.DataFrame([new_row])], ignore_index=True)
                else:
                    updated_data = data.copy()

                # Save to database
                engine = create_engine('sqlite:///project_tracker.db')
                updated_data.to_sql('ProjectTracker', con=engine, if_exists='replace', index=False)

                st.success("Changes saved successfully.")

                # Reset pinned row
                pinned_row = {col: "" for col in data.columns}
                if "Day" in pinned_row:
                    pinned_row["Day"] = datetime.today().strftime("%Y-%m-%d")
                for col in ["Datasheet", "Function", "EMC"]:
                    if col in pinned_row:
                        pinned_row[col] = False

                # Update grid options with new empty pinned row
                grid_options['pinnedTopRowData'] = [pinned_row]


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

                            generate_report(filtered_df[filtered_df.index == index], template_path, file_path_pdf, test_engineer)

    with but4:
            if st.button('💼 Single report'):
                pass

    


project_tracker()
