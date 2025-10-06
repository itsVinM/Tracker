import sqlite3
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime
import streamlit as st
from typing import Dict

DB_NAME = 'validation_tracker.db'

def database():
    """Ensures the SQLite DB and table exist."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ValidationTracker (
            Product_ID TEXT PRIMARY KEY,
            Request TEXT,    
            Homologated TEXT,
            Datasheet BOOLEAN,
            Function BOOLEAN,
            EMC BOOLEAN,
            Note TEXT,
            Current TEXT,
            Position TEXT,
            New TEXT
        )
    """)
    conn.commit()
    conn.close()

def get_data_from_db(query):
    """Fetches data from DB."""
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def update_data(df: pd.DataFrame):
    """Updates the entire DB table with a DataFrame."""
    conn = sqlite3.connect(DB_NAME)
    cols_to_drop = ['Overall_Status', 'Details_Trigger']
    df_save = df.drop(columns=[c for c in cols_to_drop if c in df.columns], errors='ignore')
    # Use replace here to handle potential changes to ID (the primary key)
    df_save.to_sql('ValidationTracker', conn, if_exists='replace', index=False) 
    conn.close()

def fill_database_from_file(uploaded_file):
    """Fills DB from an uploaded Excel file, overwriting existing data."""
    try:
        df = pd.read_excel(uploaded_file)
        if 'ID' not in df.columns or df['ID'].isnull().any():
            st.warning("Generating new IDs for the uploaded data.")
            df['ID'] = [str(int(datetime.now().timestamp() * 1000000) + i) for i in range(len(df))]
        
        update_data(df)
        st.success("Database has been populated successfully.")
    except Exception as e:
        st.error(f"Error filling database: {e}")