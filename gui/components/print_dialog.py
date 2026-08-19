"""
Print Dialog Component.
Allows selecting between direct TCP Socket 9100 or Windows Spooler and sending RAW print streams.
"""

from pathlib import Path
from typing import Dict, Optional
import tkinter as tk
from tkinter import ttk, messagebox

from engine.printer_sender import send_tcp_raw, send_windows_spooler_raw, list_windows_printers, PrinterCommunicationError


class PrintSenderDialog(tk.Toplevel):
    """Modal dialog for sending generated label stream directly to printer."""

    def __init__(self, parent: tk.Widget, generated_files: Dict[str, Path]):
        super().__init__(parent)
        self.title("Send RAW to Thermal Printer")
        self.geometry("520x400")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.generated_files = generated_files
        self.var_protocol = tk.StringVar(value="tcp")  # 'tcp' or 'spooler'
        self.var_format = tk.StringVar(value="zpl")
        self.var_ip = tk.StringVar(value="192.168.1.100")
        self.var_port = tk.StringVar(value="9100")
        self.var_printer_name = tk.StringVar()

        self._build_ui()

    def _build_ui(self):
        pad_opts = {"padx": 10, "pady": 6}

        # 1. Format Selector
        fmt_frame = ttk.LabelFrame(self, text="1. Select Printer Command Stream", padding=8)
        fmt_frame.pack(fill="x", **pad_opts)

        available_formats = [f for f in ["zpl", "tspl", "ipl"] if f in self.generated_files]
        if not available_formats:
            available_formats = ["zpl"]
        self.var_format.set(available_formats[0])

        for fmt in available_formats:
            ttk.Radiobutton(
                fmt_frame,
                text=f"{fmt.upper()} ({self.generated_files.get(fmt, Path('N/A')).name})",
                variable=self.var_format,
                value=fmt,
            ).pack(side="left", padx=10)

        # 2. Connection Method
        conn_frame = ttk.LabelFrame(self, text="2. Select Connection Target", padding=8)
        conn_frame.pack(fill="both", expand=True, **pad_opts)

        # Option A: Direct Network TCP
        rb_tcp = ttk.Radiobutton(
            conn_frame,
            text="Direct Network Socket (TCP RAW)",
            variable=self.var_protocol,
            value="tcp",
            command=self._toggle_mode,
        )
        rb_tcp.grid(row=0, column=0, columnspan=2, sticky="w", pady=2)

        ttk.Label(conn_frame, text="Printer IP:").grid(row=1, column=0, sticky="w", padx=15, pady=2)
        self.entry_ip = ttk.Entry(conn_frame, textvariable=self.var_ip, width=20)
        self.entry_ip.grid(row=1, column=1, sticky="w", pady=2)

        ttk.Label(conn_frame, text="Port:").grid(row=2, column=0, sticky="w", padx=15, pady=2)
        self.entry_port = ttk.Entry(conn_frame, textvariable=self.var_port, width=10)
        self.entry_port.grid(row=2, column=1, sticky="w", pady=2)

        # Option B: Windows Spooler
        rb_spooler = ttk.Radiobutton(
            conn_frame,
            text="Windows Print Spooler (USB / Driverless RAW)",
            variable=self.var_protocol,
            value="spooler",
            command=self._toggle_mode,
        )
        rb_spooler.grid(row=3, column=0, columnspan=2, sticky="w", pady=(10, 2))

        ttk.Label(conn_frame, text="Installed Printer:").grid(row=4, column=0, sticky="w", padx=15, pady=2)
        printers = list_windows_printers()
        if printers:
            self.var_printer_name.set(printers[0])
        self.cb_printers = ttk.Combobox(
            conn_frame,
            textvariable=self.var_printer_name,
            values=printers,
            state="readonly",
            width=30,
        )
        self.cb_printers.grid(row=4, column=1, sticky="w", pady=2)

        # Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", side="bottom", padx=10, pady=10)

        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="right", padx=4)
        ttk.Button(btn_frame, text=" SEND RAW STREAM ", command=self._do_send).pack(side="right", padx=4)

        self._toggle_mode()

    def _toggle_mode(self):
        is_tcp = self.var_protocol.get() == "tcp"
        self.entry_ip.config(state="normal" if is_tcp else "disabled")
        self.entry_port.config(state="normal" if is_tcp else "disabled")
        self.cb_printers.config(state="readonly" if not is_tcp else "disabled")

    def _do_send(self):
        fmt = self.var_format.get()
        file_path = self.generated_files.get(fmt)
        if not file_path or not file_path.is_file():
            messagebox.showerror("Error", f"Stream file for format '{fmt}' not found.")
            return

        with open(file_path, "rb") as f:
            data = f.read()

        try:
            if self.var_protocol.get() == "tcp":
                ip = self.var_ip.get().strip()
                port = int(self.var_port.get().strip())
                bytes_sent = send_tcp_raw(host=ip, port=port, data=data, timeout=4.0)
                messagebox.showinfo(
                    "Success",
                    f"Successfully sent {bytes_sent} bytes ({fmt.upper()}) to printer at {ip}:{port}",
                )
            else:
                printer_name = self.var_printer_name.get()
                if not printer_name:
                    messagebox.showwarning("Warning", "Please select a Windows printer.")
                    return
                bytes_sent = send_windows_spooler_raw(printer_name=printer_name, data=data)
                messagebox.showinfo(
                    "Success",
                    f"Successfully spooled {bytes_sent} bytes ({fmt.upper()}) to Windows printer '{printer_name}'",
                )
            self.destroy()
        except PrinterCommunicationError as e:
            messagebox.showerror("Printer Communication Failed", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to send data: {e}")
