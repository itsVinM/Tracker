import pandas as pd
import streamlit as st
from io import BytesIO
from datetime import datetime
import plotly.graph_objects as go

from database import (
    initialize_database,
    get_data_from_db,
    fill_database_from_excel,
    update_homologation_status
)
from todolist import TodoManager

st.set_page_config(
    page_title="PRODUCT ENGINEERING - VALIDATION",
    layout="wide",
)

# --- Validation Tracker Class ---
class ValidationTracker:
    def __init__(self):
        initialize_database()
        self.query = """
            SELECT po.reference_id, po.current, po.new,
                   hs.product_id, hs.homologated, hs.datasheet, hs.function_test,
                   hs.emc_test, hs.note, hs.position
            FROM ProductOrders po
            JOIN HomologationStatus hs ON po.product_id = hs.product_id
        """
        self.data = self.load_data()
        self.column_config = self.get_column_config()

    def load_data(self) -> pd.DataFrame:
        df = get_data_from_db(self.query)
        for col in ['datasheet', 'function_test', 'emc_test']:
            if col in df.columns:
                df[col] = df[col].astype(bool)
        return df

    def get_column_config(self) -> dict:
        return {
            "datasheet": st.column_config.CheckboxColumn("Datasheet", default=False),
            "function_test": st.column_config.CheckboxColumn("Function", default=False),
            "emc_test": st.column_config.CheckboxColumn("EMC", default=False),
            "homologated": st.column_config.SelectboxColumn(
                "Homologated",
                options=["⏳AWAIT", "🛠️FUNCTION", "📡 EMC", "❌ FAILED", "✅ PASSED"]
            )
        }

    def apply_filters(self) -> pd.DataFrame:
        df = self.data.copy()

        st.sidebar.markdown("### 🔍 Filters")

        ref_filter = st.sidebar.selectbox("Reference ID", options=["All"] + sorted(df['reference_id'].unique()))
        prod_filter = st.sidebar.selectbox("Product ID", options=["All"] + sorted(df['product_id'].unique()))

        if ref_filter != "All":
            df = df[df['reference_id'] == ref_filter]
        if prod_filter != "All":
            df = df[df['product_id'] == prod_filter]


        return df

    def display_editor(self) -> pd.DataFrame:
        filtered_data = self.apply_filters()
        return st.data_editor(
            filtered_data,
            hide_index=True,
            num_rows="dynamic",
            column_config=self.column_config
        )

    def save_changes(self, edited_data: pd.DataFrame):
        for _, row in self.data.iterrows():  # Save full dataset
            update_homologation_status(
                product_id=row['product_id'],
                homologated=row['homologated'],
                datasheet=row['datasheet'],
                function_test=row['function_test'],
                emc_test=row['emc_test'],
                note=row['note'],
                current=row['current'],
                position=row['position'],
                new=row['new']
            )
        st.success("✅ Changes saved successfully.")

    def download_backup(self, edited_data: pd.DataFrame):
        backup = BytesIO()
        with pd.ExcelWriter(backup) as writer:
            self.data.rename(columns={
                'function_test': 'Function',
                'emc_test': 'EMC',
                'datasheet': 'Datasheet',
                'current': 'Current',
                'new': 'New',
            }, inplace=True)
            self.data.to_excel(writer, index=False)
        today = datetime.today().strftime("%d%m%Y")
        st.download_button(
            label="🗂️ Download Backup",
            data=backup.getvalue(),
            file_name=f"Backup_Project_Tracker_{today}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    def display_charts(self):
        df = self.data

        def count_checked(column):
            return df[column].value_counts().rename({True: 'Checked', False: 'Unchecked'})

        datasheet_counts = count_checked('datasheet')
        function_counts = count_checked('function_test')
        emc_counts = count_checked('emc_test')

        fig = go.Figure()

        for category, counts in zip(
            ['Datasheet', 'Function', 'EMC'],
            [datasheet_counts, function_counts, emc_counts]
        ):
            fig.add_trace(go.Bar(name=f'{category} Checked', x=[category], y=[counts.get('Checked', 0)], marker_color='lightgreen'))
            fig.add_trace(go.Bar(name=f'{category} Unchecked', x=[category], y=[counts.get('Unchecked', 0)], marker_color='salmon'))

        fig.update_layout(
            title="Validation Summary",
            barmode='group',
            xaxis_title="Category",
            yaxis_title="Validation Counts",
            width=800,
            height=600
        )

        st.plotly_chart(fig, use_container_width=True)

# --- Main App ---
def project_tracker():
    with st.sidebar:
        st.markdown("📊 Validation tracker used for its simplicity")
        st.markdown("* Possibility to add automatic report generator")
        st.markdown("* Possibility to add Gantt chart and structure it more for project managers")

        uploaded_file = st.file_uploader("📥 Upload Excel file", type="xlsx")
        if uploaded_file:
            fill_database_from_excel(uploaded_file)
            st.success("📁 Database has been populated successfully.")

    tab1, tab2 = st.tabs(["📊 Validation Request", "📥 Todo"])

    with tab1:
        tracker = ValidationTracker()
        col1, col2 = st.columns(2, gap="small")
        st.text("MOS, Diodes and all resonant components need EMC & Functionality test")
        edited_data = tracker.display_editor()
        tracker.display_charts()

        with col1:
            if st.button("💾 Save Changes"):
                tracker.save_changes(edited_data)

        with col2:
            tracker.download_backup(edited_data)

        

    with tab2:
        todo = TodoManager()
        with st.expander("➕ Add Task"):
            todo.add_task()
        todo.display_calendar()

# --- Run App ---
project_tracker()