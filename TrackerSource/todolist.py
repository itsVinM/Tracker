import os, json
import pandas as pd
import streamlit as st
from datetime import datetime
from typing import List, Dict
import plotly.express as px

class TodoManager:
    TODO_FILE = "todo_list.json"
    PRIORITY_LEVELS = ["High", "Medium", "Low"]

    def load_todo(self) -> List[Dict[str, str]]:
        if os.path.exists(self.TODO_FILE):
            with open(self.TODO_FILE, "r") as f:
                return json.load(f)
        return []

    def save_todo(self, todos: List[Dict[str, str]]):
        with open(self.TODO_FILE, "w") as f:
            json.dump(todos, f, indent=2)

    def add_task(self):
        with st.expander("➕ Add Task", expanded=False):
            new_task = st.text_input("Enter a new task")
            priority = st.selectbox("Select priority", self.PRIORITY_LEVELS)
            due_date = st.date_input("Select due date", value=datetime.today())
            note = st.text_area("Optional note")

            if st.button("Save Task"):
                if new_task.strip():
                    todos = self.load_todo()
                    todos.append({
                        "task": new_task.strip(),
                        "priority": priority,
                        "due_date": due_date.strftime("%Y-%m-%d"),
                        "note": note.strip()
                    })
                    self.save_todo(todos)
                    st.success("Task saved successfully!")
                else:
                    st.warning("Please enter a valid task.")



    def display_calendar(self):
        todos = self.load_todo()
        if not todos:
            st.info("No tasks to display.")
            return

        df = pd.DataFrame(todos)
        df["due_date"] = pd.to_datetime(df["due_date"], errors="coerce")
        df["start"] = datetime.today()  # Optional: use today as start
        df["end"] = df["due_date"]
        df["Task"] = df["task"] + " (" + df["product"] + ")"

        fig = px.timeline(df, x_start="start", x_end="end", y="Task", color="priority")
        fig.update_yaxes(categoryorder="total ascending")
        st.plotly_chart(fig, use_container_width=True)