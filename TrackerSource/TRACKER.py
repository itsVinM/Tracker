import os, re, shutil, json, sqlite3, plotly
import pandas as pd
import streamlit as st
from io import BytesIO
from datetime import datetime
from sqlalchemy import create_engine
from typing import List, Dict
import plotly.figure_factory as ff
import plotly.graph_objects as go
import plotly.express as px

from database import *
from todolist import *


st.set_page_config(
    page_title="VALIDATION",
    layout="wide",
)

class ValidationTracker:
    # --- Defined Homologation Options ---
    HOMOLOGATION_OPTIONS = [
        "⏳AWAIT R&D", 
        "🆘PRODUCT N/A", 
        "🔍GOT PRODUCT", 
        "🛠️FUNCTION", 
        "📡 EMC RADIATED", 
        "⚡ EMC CONDUCTED",
        "⚙️ FACTORY",
        "❌ FAILED", 
        "✅ PASSED",
        "📋.DOC"
    ]

    def __init__(self):
        database()  # Ensure the multi-table structure and VIEW exist
        self.query = "SELECT * FROM ValidationTracker"
        self.data = self.load_data()
        self.column_config = self.get_column_config()


    

    def load_data(self) -> pd.DataFrame:
        data = get_data_from_db(self.query)

        if 'Product_ID' in data.columns:
            data['Product_ID'] = data['Product_ID'].astype(str)

        # Convert date columns to datetime
        for date_col in ['Priority', 'Closed']:
            if date_col in data.columns:
                data[date_col] = pd.to_datetime(data[date_col], errors='coerce')

            
        if 'Priority' in data.columns and 'Closed' in data.columns:
            def compute_progress(row):
                if pd.notnull(row['Priority']) and pd.notnull(row['Closed']):
                    total_days = (row['Closed'] - row['Priority']).days
                    elapsed_days = (datetime.today() - row['Priority']).days
                    if total_days > 0:
                        return min(1.0, max(0.0, elapsed_days / total_days))
                return 0.0

            data["Progress"] = data.apply(compute_progress, axis=1)

        return data




    def get_column_config(self) -> Dict[str, st.column_config.Column]:
        return {
            "Request": st.column_config.TextColumn("Request ID", disabled=False),
            "Homologated": st.column_config.SelectboxColumn(
                "Homologated",
                options=self.HOMOLOGATION_OPTIONS,
                width="medium"
            ),
            "Priority": st.column_config.DateColumn("Priority", format="YYYY-MM-DD"),
            "Closed": st.column_config.DateColumn("Closed", format="YYYY-MM-DD"),

            "Note": st.column_config.TextColumn("Note", disabled=False),
            "Current": st.column_config.TextColumn("Current", disabled=False),
            "Product": st.column_config.TextColumn("Product", disabled=False),
            "Position": st.column_config.TextColumn("Position", disabled=False),
            "New": st.column_config.TextColumn("New", disabled=False),
            "Reference": st.column_config.TextColumn("Reference", disabled=False),
            "Product_ID": st.column_config.Column(disabled=True, width="off"),
        }

    def display_editor(self, df: pd.DataFrame) -> pd.DataFrame:
        """Displays a single data editor with optional visibility of detail columns."""

        # Define column groups
        base_cols = ["Request", "Priority", "Closed", "Progress", "Homologated", "Product"]
        detail_cols = ["Note", "Current", "Position", "New", "Reference"]

        # Filter only existing columns
        base_cols = [col for col in base_cols if col in df.columns]
        detail_cols = [col for col in detail_cols if col in df.columns]

        # Toggle to show/hide detail columns
        show_details = st.checkbox("Show detailed columns", value=False)

        # Combine columns based on toggle
        visible_cols = base_cols + detail_cols if show_details else base_cols

        st.subheader("📌 Validation Tracker")
        edited_df = st.data_editor(
            df[visible_cols],
            column_config={col: self.column_config[col] for col in visible_cols},
            hide_index=True,
            num_rows="dynamic",
            key="editor_main",
        )

        return edited_df


    def save_changes(self, edited_data: pd.DataFrame):
        # Reload full data
        full_data = self.load_data()

        if edited_data.empty:
            st.warning("No changes to save.")
            return

        # Detect removed rows
        existing_keys = set(full_data['Request'])
        edited_keys = set(edited_data['Request'])
        removed_keys = existing_keys - edited_keys

        # Drop removed rows
        if removed_keys:
            full_data = full_data[~full_data['Request'].isin(removed_keys)]

        # Update existing rows
        full_data.update(edited_data)

        # Detect new rows
        new_rows = edited_data[~edited_data['Request'].isin(existing_keys)]
        if not new_rows.empty:
            full_data = pd.concat([full_data, new_rows], ignore_index=True)

        # Save back to DB
        update_data(full_data)
        st.success("✅ Changes saved successfully, including deletions and new rows.")

    def download_backup(self, edited_data: pd.DataFrame):
        # Always reload full data before exporting
        full_data = self.load_data()

        if full_data is None or full_data.empty:
            st.error("❌ Cannot download backup: No data available.")
            return

        backup = BytesIO()
        try:
            with pd.ExcelWriter(backup) as writer:
                full_data.to_excel(writer, index=False, sheet_name="ValidationData")
        except Exception as e:
            st.error(f"An error occurred during Excel creation: {e}")
            return

        today = datetime.today().strftime("%d%m%Y %H%M")
        st.download_button(
            label="🗂️ Download Backup",
            data=backup.getvalue(),
            file_name=f"Validation_{today}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


def project_tracker():
    tracker = ValidationTracker()
    df = tracker.data 
    
   
    but1, but2 = st.columns(2)

    metric1, metric2, metric3, metric4, metric5, metric6, metric7= st.columns(7)
        
    col_request, col_product, col_component, col_homologation = st.columns(4)
        
    with col_request:
            request_search = st.text_input("Search Request ID", key="tab_request_search")
            if request_search:
                df = df[df['Request'].astype(str).str.contains(request_search, case=False, na=False)]

    with col_product:
            product_search = st.text_input("Search Product (Used)", key="tab_product_search")
            if product_search:
                df = df[df['Product'].astype(str).str.contains(product_search, case=False, na=False)]

    with col_component:
            component_search = st.text_input("Search New Component", key="tab_new_component_search")
            if component_search:
                df = df[df['New'].astype(str).str.contains(component_search, case=False, na=False)]


    with col_homologation:
            homologated_filter = st.multiselect(
                "Filter by Homologation Status",
                options=tracker.HOMOLOGATION_OPTIONS,
                default=[],
                key="tab_homo_filter"
            )
            if homologated_filter:
                df = df[df['Homologated'].isin(homologated_filter)]


    edited_data = tracker.display_editor(df) 
    with but1:
            if st.button("📋 Save changes"):
                tracker.save_changes(edited_data)

    with but2:
            tracker.download_backup(edited_data) 

        # --- Progress Indicator ---
    total = len(df)
    passed = len(df[df["Homologated"] == "✅ PASSED"])
    failed = len(df[df["Homologated"] == "❌ FAILED"])
    awaitingRD = len(df[df["Homologated"] == "⏳AWAIT R&D"])
    factory=len(df[df["Homologated"] == "⚙️ FACTORY"])

    # Count entries with FUNCTION or EMC status
    function_emc = len(df[df["Homologated"].isin([
            "🛠️FUNCTION", "📡 EMC RADIATED", "⚡ EMC CONDUCTED"
        ])])

    missing = total - passed - failed - awaitingRD - factory - function_emc

    with metric1:
                st.metric("Total Request", value="", delta=total, delta_color="off")
    with metric2:
                st.metric("Passed Request", value="", delta=passed)
    with metric3:
                st.metric("Failed Request", value="", delta=-failed)
    with metric4:
                st.metric("Awaiting R&D", value="", delta=-awaitingRD)
    with metric5:
                st.metric("Factory Test", value="", delta=-factory)
                
    with metric6:
                st.metric("Missing Request", value="" ,delta= missing, delta_color="off")
    with metric7:
                st.metric("Ongoing Request", value="", delta=function_emc)
        
        
    # --- File Upload/DB Population (Stays in Sidebar) ---
    with st.sidebar:
        uploaded_file = st.file_uploader("Choose an Excel file to Populate DB", type="xlsx")
        
        if uploaded_file:
            st.info("Reading Excel file...")
            try:
                new_df = pd.read_excel(uploaded_file)
                update_data(new_df) 
                
                st.success("Database has been populated successfully.")
                st.rerun() # Rerun to load new data
                
            except Exception as e:
                st.error(f"Error processing file for DB population: {e}")
                st.warning("Ensure the uploaded file is a valid Excel (.xlsx) file.")


if __name__ == "__main__":
    project_tracker()