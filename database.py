import sqlite3
import pandas as pd
from sqlalchemy import create_engine
import os

# Ensure the folder exists
os.makedirs('database', exist_ok=True)

DB_NAME = 'database/project_tracker.sql'

def initialize_database(db_path: str = DB_NAME) -> None:
    """Create a unified ProductTracker table."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ProductTracker (
                product_id TEXT PRIMARY KEY,
                reference_id TEXT,
                current TEXT,
                new TEXT,
                homologated TEXT,
                datasheet BOOLEAN,
                function_test BOOLEAN,
                emc_test BOOLEAN,
                note TEXT,
                position TEXT
            )
        """)

        conn.commit()

def fill_database_from_excel(file_path: str, db_path: str = DB_NAME) -> None:
    try:
        df = pd.read_excel(file_path, engine='openpyxl')

        if 'product' in df.columns:
            df.rename(columns={'product': 'product_id'}, inplace=True)

        tracker_df = df[[
            'product_id', 'reference_id', 'Current', 'New',
            'Homologated', 'Datasheet', 'Function', 'EMC', 'Note', 'Position'
        ]].copy()

        tracker_df.rename(columns={
            'Current': 'current',
            'New': 'new',
            'Function': 'function_test',
            'EMC': 'emc_test',
            'Datasheet': 'datasheet'
        }, inplace=True)

        engine = create_engine(f'sqlite:///{db_path}')
        tracker_df.to_sql('ProductTracker', con=engine, if_exists='replace', index=False)

    except Exception as e:
        print(f"❌ Error loading Excel file: {e}")

def update_product_tracker(
    product_id: str,
    reference_id: str,
    current: str,
    new: str,
    position: str,
    homologated: str,
    datasheet: bool,
    function_test: bool,
    emc_test: bool,
    note: str,
    db_path: str = DB_NAME
) -> None:
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE ProductTracker
            SET reference_id = ?, current = ?, new = ?, homologated = ?, datasheet = ?, 
                function_test = ?, emc_test = ?, note = ?, position = ?
            WHERE product_id = ?
        """, (
            reference_id, current, new, homologated, datasheet,
            function_test, emc_test, note, position, product_id
        ))

        conn.commit()

def get_data_from_db(query: str, db_path: str = DB_NAME) -> pd.DataFrame:
    with sqlite3.connect(db_path) as conn:
        return pd.read_sql_query(query, conn)