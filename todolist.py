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
from docx import Document

# --- To-Do Manager Class ---
class TodoManager:
    TODO_FILE = "database/todo_list.json"
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

        priority_order = {"High": 1, "Medium": 2, "Low": 3}
        df["priority_rank"] = df["priority"].map(priority_order)
        df = df.sort_values(["priority_rank", "due_date"])

        priority_colors = {
            "High": "#d9534f",   # Red
            "Medium": "#f0ad4e", # Orange
            "Low": "#5cb85c"     # Green
        }
        col_high, col_medium, col_low = st.columns(3)

        for priority, col in zip(["High", "Medium", "Low"], [col_high, col_medium, col_low]):
            with col:
                st.markdown(f"#### {priority}")
                priority_tasks = df[df["priority"] == priority]

                for i, row in priority_tasks.iterrows():
                    due_date = row["due_date"]
                    date_str = due_date.strftime('%d %b %Y') if pd.notnull(due_date) else "No due date"
                    task_key = f"{row['task']}_{i}"

                    st.markdown(f"""
                    <div style="background-color:{priority_colors[priority]}; padding:8px; border-radius:6px; margin-bottom:8px; font-size:13px; color:white;">
                        <strong>📝 {row['task']}</strong><br>
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