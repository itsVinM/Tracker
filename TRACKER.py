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

# IMPORTANT: Ensure these files exist in your directory.
from database import *
from todolist import *
st.set_page_config(
    page_title="PRODUCT ENGINEERING - VALIDATION",
    layout="wide",
)
# --- Validation Tracker Class ---
class ValidationTracker:
    # --- Defined Homologation Options (Updated as requested) ---
    HOMOLOGATION_OPTIONS = [
        "⏳AWAIT R&D", 
        "🆘PRODUCT N/A", 
        "🔍GOT PRODUCT", 
        "🛠️FUNCTION", 
        "📡 EMC RADIATED", 
        "⚡ EMC CONDUCTED", 
        "❌ FAILED", 
        "✅ PASSED" 
    ]

    # -----------------------------------------------------------

    def __init__(self):
        database() # Ensure the multi-table structure and VIEW exist
        self.query = "SELECT * FROM ValidationTracker" 
        self.data = self.load_data()
        self.column_config = self.get_column_config()

    def load_data(self) -> pd.DataFrame:
        data = get_data_from_db(self.query)

        # Enforce data types for display
        for col in ['Datasheet', 'Function', 'EMC']:
            if col in data.columns:
                # Convert SQLite integers (0/1) to Python bools
                data[col] = data[col].astype(bool) 
        
        # Convert internal keys to string for display/hiding
        if 'Product_ID' in data.columns:
            data['Product_ID'] = data['Product_ID'].astype(str)
        
        return data 
    


    def get_column_config(self) -> Dict[str, st.column_config.Column]:
        return {
            "Request": st.column_config.TextColumn("Request ID", disabled=False),

            "Datasheet": st.column_config.CheckboxColumn("Datasheet", default=False, width="small"),
            "Function": st.column_config.CheckboxColumn("Function", default=False, width="small"),
            "EMC": st.column_config.CheckboxColumn("EMC", default=False, width="small"),
            "Homologated": st.column_config.SelectboxColumn(
                        "Homologated",
                        options=self.HOMOLOGATION_OPTIONS, 
                        width="medium"), 
                        
            "Note": st.column_config.TextColumn("Note", disabled=False),
            "Current": st.column_config.TextColumn("Current", disabled=False),
            "Product": st.column_config.TextColumn("Product", disabled=False),
            "Position": st.column_config.TextColumn("Position", disabled=False),
            "New": st.column_config.TextColumn("New", disabled=False),
            "Reference": st.column_config.TextColumn("Reference", disabled=False),
            
            "Product_ID": st.column_config.Column(disabled=True, width="off"), 
        }

    def display_editor(self, df: pd.DataFrame) -> pd.DataFrame:
        """Displays the data editor with the current (potentially filtered) data."""
        return st.data_editor(
            df,
            hide_index=True,
            num_rows="dynamic",
            column_config=self.get_column_config(), 
            key="validation_data_editor"
        )

    def save_changes(self, edited_data: pd.DataFrame):
        # Calls the function from database.py that updates the 3 separate tables
        # This function expects a DataFrame!
        update_data(edited_data) 
        st.success("Changes saved successfully to the multi-table database.")

    def download_backup(self, edited_data: pd.DataFrame):
        # FIX: Check if the DataFrame is empty before attempting to write to Excel
        if edited_data.empty:
            st.error("Cannot download backup: The current filtered view contains no data.")
            return

        backup = BytesIO()
        try:
            with pd.ExcelWriter(backup) as writer:
                edited_data.to_excel(writer, index=False, sheet_name="ValidationData") 
        except Exception as e:
            st.error(f"An error occurred during Excel creation: {e}")
            return

        today = datetime.today().strftime("%d%m%Y")
        st.download_button(
            label="🗂️ Download Backup (Current View)",
            data=backup.getvalue(),
            file_name=f"Backup_Project_Tracker_{today}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


def project_tracker():
    tracker = ValidationTracker()
    df = tracker.data 
    
    tab1, tab2 = st.tabs(["📋 Validation Request","📥 Todo!"])

    with tab1:
        st.subheader("Validation Tracker - Project Status")
        but1, but2,metric1, metric2, metric3, metric4 = st.columns(6)
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
        status_counts = df["Homologated"].value_counts()
        total = len(df)
        passed = len(df[df["Homologated"] == "✅ PASSED"])
        failed = len(df[df["Homologated"] == "❌ FAILED"])
        awaitRD=failed = len(df[df["Homologated"] == "❌ FAILED"])
        function_emc = (df["Function"] | df["EMC"]).sum()
        missing= total-passed-failed

        with st.container():
            with metric1:
                st.metric(f"Total & Passed", total , passed)
            with metric2:
                st.metric(f"Total & Failed", total , -failed)
            with metric3:
                st.metric(f"Miss & Ongoing", value=missing, delta= function_emc)
            
            with metric4:
                # Bar chart of all statuses
                chart_data = pd.DataFrame({
                    "Status": status_counts.index,
                    "Count": status_counts.values
                })

                fig = px.bar(chart_data, x="Status", y="Count", text="Count",
                            title="Homologation Status Distribution")
                fig.update_traces(textposition='outside')
                fig.update_layout(yaxis_title="Count", xaxis_title="Status", height=500)

                st.plotly_chart(fig, use_container_width=True)


        
    with tab2:
        todo = TodoManager() 
        with st.expander("Add task"):
            todo.add_task()
        todo.display_calendar()
        
    # --- File Upload/DB Population (Stays in Sidebar) ---
    with st.sidebar:
        st.markdown("### 🗄️ Database Management")
        st.markdown("---")
        st.subheader("Data Upload (Overwrite DB)")
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