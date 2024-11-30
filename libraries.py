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
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ProjectTracker (
        Id INTEGER PRIMARY KEY,
        INFO TEXT,
        PROJECT_ID TEXT KEY,
        start_date DATE,
        end_date DATE,
        REPORTS TEXT
    	)
    """)

    # Commit changes and close the connection
    conn.commit()
    conn.close()

def fill_database(file):
    # Read the Excel file into a DataFrame
    excel = pd.read_excel(file)

    # Define the mapping from Excel columns to database columns
    column_mapping = {
   
        'PROJECT ID': 'PROJECT_ID',
        'START DATE': 'start_date',
        'END DATE': 'end_date',
             
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
    df.columns = ["ID ","PROJECT ID", "INFO", "START DATE", "END DATE", "REPORTS"]
    conn.close()
    return df

# Function to add a new row
def add_row():
    new_row = {'test_choice': 'New Option'}
    st.session_state.data = st.session_state.data.append(new_row, ignore_index=True)


def update_data(id,  test_choice, test_start_date, test_end_date, DUT_SN, DUT_LEG):
    conn = sqlite3.connect('sqlite:///project_tracker.db')
    cursor = conn.cursor()
    cursor.execute('''
    UPDATE ProjectTracker
    SET PROJECT_ID = ?, INFO=?,   start_date = ?, end_date = ?, REPORTS=?
    WHERE id = ?
    ''', (version, test_choice, test_start_date, test_end_date, DUT_SN, DUT_LEG, id))
    conn.commit()
    conn.close()


def create_dut_chart(data, title):
    # Create a new DataFrame with the required column names for the Gantt chart
    gantt_data = data.rename(columns={
        'START DATE': 'Start',
        'END DATE': 'Finish',
        'PROJECT ID': 'PROJECT ID',
    })
    

    gantt_data['Task'] = data['PROJECT ID'] 

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
        
        report_no = f"{row['PROJECT ID']}_{today}_v0"
        
        # Format the period without time using pd.Timestamp
        row["Test Start Date"] = pd.Timestamp(row["START DATE"]).strftime("%d/%m/%Y")
        row["Test End Date"] = pd.Timestamp(row["END DATE"]).strftime("%d/%m/%Y")
        
        period = f"{row['START DATE']} - {row['END DATE']}"
        if test_engineer:
            parts = test_engineer.lower().split(" ")
            
            email = parts[0] + "." + parts[1] + "@gmail.com"
            context = {
   
                "{PROJECT ID}": row["PROJECT ID"],
                "{REPORT_NO}": report_no,
                "{PERIOD}": period,
                "{MAIL}": email,

            }
            file_name = report_no
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
