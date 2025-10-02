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


class CommTool:
    def __init__(self):
        self.mode = None
        self.serial_port = None
        self.can_bus = None
        self.log = [] 

    def setup_rs232(self, port: str, baudrate: int):
        self.mode = "rs232"
        self.serial_port = serial.Serial(port, baudrate, timeout=1)

    def setup_can(self, channel: str, bitrate: int):
        self.mode = "can"
        self.can_bus = can.interface.Bus(channel=channel, bustype='socketcan', bitrate=bitrate)

    
    def send(self, message: str, can_id: int = 0x123):
        if self.mode == "rs232":
            self.serial_port.write(message.encode())
            log_entry = {"Direction": "TX", "Protocol": "RS232", "Message": message}
            self.log.append(log_entry)
            return f"Sent over RS232: {message}"

        elif self.mode == "can":
            data = bytes.fromhex(message)
            msg = can.Message(arbitration_id=can_id, data=data, is_extended_id=False)
            self.can_bus.send(msg)
            log_entry = {"Direction": "TX", "Protocol": "CAN", "Message": f"ID={hex(can_id)} Data={message}"}
            self.log.append(log_entry)
            return f"Sent CAN message: ID={hex(can_id)}, Data={message}"

    def read(self, timeout: int = 2):
        if self.mode == "rs232":
            self.serial_port.timeout = timeout
            response = self.serial_port.readline().decode(errors="ignore").strip()
            if response:
                self.log.append({"Direction": "RX", "Protocol": "RS232", "Message": response})
                return f"RS232 received: {response}"
            return "No RS232 response."

        elif self.mode == "can":
            msg = self.can_bus.recv(timeout)
            if msg:
                msg_str = f"ID={hex(msg.arbitration_id)} Data={msg.data.hex()}"
                self.log.append({"Direction": "RX", "Protocol": "CAN", "Message": msg_str})
                return f"CAN received: {msg_str}"
            return "No CAN message received."

    def monitor(self, duration: int = 10, filter_ids=None):
        messages = []
        start_time = time.time()

        if self.mode == "rs232":
            while time.time() - start_time < duration:
                line = self.serial_port.readline().decode(errors="ignore").strip()
                if line:
                    entry = {"Direction": "RX", "Protocol": "RS232", "Message": line}
                    self.log.append(entry)
                    messages.append(f"[RS232] {line}")

        elif self.mode == "can":
            while time.time() - start_time < duration:
                msg = self.can_bus.recv(timeout=1)
                if msg:
                    if filter_ids is None or msg.arbitration_id in filter_ids:
                        msg_str = f"ID={hex(msg.arbitration_id)} Data={msg.data.hex()}"
                        entry = {"Direction": "RX", "Protocol": "CAN", "Message": msg_str}
                        self.log.append(entry)
                        messages.append(f"[CAN] {msg_str}")
        return messages

    def close(self):
        if self.serial_port:
            self.serial_port.close()
        if self.can_bus:
            self.can_bus.shutdown()
    
    def run_streamlit(self):
        st.title("RS232 / CAN Communication Tool")

        self.mode = st.selectbox("Select Interface Mode", ["RS232", "CAN"])
        message = st.text_input("Message to Send")

        if self.mode == "rs232":
            port = st.text_input("Serial Port (e.g., COM3 or /dev/ttyUSB0)")
            baudrate = st.number_input("Baudrate", value=9600, step=100)
            read_response = st.checkbox("Read response after sending")
            monitor = st.checkbox("Monitor RS232 for 10 seconds")

            if st.button("Send"):
                try:
                    self.setup_rs232(port, baudrate)
                    st.success(self.send(message))

                    if read_response:
                        st.info(self.read())

                    if monitor:
                        logs = self.monitor(duration=10)
                        st.text_area("RS232 Monitor Log", "\n".join(logs), height=200)

                    self.close()
                except Exception as e:
                    st.error(str(e))

        elif self.mode == "can":
            channel = st.text_input("CAN Channel (e.g., can0)")
            bitrate = st.number_input("Bitrate", value=500000, step=10000)
            can_id = st.number_input("CAN ID (hex)", value=0x123, format="0x%X")
            read_response = st.checkbox("Read CAN message after sending")
            monitor = st.checkbox("Monitor CAN for 10 seconds")
            filter_ids_input = st.text_input("Filter CAN IDs (comma-separated hex, e.g., 0x123,0x456)")

            if st.button("Send"):
                try:
                    self.setup_can(channel, bitrate)
                    st.success(self.send(message, can_id=can_id))

                    if read_response:
                        st.info(self.read())

                    if monitor:
                        filter_ids = None
                        if filter_ids_input:
                            try:
                                filter_ids = [int(x.strip(), 16) for x in filter_ids_input.split(",")]
                            except ValueError:
                                st.warning("Invalid CAN ID filter format.")
                        logs = self.monitor(duration=10, filter_ids=filter_ids)
                        st.text_area("CAN Monitor Log", "\n".join(logs), height=200)

                    self.close()
                except Exception as e:
                    st.error(str(e))
        if self.log:
            st.markdown("### 📋 Message Log")
            st.dataframe(self.log, use_container_width=True)


    
