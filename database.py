import sqlite3
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine

DB_NAME = 'project_tracker.db'

def initialize_database(db_path: str = DB_NAME) -> None:
    """Create relational tables for OrderList, ProductsList, and HomologationStatus."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS OrderList (
                reference_id TEXT PRIMARY KEY,
                request_code TEXT UNIQUE,
                created_at DATE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ProductsList (
                product_id TEXT PRIMARY KEY,
                reference_id TEXT,
                FOREIGN KEY (reference_id) REFERENCES OrderList(reference_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS HomologationStatus (
                product_id TEXT PRIMARY KEY,
                homologated TEXT,
                datasheet BOOLEAN,
                function_test BOOLEAN,
                emc_test BOOLEAN,
                note TEXT,
                current TEXT,
                used TEXT,
                position TEXT,
                new TEXT,
                last_updated DATE,
                FOREIGN KEY (product_id) REFERENCES ProductsList(product_id)
            )
        """)

        conn.commit()

def fill_database_from_excel(file_path: str, db_path: str = DB_NAME) -> None:
    try:
        df = pd.read_excel(file_path)

        df['reference_id'] = df['Request'].apply(lambda x: f"REF_{x}")
        df['product_id'] = df['Request'].apply(lambda x: f"PROD_{x}")

        order_df = df[['reference_id', 'Request']].copy()
        order_df.rename(columns={'Request': 'request_code'}, inplace=True)
        order_df['created_at'] = datetime.today().strftime('%Y-%m-%d')

        products_df = df[['product_id', 'reference_id']].copy()

        homologation_df = df[['product_id', 'Homologated', 'Datasheet', 'Function', 'EMC', 'Note', 'Current', 'Used', 'Position', 'New']].copy()
        homologation_df.rename(columns={
            'Function': 'function_test',
            'EMC': 'emc_test',
            'Datasheet': 'datasheet'
        }, inplace=True)
        homologation_df['last_updated'] = datetime.today().strftime('%Y-%m-%d')

        engine = create_engine(f'sqlite:///{db_path}')
        order_df.to_sql('OrderList', con=engine, if_exists='replace', index=False)
        products_df.to_sql('ProductsList', con=engine, if_exists='replace', index=False)
        homologation_df.to_sql('HomologationStatus', con=engine, if_exists='replace', index=False)

    except Exception as e:
        print(f"Error loading Excel file: {e}")

def get_data_from_db(query: str, db_path: str = DB_NAME) -> pd.DataFrame:
    with sqlite3.connect(db_path) as conn:
        return pd.read_sql_query(query, conn)

def update_homologation_status(
    product_id: str,
    homologated: str,
    datasheet: bool,
    function_test: bool,
    emc_test: bool,
    note: str,
    current: str,
    used: str,
    position: str,
    new: str,
    db_path: str = DB_NAME
) -> None:
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE HomologationStatus
            SET homologated = ?, datasheet = ?, function_test = ?, emc_test = ?, note = ?, 
                current = ?, used = ?, position = ?, new = ?, last_updated = ?
            WHERE product_id = ?
        """, (
            homologated, datasheet, function_test, emc_test, note,
            current, used, position, new,
            datetime.today().strftime('%Y-%m-%d'), product_id
        ))
        conn.commit()
