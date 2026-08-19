"""
Unit tests for Printer Sender (TCP Port 9100 and Windows Spooler enumerator).
"""

from pathlib import Path
import socket
import sys
import threading
import time
import unittest

from engine.printer_sender import send_tcp_raw, list_windows_printers, PrinterCommunicationError


class TestPrinterSender(unittest.TestCase):
    def test_send_tcp_raw_success(self):
        received_data = bytearray()
        server_ready = threading.Event()

        def mock_server():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("127.0.0.1", 0))  # Bind to any free port
                port = s.getsockname()[1]
                s.listen(1)
                mock_server.port = port
                server_ready.set()

                conn, _ = s.accept()
                with conn:
                    while True:
                        chunk = conn.recv(1024)
                        if not chunk:
                            break
                        received_data.extend(chunk)

        server_thread = threading.Thread(target=mock_server, daemon=True)
        server_thread.start()
        server_ready.wait(timeout=2.0)

        payload = b"^XA^FO50,50^ADN,36,20^FDTEST LABEL^FS^XZ"
        bytes_sent = send_tcp_raw("127.0.0.1", mock_server.port, payload, timeout=2.0)
        time.sleep(0.1)

        self.assertEqual(bytes_sent, len(payload))
        self.assertEqual(bytes(received_data), payload)

    def test_send_tcp_raw_timeout(self):
        # Connecting to a non-routable IP should trigger error or timeout
        with self.assertRaises((PrinterCommunicationError, ValueError)):
            send_tcp_raw("192.0.2.1", 9100, b"TEST", timeout=0.2)

    def test_send_tcp_raw_validation(self):
        with self.assertRaises(ValueError):
            send_tcp_raw("", 9100, b"DATA")
        with self.assertRaises(ValueError):
            send_tcp_raw("127.0.0.1", 9100, b"")

    def test_list_windows_printers(self):
        if sys.platform == "win32":
            printers = list_windows_printers()
            self.assertIsInstance(printers, list)
            # Typically Windows has at least one PDF or XPS writer printer installed
            print(f"Detected {len(printers)} Windows printers: {printers}")


if __name__ == "__main__":
    unittest.main()
