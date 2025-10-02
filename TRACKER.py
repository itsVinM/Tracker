import os
import json
import pandas as pd
import streamlit as st
from io import BytesIO
from datetime import datetime
from sqlalchemy import create_engine
from typing import List, Dict, Literal

from libraries import *  
from database import *   

st.set_page_config(
    page_title="PRODUCT ENGINEERING - VALIDATION",
    layout="wide",
)

# --- Validation Tracker Class ---
class ValidationTracker:
    def __init__(self):
        database()
        self.query = "SELECT * FROM ProjectTracker"
        self.data = self.load_data()
        self.column_config = self.get_column_config()

    def load_data(self) -> pd.DataFrame:
        data = get_data_from_db(self.query)

        # Enforce data types
        if 'Day' in data.columns:
            data['Day'] = pd.to_datetime(data['Day'], errors='coerce')
        for col in ['Datasheet', 'Function', 'EMC']:
            if col in data.columns:
                data[col] = data[col].astype(bool)
        if 'Homologated' not in data.columns:
            data['Homologated'] = ""
        data['Progress'] = data.apply(
            lambda row: 0 if row["Homologated"] in ["Passed", "Failed"]
            else (pd.Timestamp.now() - row["Day"]).days if pd.notnull(row["Day"]) else 0,
            axis=1
        )
        data['Progress'] = data['Progress'].astype(int)
        return data

    def get_column_config(self) -> Dict[str, st.column_config.Column]:
        return {
            "Datasheet": st.column_config.CheckboxColumn("Datasheet", default=False),
            "Function": st.column_config.CheckboxColumn("Function", default=False),
            "EMC": st.column_config.CheckboxColumn("EMC", default=False),
            "Progress": st.column_config.ProgressColumn(
                "Progress", min_value=0, max_value=40, format="%.0f days"
            ),
            "Homologated": st.column_config.TextColumn(
                "Homologated", help="Status of validation", validate=".*", required=False
            )
        }

    def display_editor(self) -> pd.DataFrame:
        return st.data_editor(
            self.data,
            hide_index=True,
            num_rows="dynamic",
            column_config=self.column_config
        )

    def save_changes(self, edited_data: pd.DataFrame):
        engine = create_engine('sqlite:///project_tracker.db')
        edited_data.to_sql('ProjectTracker', con=engine, if_exists='replace', index=False)
        st.success("Changes saved successfully.")

    def download_backup(self, edited_data: pd.DataFrame):
        backup = BytesIO()
        with pd.ExcelWriter(backup) as writer:
            edited_data.to_excel(writer, index=False)
        today = datetime.today().strftime("%d%m%Y")
        st.download_button(
            label="🗂️ Download Backup",
            data=backup.getvalue(),
            file_name=f"Backup_Project_Tracker_{today}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


# --- To-Do Manager Class ---
class TodoManager:
    TODO_FILE = "todo_list.json"
    PRIORITY_LEVELS = ["High", "Medium", "Low"]

    def load_todo(self) -> List[Dict[str, str]]:
        if os.path.exists(self.TODO_FILE):
            with open(self.TODO_FILE, "r") as f:
                todos = json.load(f)
                valid_todos = []
                for item in todos:
                    task = str(item.get("task", "")).strip()
                    priority = item.get("priority", "Medium")
                    due_date = item.get("due_date", "")
                    if priority not in self.PRIORITY_LEVELS:
                        priority = "Medium"
                    if task:
                        valid_todos.append({
                            "task": task,
                            "priority": priority,
                            "due_date": due_date
                        })
                return valid_todos
        return []

    def save_todo(self, todos: List[Dict[str, str]]):
        with open(self.TODO_FILE, "w") as f:
            json.dump(todos, f, indent=2)

    def display_calendar(self):
        todos = self.load_todo()
        if not todos:
            st.info("No tasks scheduled.")
            return

        df = pd.DataFrame(todos)
        df["due_date"] = pd.to_datetime(df["due_date"], errors="coerce")

        # Sort by priority and due date
        priority_order = {"High": 1, "Medium": 2, "Low": 3}
        df["priority_rank"] = df["priority"].map(priority_order)
        df = df.sort_values(["priority_rank", "due_date"])

        priority_colors = {
            "High": "#902018",   # Red
            "Medium": "#93871c", # Yellow
            "Low": "#2b6a2d"     # Green
        }

        # Create 3 columns for Low, Medium, High
        col_low, col_medium, col_high = st.columns(3)

        for priority, col in zip(["Low", "Medium", "High"], [col_low, col_medium, col_high]):
            with col:
                st.markdown(f"### {priority}")
                priority_tasks = df[df["priority"] == priority]

                if priority_tasks.empty:
                    st.markdown("No tasks.")
                else:
                    for i, row in priority_tasks.iterrows():
                        due_date = row["due_date"]
                        date_str = due_date.strftime('%d %b %Y') if pd.notnull(due_date) else "No due date"
                        task_key = f"{row['task']}_{i}"

                        st.markdown(f"""
                        <div style="background-color:{priority_colors[priority]}; padding:4px; border-radius:4px; margin-bottom:4px; font-size:12px; color:white;">
                            📝 <strong>{row['task']}</strong><br>
                            📆 <em>{date_str}</em>
                        </div>
                        """, unsafe_allow_html=True)

                        with st.expander("❌ Cancel", expanded=False):
                            confirm_key = f"confirm_{task_key}"
                            if st.checkbox(f"Confirm cancel '{row['task']}'", key=confirm_key):
                                todos.remove({
                                    "task": row["task"],
                                    "priority": row["priority"],
                                    "due_date": row["due_date"].strftime("%Y-%m-%d") if pd.notnull(row["due_date"]) else ""
                                })
                                self.save_todo(todos)
                                st.success(f"Task '{row['task']}' cancelled.")
                                
    
    def add_task(self):
            new_task = st.text_input("Enter a new task")
            priority = st.selectbox("Select priority", self.PRIORITY_LEVELS)
            due_date = st.date_input("Select due date", value=datetime.today())
            if st.button("Save Task"):
                if new_task.strip():
                    todos = self.load_todo()
                    todos.append({
                        "task": new_task.strip(),
                        "priority": priority,
                        "due_date": due_date.strftime("%Y-%m-%d")
                    })
                    self.save_todo(todos)
                    st.success("Task saved successfully!")
                else:
                    st.warning("Please enter a valid task.")

    


# --- Main App ---
def project_tracker():
    
    with st.sidebar:
        st.markdown("📊 Validation tracker by Vincentiu")
        uploaded_file = st.file_uploader("Choose an Excel file", type="xlsx")
        debug_mode = st.checkbox("🔧 Developer Mode", value=False)
        if uploaded_file:
            fill_database(uploaded_file)
            st.success("Database has been populated successfully.")

    tab1, tab2 = st.tabs(["📊 Validation request", "📥Todo!()"])

    with tab1:
        tracker = ValidationTracker()
        but1, but2, but3, but4 = st.columns(4, gap="small")
        edited_data = tracker.display_editor()

        with but1:
            if st.button("💾 Save Changes"):
                tracker.save_changes(edited_data)

        with but2:
            tracker.download_backup(edited_data)

        
        if debug_mode:
                with but3:
                    if st.button("📥 High volume reports"):
                        tracker.generate_reports(edited_data)

                with but4:
                    if st.button("💼 Single report"):
                        st.info("Single report generation logic goes here.")


    
    with tab2:
        todo = TodoManager()
        todo.display_calendar()
        todo.add_task()


project_tracker()