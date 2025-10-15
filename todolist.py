import os, json
import pandas as pd
import streamlit as st
from datetime import datetime
from typing import List, Dict

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
                    note = item.get("note", "")
                    if priority not in self.PRIORITY_LEVELS:
                        priority = "Medium"
                    if task:
                        valid_todos.append({
                            "task": task,
                            "priority": priority,
                            "due_date": due_date,
                            "note": note
                        })
                return valid_todos
        return []

    def save_todo(self, todos: List[Dict[str, str]]):
        with open(self.TODO_FILE, "w") as f:
            json.dump(todos, f, indent=2)

    def add_task(self):
        st.header("➕ Add New Task")
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
        st.header("📅 Task Calendar")
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
            "High": "#d9534f",
            "Medium": "#f0ad4e",
            "Low": "#5cb85c"
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

                    note = row.get("note", "")
                    note_html = f"<br>🗒️ <em>{note}</em>" if note else ""

                    st.markdown(f"""
                    <div style="background-color:{priority_colors[priority]}; padding:8px; border-radius:6px; margin-bottom:8px; font-size:13px; color:white;">
                        <strong>📝 {row['task']}</strong><br>
                        📆 <em>{date_str}</em>{note_html}
                    </div>
                    """, unsafe_allow_html=True)

                    with st.expander("✏️ Edit / ❌ Cancel", expanded=False):
                        new_task = st.text_input("Edit task", value=row["task"], key=f"edit_task_{i}")
                        new_priority = st.selectbox("Edit priority", self.PRIORITY_LEVELS, index=self.PRIORITY_LEVELS.index(row["priority"]), key=f"edit_priority_{i}")
                        new_due_date = st.date_input("Edit due date", value=due_date if pd.notnull(due_date) else datetime.today(), key=f"edit_date_{i}")
                        new_note = st.text_area("Edit note", value=note, key=f"edit_note_{i}")

                        if st.button("💾 Save Changes", key=f"save_{i}"):
                            todos[i] = {
                                "task": new_task.strip(),
                                "priority": new_priority,
                                "due_date": new_due_date.strftime("%Y-%m-%d"),
                                "note": new_note.strip()
                            }
                            self.save_todo(todos)
                            st.success("Task updated successfully!")

                        if st.button("❌ Delete Task", key=f"delete_{i}"):
                            todos.pop(i)
                            self.save_todo(todos)
                            st.warning("Task deleted.")
                            