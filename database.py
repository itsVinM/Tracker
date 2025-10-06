import sqlite3
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine

DB_NAME = 'project_tracker.db'

def initialize_database(db_path: str = DB_NAME) -> None:
    """Create simplified tables: ProductOrders and HomologationStatus."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ProductOrders (
                product_id TEXT,
                reference_id TEXT,
                current TEXT,
                new TEXT,
                PRIMARY KEY (product_id, reference_id)   
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

        # Rename 'product' to 'product_id'
        df.rename(columns={'product': 'product_id'}, inplace=True)

        

        product_orders_df = df[['product_id', 'reference_id']].copy()

        homologation_df = df[['product_id', 'Current', 'New', 'Position', 'Homologated', 'Datasheet', 'Function', 'EMC', 'Note' ]].copy()
        homologation_df.rename(columns={
            'Function': 'function_test',
            'EMC': 'emc_test',
            'Datasheet': 'datasheet'
        }, inplace=True)

        engine = create_engine(f'sqlite:///{db_path}')
        product_orders_df.to_sql('ProductOrders', con=engine, if_exists='replace', index=False)
        homologation_df.to_sql('HomologationStatus', con=engine, if_exists='replace', index=False)

    except Exception as e:
        print(f"Error loading Excel file: {e}")

def get_data_from_db(query: str, db_path: str = DB_NAME) -> pd.DataFrame:
    with sqlite3.connect(db_path) as conn:
        return pd.read_sql_query(query, conn)

def update_homologation_status(
    product_id: str,
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
            UPDATE HomologationStatus
            SET current = ?, new = ?, position = ?, homologated = ?, datasheet = ?, function_test = ?, emc_test = ?, note = ?, 
            WHERE product_id = ?
        """, (
            current, new, position,homologated, datasheet, function_test, emc_test, note,
            product_id
        ))
        conn.commit()
