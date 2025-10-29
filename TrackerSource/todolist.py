import os, json
import pandas as pd
import streamlit as st
from datetime import datetime
from typing import List, Dict
from streamlit_calendar import calendar  # pip install streamlit-calendar
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

    def display_calendar_and_gantt(self):
        st.subheader("📅 Calendar & 📊 Gantt Chart")
        todos = self.load_todo()
        if not todos:
            st.info("No tasks scheduled.")
            return

        df = pd.DataFrame(todos)
        df["due_date"] = pd.to_datetime(df["due_date"], errors="coerce")

        # Prepare events for calendar
        events = []
        for t in todos:
            color = "#d9534f" if t["priority"] == "High" else "#f0ad4e" if t["priority"] == "Medium" else "#5cb85c"
            events.append({
                "title": t["task"],
                "start": t["due_date"],
                "color": color
            })

        # Two-column layout
        col_calendar, col_gantt = st.columns([2, 3])

        with col_calendar:
            st.markdown("### Calendar View")
            selected_date = st.date_input("Select a date", value=datetime.today())
            calendar(events=events)

            # Show tasks for selected date
            day_tasks = df[df["due_date"].dt.date == selected_date]
            st.markdown("#### Tasks for Selected Day")
            if day_tasks.empty:
                st.info("No tasks for this day.")
            else:
                for priority in self.PRIORITY_LEVELS:
                    st.markdown(f"**{priority}**")
                    for _, row in day_tasks[day_tasks["priority"] == priority].iterrows():
                        st.write(f"- {row['task']}")

        with col_gantt:
            st.markdown("### Gantt Chart")
            # Create Gantt chart using Plotly
            df["start"] = df["due_date"]
            df["end"] = df["due_date"]  # Single-day tasks
            color_map = {"High": "red", "Medium": "orange", "Low": "green"}
            fig = px.timeline(df, x_start="start", x_end="end", y="task", color="priority",
                              color_discrete_map=color_map, title="Task Timeline")
            fig.update_yaxes(autorange="reversed")  # Gantt style
            st.plotly_chart(fig, use_container_width=True)