import pandas as pd
import streamlit as st
import json
from io import BytesIO
from datetime import datetime
from typing import Dict, List, Any, Optional

from database import *

class ValidationChecker:
  
    def __init__(self):
        # Initial load from database to populate the display state
        if 'checker_data' not in st.session_state:
             st.session_state['checker_data'] = self.load_data()
             
        self.data = st.session_state['checker_data']
        self.column_config = self.get_column_config()

    def load_data(self, request_id: Optional[str] = None, product_model: Optional[str] = None) -> pd.DataFrame:
        """
        Loads all data from the database and performs in-memory filtering.
        """
        # Query the specific Checker table
        query = "SELECT * FROM ValidationChecker_Data"
        df_master = get_data_from_db(query)

        df_filtered = df_master.copy()
        
        # Perform filtering on the returned DataFrame
        if request_id:
            request_id = request_id.strip()
            df_filtered = df_filtered[df_filtered['Request'].astype(str).str.contains(request_id, case=False, na=False)]
        
        if product_model:
            product_model = product_model.strip()
            df_filtered = df_filtered[df_filtered['Product'].astype(str).str.contains(product_model, case=False, na=False)]

        return df_filtered

    def get_column_config(self) -> Dict[str, st.column_config.Column]:
        return {
            "Request": st.column_config.TextColumn("Request ID", help="The unique request identifier.", disabled=False),
            "Product": st.column_config.TextColumn("Product Model", help="The product being validated.", disabled=False),
            "Current": st.column_config.TextColumn("Current Version", help="The existing product version.", disabled=False),
            "New": st.column_config.TextColumn("New Version", help="The target product version.", disabled=False),
            "ISO_Standards": st.column_config.TextColumn("ISO / Standards", help="Applicable standards.", disabled=False),
            "Equip_Used": st.column_config.TextColumn("Equipment Used", help="List of primary equipment used.", disabled=False),
            "Engineer": st.column_config.TextColumn("Engineer", help="Validating Engineer.", disabled=False),
            "Checker_ID": st.column_config.Column(disabled=True, width="off"),
            "Tests_JSON": st.column_config.Column(disabled=True, width="off"),
        }

    def parse_tests_json(self, json_string: str) -> List[Dict[str, Any]]:
        """Safely parses the JSON string for test details."""
        try:
            return json.loads(json_string)
        except (json.JSONDecodeError, TypeError):
            return []

    def display_editor(self, df: pd.DataFrame) -> pd.DataFrame:
        """Displays the data editor for the main fields."""
        
        editor_cols = ["Request", "Product", "Current", "New", "ISO_Standards", "Equip_Used", "Engineer"]
        visible_cols = [col for col in editor_cols if col in df.columns]
        
        # Hide the 'Checker_ID' and 'Tests_JSON' columns which are internal DB fields
        col_config = {col: self.column_config.get(col) for col in visible_cols}

        edited_df = st.data_editor(
            df[visible_cols],
            column_config=col_config,
            hide_index=True,
            num_rows="dynamic",
            key="checker_editor_main",
        )
        return edited_df

    def display_test_details(self, df: pd.DataFrame):
        """Displays the nested test details for each entry using st.expander."""
        
        st.markdown("---")
        st.subheader("📊 Detailed Test Results")
        
        if df.empty:
            st.info("Load data or perform a search to view test details.")
            return

        for index, row in df.iterrows():
            request_id = row['Request']
            product_name = row['Product']
            # Safely get and parse the JSON string
            test_details = self.parse_tests_json(row.get('Tests_JSON', '[]'))

            with st.expander(f"**{request_id}** - {product_name} ({len(test_details)} Tests Recorded)"):
                if test_details:
                    test_df = pd.DataFrame(test_details)
                    st.dataframe(
                        test_df, 
                        hide_index=True,
                        column_config={
                            "Test Id": st.column_config.TextColumn("Test ID"),
                            "purpose": st.column_config.TextColumn("Purpose"),
                            "results": st.column_config.TextColumn("Result"),
                        }
                    )
                else:
                    st.warning("No structured test results found for this request (Tests_JSON column is empty or invalid).")
        st.markdown("---")

    def save_changes(self, edited_data: pd.DataFrame):
        """Saves changes back to the database."""
        
        # 1. Load the current full master data from the database
        full_master_data = self.load_data() 
        
        if edited_data.empty:
            st.warning("No changes to save.")
            return

        # Drop rows where 'Request' is missing (from dynamic row additions that weren't filled out)
        edited_data = edited_data.dropna(subset=['Request'])
        if edited_data.empty:
             st.warning("No valid rows to save (Request ID missing).")
             return
             
        # Use Request ID as the index for merging
        full_master_data = full_master_data.set_index('Request')
        edited_data_indexed = edited_data.set_index('Request')
        
        # Iterate over edited rows and merge them into the master data
        for req_id, row in edited_data_indexed.iterrows():
            # Check if this is an existing or new Request ID
            if req_id in full_master_data.index:
                # Update existing row using the columns from the editor
                for col in row.index:
                    full_master_data.loc[req_id, col] = row[col]
            else:
                # Add new row
                new_row = row.to_dict()
                # Populate required internal columns with defaults for new rows
                new_row['Tests_JSON'] = new_row.get('Tests_JSON', '[]')
                new_row['Checker_ID'] = new_row.get('Checker_ID', str(int(datetime.now().timestamp() * 1000000))) 
                full_master_data.loc[req_id] = new_row
                
        updated_full_master_data = full_master_data.reset_index()

        # Write the entire updated master dataframe back to the database
        update_checker_data(updated_full_master_data) 
        st.session_state['checker_data'] = updated_full_master_data.copy() # Update display state
        st.success("✅ Checker Changes saved successfully.")


    def download_backup(self, df: pd.DataFrame):
        """Creates an Excel backup of the currently displayed dataset."""
        if df is None or df.empty:
            st.error("❌ Cannot download backup: No data available to download.")
            return

        backup = BytesIO()
        try:
            # Ensure the internal columns (Tests_JSON, Checker_ID) are included in the backup
            backup_df = df.copy() 
            with pd.ExcelWriter(backup, engine='xlsxwriter') as writer:
                backup_df.to_excel(writer, index=False, sheet_name="CheckerData")
        except Exception as e:
            st.error(f"An error occurred during Excel creation: {e}")
            return

        today = datetime.today().strftime("%d%m%Y %H%M")
        
        st.download_button(
            label="⬇️ Download Filtered Data Backup",
            data=backup.getvalue(),
            file_name=f"ValidationChecker_Filtered_{today}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="checker_download_btn"
        )
