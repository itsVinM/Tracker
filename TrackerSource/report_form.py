import streamlit as st
import pandas as pd
import docx
from docx import Document
from docx.shared import Inches, Pt
from docx.oxml import OxmlElement
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
import io, os, html
from datetime import date
from io import BytesIO
from PIL import Image
from st_aggrid import AgGrid, GridOptionsBuilder

# Predefined comparison fields per component type
PRODUCT_COMPARISON_FIELDS = {
    "MOSFET": {
        "materiales": ["Vds", "Id", "Rds(on)", "Qg", "Vgs(th)", "Tj(max)", "Pd(max)", "Compliance"],
        "dimensionado": ["Package", "Pin Count", "Mounting Type", "Size"]
    },
    "Diode": {
        "materiales": ["Vr", "If", "Vf", "trr", "Tj(max)", "Pd(max)", "Compliance"],
        "dimensionado": ["Package", "Pin Count", "Mounting Type", "Size"]
    },
    "Inductor": {
        "materiales": ["Inductance", "Rated Current", "Saturation Current", "DCR", "Shielding", "Compliance"],
        "dimensionado": ["Core Size", "Height", "Footprint", "Mounting Type"]
    },
    "Connector": {
        "materiales": ["Current Rating", "Voltage Rating", "Contact Resistance", "Insulation Resistance", "Compliance"],
        "dimensionado": ["Pitch", "Rows", "Contact Count", "Mounting Type"]
    },
    "DC-DC Converter": {
        "materiales": ["Input Voltage Range", "Output Voltage", "Output Current", "Efficiency", "Isolation Voltage", "Compliance"],
        "dimensionado": ["Module Size", "Height", "Pin Count", "Mounting Type"]
    },
    "Capacitor": {
        "materiales": ["Capacitance", "Voltage Rating", "ESR", "Ripple Current", "Compliance"],
        "dimensionado": ["Package", "Size", "Mounting Type"]
    },
    "Custom": {
        "materiales": [],
        "dimensionado": []
    }
}


class HomologationApp:
    def __init__(self):
        if 'report_data' not in st.session_state:
            st.session_state.report_data = {}

    def add_hyperlink(self, paragraph, url, text):
        part = paragraph.part
        r_id = part.relate_to(url, 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink', is_external=True)
        hyperlink = OxmlElement('w:hyperlink')
        hyperlink.set(qn('r:id'), r_id)
        new_run = OxmlElement('w:r')
        rPr = OxmlElement('w:rPr')
        color = OxmlElement('w:color')
        color.set(qn('w:val'), '0000FF')
        rPr.append(color)
        underline = OxmlElement('w:u')
        underline.set(qn('w:val'), 'single')
        rPr.append(underline)
        new_run.append(rPr)
        text_elem = OxmlElement('w:t')
        text_elem.text = text
        new_run.append(text_elem)
        hyperlink.append(new_run)
        paragraph._p.append(hyperlink)

    def editable_table_aggrid(self, df, key):
        gb = GridOptionsBuilder.from_dataframe(df)
        gb.configure_default_column(editable=True)
        grid_options = gb.build()
        grid_response = AgGrid(df, gridOptions=grid_options, key=key, update_mode='MODEL_CHANGED')
        return pd.DataFrame(grid_response['data'])

    def display_form(self):
        logo_path = "premium_psu_logo.png"
        data = st.session_state.report_data

        with st.expander("General Information", expanded=True):
            cols = st.columns(3)
            data['product_type'] = cols[0].selectbox("Component Type", list(PRODUCT_COMPARISON_FIELDS.keys()))
            data['doc_id'] = cols[1].text_input("Document ID", "H-2025-133")
            data['edition'] = cols[2].text_input("Edition", "2")
            cols2 = st.columns(3)
            data['codigos'] = cols2[0].text_input("Códigos", "26010206")
            data['date'] = cols2[1].date_input("Date", value=date.today()).strftime("%d.%m.%Y")
            data['author'] = cols2[2].text_input("Author", "V.Mocanu")

        with st.expander("Objecto", expanded=True):
            data['objeto'] = st.text_area("Objecto", "Se estudia la posibilidad de homologar el componente...")

        with st.expander("Motivo", expanded=True):
            data['motivo'] = st.text_area("Motivo", "Solicitante:\nMotivo:")

        with st.expander("Investigativo", expanded=True):
            data['investigativo'] = st.text_area("Investigativo", "El componente que se compraba hasta ahora es...\nG:\\Laboratori\\PLANOS - M. PRIMAS_Backup\\Data sheets")

        num_links = st.slider("Número de componentes a comparar", 1, 5, 2)
        data['datasheet_links'] = []
        for i in range(num_links):
            name = st.text_input(f"Nombre del componente {i+1}", key=f"name_{i}")
            url = st.text_input(f"Enlace del componente {i+1}", key=f"url_{i}")
            if not name.strip():
                name = f"Component_{i+1}"
            data['datasheet_links'].append({'name': name, 'url': url})

        with st.expander("Comparison Tables", expanded=True):
            comp_names = [comp['name'] for comp in data['datasheet_links']]
            materiales_df = pd.DataFrame(columns=["Field"] + comp_names)
            for field in PRODUCT_COMPARISON_FIELDS[data['product_type']]['materiales']:
                row = {"Field": field}
                for name in comp_names:
                    row[name] = ""
                materiales_df.loc[len(materiales_df)] = row
            edited_materiales_df = self.editable_table_aggrid(materiales_df, key="materiales_editor")
            data['materiales'] = edited_materiales_df.to_dict(orient="records")

            dimensionado_df = pd.DataFrame(columns=["Field"] + comp_names)
            for field in PRODUCT_COMPARISON_FIELDS[data['product_type']]['dimensionado']:
                row = {"Field": field}
                for name in comp_names:
                    row[name] = ""
                dimensionado_df.loc[len(dimensionado_df)] = row
            edited_dimensionado_df = self.editable_table_aggrid(dimensionado_df, key="dimensionado_editor")
            data['dimensionado'] = edited_dimensionado_df.to_dict(orient="records")

        with st.expander("Conclusion", expanded=True):
            data['conclusion'] = st.text_area("Conclusión", "El componente propuesto tiene un diseño con mismas dimensiones de las opciones homologadas.")

        if st.button("Generate DOCX Report"):
            self.generate_doc(data, logo_path)

    def generate_doc(self, data, logo_path):
        doc = Document()
        style = doc.styles['Normal']
        font = style.font
        font.name = 'Aptos Narrow'
        font.size = Pt(11)

        table = doc.add_table(rows=1, cols=3)
        table.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cell_logo = table.cell(0, 0)
        image = Image.open(logo_path)
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        run = cell_logo.paragraphs[0].add_run()
        run.add_picture(buffer, width=Inches(1.2))

        cell_center = table.cell(0, 1)
        p_center = cell_center.paragraphs[0]
        p_center.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_center = p_center.add_run(f"{data['product_type']}\nSolicitud de homologación\nCódigos: {data['codigos']}")
        run_center.bold = True

        cell_right = table.cell(0, 2)
        info = (
            f"Doc ID: {data['doc_id']}\n"
            f"Date: {data['date']}\n"
            f"Author: {data['author']}\n"
            f"Edition: {data['edition']}\n"
        )
        cell_right.text = info

        doc.add_paragraph()
        doc.add_heading('1. Objetivo', level=1)
        doc.add_paragraph(data['objeto'])

        doc.add_heading('2. Motivo de la solicitud', level=1)
        doc.add_paragraph(data.get('motivo', ''))

        doc.add_heading('3. Investigativo previo', level=1)
        doc.add_paragraph(data.get('investigativo', ''))

        doc.add_paragraph("Componentes:", style='Normal')
        for comp in data.get('datasheet_links', []):
            name = comp.get('name', 'Componente')
            url = comp.get('url', '')
            p = doc.add_paragraph()
            if url.strip():
                self.add_hyperlink(p, url, f"[{data['codigos']}] {name}")
            else:
                p.add_run(f"[{data['codigos']}] {name}")

        doc.add_heading('4. Comparativa parámetros', level=1)
        doc.add_heading('Materiales y características mecánicas', level=2)
        materiales = data.get("materiales", [])
        if materiales:
            keys = list(materiales[0].keys())
            table_mat = doc.add_table(rows=1, cols=len(keys))
            table_mat.style = 'Table Grid'
            for i, key in enumerate(keys):
                cell = table_mat.cell(0, i)
                cell.text = key
                cell.paragraphs[0].runs[0].bold = True
            for row_data in materiales:
                row = table_mat.add_row().cells
                for i, key in enumerate(keys):
                    row[i].text = str(row_data.get(key, ''))

        doc.add_heading('Dimensiones', level=2)
        dimensionado = data.get("dimensionado", [])
        if dimensionado:
            keys = list(dimensionado[0].keys())
            table_dim = doc.add_table(rows=1, cols=len(keys))
            table_dim.style = 'Table Grid'
            for i, key in enumerate(keys):
                cell = table_dim.cell(0, i)
                cell.text = key
                cell.paragraphs[0].runs[0].bold = True
            for row_data in dimensionado:
                row = table_dim.add_row().cells
                for i, key in enumerate(keys):
                    row[i].text = str(row_data.get(key, ''))

        doc.add_heading('6. Conclusiones', level=1)
        doc.add_paragraph(data.get("conclusion", ""))

        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)

        st.download_button(
            label="Download DOCX",
            data=buffer,
            file_name=f"Homologacion_{data.get('doc_id', 'sin_id')}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

        self.log_report(data)

    def log_report(self, data):
        log_path = "report_log.json"
        log_entry = {
            "doc_id": data.get("doc_id"),
            "date": data.get("date"),
            "author": data.get("author"),
            "component": data.get("component", ""),
            "product_type": data.get("product_type", ""),
            "timestamp": str(date.today())
        }

        if os.path.exists(log_path):
            with open(log_path, "r") as f:
                logs = json.load(f)
        else:
            logs = []

        logs.append(log_entry)

        with open(log_path, "w") as f:
            json.dump(logs, f, indent=2)