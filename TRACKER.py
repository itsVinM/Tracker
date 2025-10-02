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

import serial, can
import time

 
from database import *  
from todolist import *

st.set_page_config(
    page_title="PRODUCT ENGINEERING - VALIDATION",
    layout="wide",
)

import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from io import BytesIO
from datetime import datetime
import plotly.graph_objects as go
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as ReportLabImage, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import io
import os
import plotly.io as pio

# Your existing functions
def fill_database(uploaded_file):
    # This function is assumed to be defined elsewhere in your full script
    pass

# Your modified ValidationTracker class
class ValidationTracker:
    def __init__(self, data: pd.DataFrame):
        self.data = data
        self.column_config = {
            "Datasheet": st.column_config.CheckboxColumn("Datasheet", help="Is the datasheet validated?"),
            "Function": st.column_config.CheckboxColumn("Function", help="Is the functionality tested?"),
            "EMC": st.column_config.CheckboxColumn("EMC", help="Is the EMC tested?")
        }

    def display_editor_with_forms(self):
        """
        Displays a table-like structure with a 'Details' button for each row.
        Clicking the button will open a detailed form for that row.
        """
        
        # Display header
        col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])
        with col1: st.markdown("**Reference**")
        with col2: st.markdown("**Function**")
        with col3: st.markdown("**EMC**")
        with col4: st.markdown("**Datasheet**")
        with col5: st.markdown("**Actions**")

        # Display data rows with a button
        for index, row in self.data.iterrows():
            col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])
            with col1: st.write(row['Reference'])
            with col2: st.write(row['Function'])
            with col3: st.write(row['EMC'])
            with col4: st.write(row['Datasheet'])
            with col5:
                if st.button('Details', key=f"details_button_{index}"):
                    st.session_state['editing_row_id'] = index
                    st.session_state['show_details_form'] = True
            
        # Display the form if a button was clicked
        if st.session_state.get('show_details_form', False):
            self.display_details_form(st.session_state['editing_row_id'])

    def display_details_form(self, row_id: int):
        """
        Renders a detailed form for EMC and Homologation.
        """
        row_data = self.data.loc[row_id]
        
        with st.container(border=True):
            st.subheader(f"Detailed Validation for: {row_data['Reference']}")
            
            with st.form(key=f'details_form_{row_id}'):
                st.write("### EMC Sub-tests")
                emc_radiated = st.checkbox('Radiated Emissions', value=row_data.get('EMC - Radiated', False))
                emc_conducted = st.checkbox('Conducted Emissions', value=row_data.get('EMC - Conducted', False))
                
                st.write("### Homologation Details")
                homologation_region = st.text_input('Region', value=row_data.get('Homologation - Region', ''))
                homologation_cert_id = st.text_input('Certificate ID', value=row_data.get('Homologation - Cert ID', ''))
                homologation_exp_date = st.date_input('Expiry Date', value=pd.to_datetime(row_data.get('Homologation - Expiry Date', None)))

                if st.form_submit_button("Save Details"):
                    self.data.loc[row_id, 'EMC - Radiated'] = emc_radiated
                    self.data.loc[row_id, 'EMC - Conducted'] = emc_conducted
                    self.data.loc[row_id, 'Homologation - Region'] = homologation_region
                    self.data.loc[row_id, 'Homologation - Cert ID'] = homologation_cert_id
                    self.data.loc[row_id, 'Homologation - Expiry Date'] = homologation_exp_date

                    st.session_state['show_details_form'] = False
                    st.experimental_rerun()

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
    
    def generate_pdf_report(self):
        """
        Generates a PDF report with charts and data tables.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()

        story.append(Paragraph("Validation and Compliance Report", styles['Title']))
        story.append(Spacer(1, 12))
        story.append(Paragraph(f"Report Date: {datetime.today().strftime('%B %d, %Y')}", styles['Normal']))
        story.append(Spacer(1, 24))

        fig = self.display_charts()
        chart_image_bytes = pio.to_image(fig, format='png')
        story.append(ReportLabImage(io.BytesIO(chart_image_bytes), width=400, height=300))
        story.append(Spacer(1, 24))

        df_to_report = self.data.reset_index(drop=True)
        data = [df_to_report.columns.values.tolist()] + df_to_report.values.tolist()
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(table)
        
        doc.build(story)
        
        st.download_button(
            label="📥 Download PDF Report",
            data=buffer.getvalue(),
            file_name=f"Validation_Report_{datetime.today().strftime('%Y%m%d')}.pdf",
            mime="application/pdf"
        )

    def display_charts(self):
        df = self.data

        # Count Checked and Unchecked for each category
        datasheet_counts = df['Datasheet'].value_counts().rename({True: 'Checked', False: 'Unchecked'})
        function_counts = df['Function'].value_counts().rename({True: 'Checked', False: 'Unchecked'})
        emc_counts = df['EMC'].value_counts().rename({True: 'Checked', False: 'Unchecked'})

        fig = go.Figure()
        fig.add_trace(go.Bar(name='Datasheet Checked', x=['Datasheet'], y=[datasheet_counts.get('Checked', 0)], marker_color='lightgreen'))
        fig.add_trace(go.Bar(name='Datasheet Unchecked', x=['Datasheet'], y=[datasheet_counts.get('Unchecked', 0)], marker_color='salmon'))
        fig.add_trace(go.Bar(name='Function Checked', x=['Function'], y=[function_counts.get('Checked', 0)], marker_color='lightgreen'))
        fig.add_trace(go.Bar(name='Function Unchecked', x=['Function'], y=[function_counts.get('Unchecked', 0)], marker_color='salmon'))
        fig.add_trace(go.Bar(name='EMC Checked', x=['EMC'], y=[emc_counts.get('Checked', 0)], marker_color='lightgreen'))
        
        fig.update_layout(
            title="Validation Summary",
            barmode='group',
            xaxis_title="Category",
            yaxis=dict(title='Validation Counts'),
            width=800,
            height=600
        )
        return fig
    
def project_tracker():
    # Initialize session state for forms
    if 'show_details_form' not in st.session_state:
        st.session_state['show_details_form'] = False
    if 'editing_row_id' not in st.session_state:
        st.session_state['editing_row_id'] = None
    if 'data' not in st.session_state:
        st.session_state['data'] = pd.DataFrame() # Or load from your database
        
    with st.sidebar:
        st.markdown("📊 Validation tracker by Vincentiu")
        uploaded_file = st.file_uploader("Choose an Excel file", type="xlsx")
        debug_mode = st.checkbox("🔧 Developer Mode", value=False)
        if uploaded_file:
            fill_database(uploaded_file)
            st.session_state['data'] = pd.read_excel(uploaded_file)
            st.success("Database has been populated successfully.")

    tab1, tab2 = st.tabs(["📊 Validation request", "📥Todo!"])

    with tab1:
        # Load data from session state
        tracker = ValidationTracker(st.session_state['data'])
        but1, but2, but3 = st.columns(3, gap="small")

        # Now calling the new display method
        tracker.display_editor_with_forms()

        # Moved display_charts inside a function to return the figure
        # The PDF generation function will call this internally
        st.plotly_chart(tracker.display_charts(), use_container_width=True)

        with but1:
            if st.button("💾 Save Changes"):
                tracker.save_changes(st.session_state['data'])
        with but2:
            tracker.download_backup(st.session_state['data'])
        
        # New buttons for report generation
        with but3:
            if st.button("📄 Generate PDF Report"):
                tracker.generate_pdf_report()
    
    

    with tab2:
        todo = TodoManager()
        with st.expander("Add task"):
            todo.add_task()
        todo.display_calendar()


project_tracker()