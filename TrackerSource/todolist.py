
import os, json
import pandas as pd
import streamlit as st
from datetime import datetime
from typing import List, Dict
from streamlit_calendar import calendar  # pip install streamlit-calendar
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
        st.subheader("➕ Add New Task")
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

    def display_calendar(self):
        st.subheader("📅 Task Calendar")
        todos = self.load_todo()
        if not todos:
            st.info("No tasks scheduled.")
            return

        df = pd.DataFrame(todos)
        df["due_date"] = pd.to_datetime(df["due_date"], errors="coerce")

        # Prepare events for streamlit-calendar
        events = []
        for t in todos:
            color = "#d9534f" if t["priority"] == "High" else "#f0ad4e" if t["priority"] == "Medium" else "#5cb85c"
            events.append({
                "title": t["task"],
                "start": t["due_date"],
                "color": color
            })

        # Two-column layout
        col_calendar, col_list = st.columns([2, 2])

        with col_calendar:
            st.markdown("### Calendar View")
            selected_date = st.date_input("Select a date", value=datetime.today())
            calendar(events=events)

        with col_list:
            st.markdown("### Priority List for Selected Day")
            day_tasks = df[df["due_date"].dt.date == selected_date]
            if day_tasks.empty:
                st.info("No tasks for this day.")
            else:
                for priority in self.PRIORITY_LEVELS:
                    st.markdown(f"#### {priority}")
                    priority_tasks = day_tasks[day_tasks["priority"] == priority]
                    for i, row in priority_tasks.iterrows():
                        st.write(f"- {row['task']}")

                        # Edit/Delete options
                        with st.expander("Edit / Delete"):
                            new_task = st.text_input("Edit task", value=row["task"], key=f"edit_task_{i}")
                            new_priority = st.selectbox("Edit priority", self.PRIORITY_LEVELS, index=self.PRIORITY_LEVELS.index(row["priority"]), key=f"edit_priority_{i}")
                            new_due_date = st.date_input("Edit due date", value=row["due_date"], key=f"edit_date_{i}")

                            if st.button("Save Changes", key=f"save_{i}"):
                                todos[i] = {
                                    "task": new_task.strip(),
                                    "priority": new_priority,
                                    "due_date": new_due_date.strftime("%Y-%m-%d")
                                }
                                self.save_todo(todos)
                                st.success("Task updated successfully!")

                            if st.button("Delete Task", key=f"delete_{i}"):
                                todos.pop(i)
                                self.save_todo(todos)
                                st.warning("Task deleted.")
