
import re, shutil, sqlite3, os
from datetime import datetime
from sqlalchemy import create_engine
import pandas as pd


################# DATABASE SECTION ##############

def database():
    conn = sqlite3.connect('project_tracker.db')
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ProjectTracker (
        Request TEXT PRIMARY KEY,
        Reference INTEGER,
        Step TEXT,
        Homologation TEXT,
        Reason TEXT,
        Current TEXT,
        Used TEXT,
        Position TEXT,
        Day DATE,
        New TEXT,
        Datasheet BOOLEAN,
        Function BOOLEAN,
        EMC BOOLEAN,
        Note TEXT
    )
    """)
    conn.commit()
    conn.close()

def fill_database(file):
    excel = pd.read_excel(file)
    engine = create_engine('sqlite:///project_tracker.db')
    excel.to_sql('ProjectTracker', con=engine, if_exists='replace', index=False)

def get_data_from_db(query):
    conn = sqlite3.connect('project_tracker.db')
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def update_data(request_id, reference, step, reason, current, used, position, day, new, datasheet, function, emc):
    conn = sqlite3.connect('project_tracker.db')
    cursor = conn.cursor()
    cursor.execute('''
    UPDATE ProjectTracker
    SET Reference = ?, Step = ?, Reason = ?, Current = ?, Used = ?, Position = ?, Day = ?, New = ?, Datasheet = ?, Function = ?, EMC = ?
    WHERE Request = ?
    ''', (reference, step, reason, current, used, position, day, new, datasheet, function, emc, request_id))
    conn.commit()
    conn.close()
