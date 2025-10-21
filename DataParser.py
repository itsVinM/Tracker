import fitz  # PyMuPDF
import docx
import re

class DatasheetParser:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.text = self._extract_text()

    def _extract_text(self):
        with fitz.open(self.pdf_path) as pdf:
            return "\n".join(page.get_text() for page in pdf)

    def convert_to_word(self, word_path):
        doc = docx.Document()
        doc.add_paragraph(self.text)
        doc.save(word_path)
        return word_path

    def parse_info(self):
        patterns = {
            "Voltage Rating": r"(Voltage Rating|VRRM|DC Blocking Voltage)[^\d]*(\d+\.?\d*)\s*V",
            "Current Rating": r"(Current Rating|IF\s*@\s*\d+°C|Continuous Forward Current)[^\d]*(\d+\.?\d*)\s*A",
            "Forward Voltage": r"(Forward Voltage|VF\s*@\s*\d+A)[^\d]*(\d+\.?\d*)\s*V",
            "Reverse Current": r"(Reverse Current|IR\s*@\s*\d+V)[^\d]*(\d+\.?\d*)\s*[µu]A",
            "Thermal Resistance": r"(Thermal Resistance|RθJC)[^\d]*(\d+\.?\d*)\s*°C/W"
        }

        info = {}
        for key, pattern in patterns.items():
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                unit = " V" if "Voltage" in key else " A" if "Current" in key else " °C/W" if "Thermal" in key else " µA"
                info[key] = match.group(2) + unit
        return info