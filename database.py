import sqlite3
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine
import os


# Ensure the folder exists
os.makedirs('database', exist_ok=True)

DB_NAME ='database/project_tracker.sql'


def initialize_database(db_path: str = DB_NAME) -> None:
    """Create tables: ProductOrders and HomologationStatus."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ProductOrders (
                product_id TEXT PRIMARY KEY,
                reference_id TEXT,
                current TEXT,
                new TEXT
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
                position TEXT,
                FOREIGN KEY(product_id) REFERENCES ProductOrders(product_id)
            )
        """)

        conn.commit()


def fill_database_from_excel(file_path: str, db_path: str = DB_NAME) -> None:
    try:
        df = pd.read_excel(file_path)

        # Rename 'product' to 'product_id' if needed
        if 'product' in df.columns:
            df.rename(columns={'product': 'product_id'}, inplace=True)

        product_orders_df = df[['product_id', 'reference_id', 'Current', 'New']].copy()
        product_orders_df.rename(columns={'Current': 'current', 'New': 'new'}, inplace=True)

        homologation_df = df[['product_id', 'Homologated', 'Datasheet', 'Function', 'EMC', 'Note', 'Position']].copy()
        homologation_df.rename(columns={
            'Function': 'function_test',
            'EMC': 'emc_test',
            'Datasheet': 'datasheet'
        }, inplace=True)

        engine = create_engine(f'sqlite:///{db_path}')
        product_orders_df.to_sql('ProductOrders', con=engine, if_exists='replace', index=False)
        homologation_df.to_sql('HomologationStatus', con=engine, if_exists='replace', index=False)

    except Exception as e:
        print(f"❌ Error loading Excel file: {e}")

def get_data_from_db(query: str, db_path: str = DB_NAME) -> pd.DataFrame:
    with sqlite3.connect(db_path) as conn:
        return pd.read_sql_query(query, conn)


def update_homologation_status(reference_id, product_id, homologated, datasheet, function_test, emc_test, note, current, position, new):
    # Example SQL update (adjust to your schema)
    query = """
        UPDATE HomologationStatus
        SET homologated = ?, datasheet = ?, function_test = ?, emc_test = ?, note = ?, current = ?, position = ?, new = ?
        WHERE product_id = ? AND reference_id = ?
    """
    cursor.execute(query, (homologated, datasheet, function_test, emc_test, note, current, position, new, product_id, reference_id))
    connection.commit()
