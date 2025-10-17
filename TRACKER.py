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

    # --- Priority Options with Emojis ---
    PRIORITY_OPTIONS = [
        "🔴 High",
        "🟡 Medium",
        "🟢 Low"
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

        # Add missing columns with default values
        if 'Priority' not in data.columns:
            data['Priority'] = "🟢 Low"
        if 'Start_Date' not in data.columns:
            data['Start_Date'] = pd.to_datetime("today").normalize()
        if 'End_Date' not in data.columns:
            data['End_Date'] = pd.to_datetime("today").normalize()
        if 'Progress' not in data.columns:
            data['Progress'] = 0.0  # Progress as float between 0 and 1

        return data

    def get_column_config(self) -> Dict[str, st.column_config.Column]:
        return {
            "Request": st.column_config.TextColumn("Request ID", disabled=False),
            "Homologated": st.column_config.SelectboxColumn(
                "Homologated",
                options=self.HOMOLOGATION_OPTIONS,
                width="medium"
            ),
            "Priority": st.column_config.SelectboxColumn(
                "Priority",
                options=self.PRIORITY_OPTIONS,
                width="small"
            ),
            "Start_Date": st.column_config.DateColumn("Start Date"),
            "End_Date": st.column_config.DateColumn("End Date"),
            "Progress": st.column_config.ProgressColumn("Progress", min_value=0.0, max_value=1.0, format="%.0f%%"),
            "Note": st.column_config.TextColumn("Note", disabled=False),
            "Current": st.column_config.TextColumn("Current", disabled=False),
            "Product": st.column_config.TextColumn("Product", disabled=False),
            "Position": st.column_config.TextColumn("Position", disabled=False),
            "New": st.column_config.TextColumn("New", disabled=False),
            "Reference": st.column_config.TextColumn("Reference", disabled=False),
            "Product_ID": st.column_config.Column(disabled=True, width="off"),
        }

 
    def display_editor(self, df: pd.DataFrame) -> pd.DataFrame:
        """Displays the data editor split into two synchronized views."""

        # Define desired column groups
        left_cols = ["Request", "Priority", "Homologated", "Product", "Start_Date", "End_Date", "Progress"]
        right_cols = ["Note", "Current", "Position", "New", "Reference"]

        # Filter only existing columns
        left_cols = [col for col in left_cols if col in df.columns]
        right_cols = [col for col in right_cols if col in df.columns]

        col1, col2 = st.columns([1, 2], width="stretch")

        with col1:
            st.subheader("📌 Tracker Overview")
            edited_left = st.data_editor(
                df[left_cols],
                column_config={col: self.column_config[col] for col in left_cols},
                hide_index=True,
                num_rows="dynamic",
                key="editor_left"
            )

        with col2:
            st.subheader("📄 Details")
            edited_right = st.data_editor(
                df[right_cols],
                column_config={col: self.column_config[col] for col in right_cols},
                hide_index=True,
                num_rows="dynamic",
                key="editor_right"
            )

        # Merge edited data back together
        edited_df = pd.concat([edited_left, edited_right], axis=1)

        return edited_df


    def save_changes(self, edited_data: pd.DataFrame):
        update_data(edited_data)
        st.success("Changes saved successfully to the multi-table database.")

    def download_backup(self, edited_data: pd.DataFrame):
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
            label="🗂️ Download Backup",
            data=backup.getvalue(),
            file_name=f"Backup_Project_Tracker_{today}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


def project_tracker():
    tracker = ValidationTracker()
    df = tracker.data 
    
    tab1, tab2 = st.tabs(["📋 Validation Status","📥 Todo!"])

    with tab1:
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