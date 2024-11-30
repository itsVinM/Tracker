import streamlit as st
import pandas as pd
from docx import Document
import os
from datetime import datetime
import re, shutil
import plotly
import plotly.figure_factory as ff
import plotly.graph_objects as go
import json
import sqlite3
from sqlalchemy import create_engine
import matplotlib.pyplot as plt

def database():
    # Connect database or create one
    conn=sqlite3.connect('project_tracker.db')

    #create cursor object
    cursor=conn.cursor()
    # Create a table (if it doesn't exist)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ProjectTracker (
        Id INTEGER PRIMARY KEY,
        Version TEXT,
        DUT_LEG TEXT,
        DUT_SN TEXT KEY,
        Vmd_order INTEGER,
        Oderer TEXT,
        Planned_start_date DATE,
        Planned_end_date DATE,
        Test_bench TEXT,
        Test_choice TEXT,
        Test_start_date DATE,
        Test_end_date DATE,
        Comment TEXT,
        REPORTS TEXT,
        Photo TEXT,
        MF4 TEXT,
        PANAMA_MF4	TEXT,
        PANAMA_PHOTO TEXT, 
        CHECKLIST       
    )
    ''')

    # Commit changes and close the connection
    conn.commit()
    conn.close()

def fill_database(file):
    # Read the Excel file into a DataFrame
    excel = pd.read_excel(file)

    # Define the mapping from Excel columns to database columns
    column_mapping = {
        'UNIT':'VERSION',
        'DUT': 'DUT_SN',
        'START DATE': 'Test_start_date',
        'END DATE': 'Test_end_date',
             
    }
    
    # Rename the columns in the DataFrame according to the mapping
    excel.rename(columns=column_mapping, inplace=True)
    
    # Create a SQLAlchemy engine
    engine = create_engine('sqlite:///project_tracker.db')

    # Write data to the ProjectTracker table
    excel.to_sql('ProjectTracker', con=engine, if_exists='replace', index=False)

def get_data_from_db(query):
    conn = sqlite3.connect('project_tracker.db')
    df = pd.read_sql_query(query, conn)
    # Rename columns
    df.columns = ["ID ","DUT SN", "Version", "DUT LEG", "Test bench","Test Choice", "Test Start Date", "Test End Date", "Comment", "REPORTS","Photo", "MF4","PANAMA MF4","PANAMA PHOTO","VMD Order", "Orderer", "Planned Start Date", "Planned End Date", ]
    conn.close()
    return df

# Function to add a new row
def add_row():
    new_row = {'test_choice': 'New Option'}
    st.session_state.data = st.session_state.data.append(new_row, ignore_index=True)


def update_data(id, version, test_choice, test_start_date, test_end_date, DUT_SN, DUT_LEG):
    conn = sqlite3.connect('sqlite:///project_tracker.db')
    cursor = conn.cursor()
    cursor.execute('''
    UPDATE ProjectTracker
    SET version = ?,  DUT_LEG = ?, DUT_SN = ?,  test_choice = ?, test_start_date = ?, test_end_date = ?,
    WHERE id = ?
    ''', (version, test_choice, test_start_date, test_end_date, DUT_SN, DUT_LEG, id))
    conn.commit()
    conn.close()


def create_leg_chart(data, title):
    # Create a new DataFrame with the required column names for the Gantt chart
    gantt_data = data.rename(columns={
        'Test Start Date': 'Start',
        'Test End Date': 'Finish',
        'Version':'Version'
    })
    
    gantt_data['Task'] = data['DUT LEG'] 
    
    if gantt_data.empty:
        st.warning("NO DATA")
    else:
        # Create Gantt chart
        try:
            fig = ff.create_gantt(gantt_data, index_col='Task', show_colorbar=True, group_tasks=True)
            fig.update_layout(title_text=title, xaxis_title='Timeline', autosize=True)
            return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
        except:
            st.warning("You forgot to input all the information")

def create_dut_chart(data, title):
    # Create a new DataFrame with the required column names for the Gantt chart
    gantt_data = data.rename(columns={
        'Test Start Date': 'Start',
        'Test End Date': 'Finish',
        'DUT SN': 'DUT SN',
        'DUT LEG': 'DUT LEG',
        'Version':'Version'
    })
    

    gantt_data['Task'] = data['DUT SN'] + '_' + data['Test Choice'] + '_' +data['DUT LEG']

    # Ensure all entries in the Task column are strings
    gantt_data['Task'] = gantt_data['Task'].astype(str)
    
    if gantt_data['Finish'].isnull().any():
        today = datetime.today()
        gantt_data['Finish'].fillna(today, inplace=True)

    # Generate colors based on the number of unique tasks
    unique_tasks = gantt_data['Task'].nunique()
    

    # Check if gantt_data is empty after filtering
    if gantt_data.empty:
        raise ValueError("No data available for the selected DUT SN.")
    
    cmap = plt.get_cmap('tab20')  # You can choose other colormaps like 'tab10', 'viridis', etc.
    colors = [cmap(i) for i in range(unique_tasks)]
    # Convert RGBA to hex
    colors = ['#%02x%02x%02x' % (int(r*255), int(g*255), int(b*255)) for r, g, b, _ in colors]

    fig = ff.create_gantt(gantt_data, index_col='Task', show_colorbar=True, group_tasks=True, colors=colors[:unique_tasks])
    fig.update_layout(title_text=title, xaxis_title='Timeline', autosize=True)
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

def create_directory():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    path=os.path.join(current_dir, "")
    """Creates a directory if it doesn't exist."""
    if not os.path.exists(path):
        os.makedirs(path)

def replace_placeholders(template_path, context, output_path):
    # Load the template document
    if not os.path.exists(template_path):
        print(f"Error: The file at {template_path} does not exist.")
        return None
    try:
        doc = Document(template_path)
    except Exception as e:
        print(f"Error loading template: {e}")
        return None
    
    # Iterate over each paragraph in the document
    for paragraph in doc.paragraphs:
        for placeholder, value in context.items():
            if placeholder in paragraph.text:
                paragraph.text = paragraph.text.replace(placeholder, value)
    
    # Iterate over each table in the document
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for placeholder, value in context.items():
                    if placeholder in cell.text:
                        cell.text = cell.text.replace(placeholder, str(value))
    
    # Save the modified document to the specified output path
    doc.save(output_path)
    
    return output_path

def generate_report(report_df, template_path, file_path, test_engineer):
    today = datetime.today()
    today_string = today.strftime("%d/%m/%Y")
    today=today.strftime("%d%m%Y")
    # Iterate over the DataFrame rows
    for index, row in report_df.iterrows():
        
        report_no = f"DCDC_{row['Version']}_{row['DUT LEG']}_{row['Test Choice']}_{row['DUT SN']}_{today}_v0"
        leg_match = re.search(r'\d+', row['DUT LEG'])
        leg_number = leg_match.group() if leg_match else ""
        
        # Format the period without time using pd.Timestamp
        row["Test Start Date"] = pd.Timestamp(row["Test Start Date"]).strftime("%d/%m/%Y")
        row["Test End Date"] = pd.Timestamp(row["Test End Date"]).strftime("%d/%m/%Y")
        
        period = f"{row['Test Start Date']} - {row['Test End Date']}"
        if test_engineer:
            parts = test_engineer.lower().split(" ")
            
            email = parts[0] + "." + parts[1] + "@idiada.com"
            context = {
                "{TEST}": row["Test Choice"],
                "{DUT}": row["DUT SN"],
                "{REPORT_NO}": report_no,
                "{UNIT}": row["Version"],
                "{LEG}": leg_number,
                "{PERIOD}": period,
                "{VERSION}": today_string,
                "{TEST_ENGINEER}":test_engineer,
                "{MAIL}": email,
                "{PANAMA_PHOTO}": row["PANAMA PHOTO"],
                "{PANAMA_MF4}" : row["PANAMA MF4"]
            }
            file_name = f"DCDC_{row['Version']}_{row['DUT LEG']}_{row['Test Choice']}_{row['DUT SN']}"
            # Generate a unique output file path
            output_file_path = os.path.join(os.path.dirname(file_path), f"{file_name}.pdf")
        

            # Replace placeholders in the template and save to the new file
            replace_placeholders(template_path, context,file_path)
        else:
            raise Exception("Who is the engineer?")
            

def load_template(test_value):
        # Get the absolute path of the current script
    current_dir = os.path.dirname(os.path.abspath(__file__))
    test_value = test_value.strip()
    
    # Construct the full path to the template directory
    template_dir = os.path.join(current_dir, "TEMPLATES")
    template_path = os.path.join(template_dir, f"{test_value}.docx")
    
    if os.path.exists(template_path):
        return template_path
    else:
        st.error(f"Template for {test_value} not found.")
        return None