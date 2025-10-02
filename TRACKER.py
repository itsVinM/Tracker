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

    def load_todo(self) -> List[Dict[str, Literal["High", "Medium", "Low"]]]:
        if os.path.exists(self.TODO_FILE):
            with open(self.TODO_FILE, "r") as f:
                todos = json.load(f)
                valid_todos = []
                for item in todos:
                    task = str(item.get("task", "")).strip()
                    priority = item.get("priority", "Medium")
                    if priority not in self.PRIORITY_LEVELS:
                        priority = "Medium"
                    if task:
                        valid_todos.append({"task": task, "priority": priority})
                return valid_todos
        return []

    def save_todo(self, todos: List[Dict[str, str]]):
        with open(self.TODO_FILE, "w") as f:
            json.dump(todos, f, indent=2)

    def display_todo(self):
        st.text("📝 To-Do List")
        todos = self.load_todo()
        if todos:
            updated_todos = []
            for i, item in enumerate(todos):
                col1, col2, col3 = st.columns([0.05, 0.75, 0.2])
                done = col1.checkbox("", key=f"todo_{i}")
                if not done:
                    updated_todos.append(item)
                    col2.markdown(f"{i+1}. {item['task']}")
                    col3.markdown(f"🔺 {item['priority']}")
                else:
                    col2.markdown(f"~~{i+1}. {item['task']}~~ ✅")
                    col3.markdown(f"~~🔺 {item['priority']}~~")
            if updated_todos != todos:
                self.save_todo(updated_todos)
        else:
            st.info("No tasks saved yet.")

    def add_task(self):
        st.text("➕ Add New To-Do Item")
        new_task = st.text_input("Enter a new task")
        priority = st.selectbox("Select priority", self.PRIORITY_LEVELS)
        if st.button("Save Task"):
            if new_task.strip():
                todos = self.load_todo()
                todos.append({"task": new_task.strip(), "priority": priority})
                self.save_todo(todos)
                st.success("Task saved successfully!")
            else:
                st.warning("Please enter a valid task.")

# --- Main App ---
def project_tracker():
    with st.sidebar:
        st.markdown("Validation tracker by Vincentiu")
        uploaded_file = st.file_uploader("Choose an Excel file", type="xlsx")
        if uploaded_file:
            fill_database(uploaded_file)
            st.success("Database has been populated successfully.")

    tab1, tab2 = st.tabs(["📊 Validation request", "📥Todo!()"])

    with tab1:
        tracker = ValidationTracker()
        but1, but2, _, _ = st.columns(4, gap="small")
        edited_data = tracker.display_editor()

        with but1:
            if st.button("💾 Save Changes"):
                tracker.save_changes(edited_data)

        with but2:
            tracker.download_backup(edited_data)

    with tab2:
        todo = TodoManager()
        todo.display_todo()
        todo.add_task()

project_tracker()