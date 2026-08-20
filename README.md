# 🏷️ JSON Label Thermal Printer Parser & Engine

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Architecture](https://img.shields.io/badge/Architecture-3--Layer%20Decoupled-orange.svg)](#architecture-overview)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](#testing)

Sistem rendering dan pencetakan label termal pabrik terpusat (*Centralized Factory Thermal Label System*) berbasis **3-Layer Decoupled Architecture**. Memisahkan secara ketat antara **Data Contract (SAP ERP)**, **Visual Layout (SVG Vector Template)**, dan **Native Rendering & Rasterization Engine (Python)**.

---

## 📑 Daftar Isi

- [Arsitektur Sistem (3-Layer Architecture)](#-arsitektur-sistem-3-layer-architecture)
- [Fitur Utama](#-fitur-utama)
- [Struktur Direktori](#-struktur-direktori)
- [Instalasi & Prasyarat](#-instalasi--prasyarat)
- [Penggunaan CLI (Command Line Interface)](#-penggunaan-cli-command-line-interface)
- [Aplikasi Desktop GUI (Preview & Inspector)](#-aplikasi-desktop-gui-preview--inspector)
- [Dukungan Bahasa Printer Thermal](#-dukungan-bahasa-printer-thermal)
- [Format Kontrak Data JSON (v1.1)](#-format-kontrak-data-json-v11)
- [Panduan Pembuatan Template SVG](#-panduan-pembuatan-template-svg)
- [Build Standalone Executable (.exe)](#-build-standalone-executable-exe)
- [Pengujian Unit (Unit Testing)](#-pengujian-unit-unit-testing)

---

## 🏛️ Arsitektur Sistem (3-Layer Architecture)

```
+-------------------------------------------------------------+
| Layer 1: SAP ERP (ABAP / RFC)                               |
| - Program: ZMMR_LABELROL_JSON                               |
| - Pure Data Contract JSON (No business evaluation/logic)    |
+------------------------------+------------------------------+
                               | Injeksi Data JSON
                               v
+-------------------------------------------------------------+
| Layer 2: Vector Layout Template (SVG)                       |
| - Standar Industri: 200mm x 80mm @ 203.2 DPI (1600x640 px)  |
| - Tokens: {{token}}, data-field, data-barcode, data-qr      |
+------------------------------+------------------------------+
                               | Vektorisasi & Rasterisasi
                               v
+-------------------------------------------------------------+
| Layer 3: Native Rendering & Printing Engine                 |
| - resvg / Pillow: 1-Bit Monochrome Binarization (MSB first) |
| - Native Encoders: ZPL (Zebra), TSPL (TSC), IPL (Intermec)  |
| - RAW Windows Spooler / TCP Socket Direct Sender            |
+-------------------------------------------------------------+
```

---

## ✨ Fitur Utama

- **Zero-Logic Decoupled Injection**: Template SVG bersifat murni visual layout, data dinamis diinjeksikan secara terpisah via JSON Contract v1.1.
- **Fail-Fast Orphan Token Detection**: Mencegah label tercetak cacat dengan melempar error jika terdapat placeholder `{{...}}` yang tidak terisi.
- **Vector Native Barcode & QR Generator**:
  - **1D Barcode**: Code 128 (Subtype B) presisi piksel sesuai bounding box.
  - **2D Barcode**: QR Code (Model 2, Error Correction Level M).
- **Sub-pixel 1-Bit Monochrome Rasterizer**:
  - Konversi ke monokrom murni (1 bit per piksel, 8 piksel per byte, MSB first) pada resolusi **203.2 DPI (8 dots/mm)**.
  - Byte-aligned output horizontal (200 bytes per baris).
- **Multi-Brand Thermal Printer Encoders**:
  - **Zebra (ZPL II)**: Menggunakan perintah `^GFA` (Graphic Field ASCII Hex Compression).
  - **TSC (TSPL2)**: Menggunakan binary stream `BITMAP X,Y,width_bytes,height,mode,bitmap_data`.
  - **Intermec / Honeywell (IPL)**: Menggunakan 7-tahap sekuens standar Intermec Graphics Layout Mode (`<STX>G1;...`).
- **Direct Hardware Spooler**: Kirim perintah native langsung ke Windows Print Spooler (RAW datatype) atau TCP Raw Socket (Port 9100).
- **Interactive Desktop GUI**: Preview SVG realtime, inspeksi tree JSON, zooming, pan canvas, dan dialog cetak.
- **Headless Standalone Binaries**: Dapat dibuild menjadi file `.exe` mandiri tanpa dependensi runtime Python di mesin operator/SAP server.

---

## 📁 Struktur Direktori

```
JSON_LABEL_THERMAL_PRINTER_PARSER/
├── assets/templates/label_roll_80x200.svg # Master SVG Template 200x80mm
├── data_samples/sample_roll.json          # Contoh Payload JSON SAP v1.1
├── engine/
│   ├── barcode_generator.py      # Modul generator barcode 1D & QR Code
│   ├── bit_packer.py             # Modul bit-packing 1-bit monochrome
│   ├── rasterizer.py             # Modul rasterisasi SVG via resvg-cli
│   ├── renderer.py               # Injeksi data contract & token validator
│   ├── processor.py              # Pipeline orchestrator
│   ├── printer_sender.py         # RAW Windows Spooler & TCP Socket sender
│   ├── bin/resvg.exe             # Standalone fast SVG rasterizer v0.44.0
│   └── printer_encoders/
│       ├── zpl_encoder.py        # Zebra ZPL II encoder (^GFA)
│       ├── tspl_encoder.py       # TSC TSPL2 encoder (BITMAP)
│       └── ipl_encoder.py        # Intermec IPL encoder (<STX>G1;...)
├── gui/
│   ├── app.py                    # Entry point aplikasi GUI Desktop
│   ├── main_window.py            # Window utama (PySide6)
│   └── components/               # Komponen GUI (Canvas, Inspector, Dialog)
├── scripts/build_executables.py  # Script PyInstaller otomatis
├── tests/                        # Suite unit testing lengkap (26+ test cases)
├── cli.py                        # Entry point CLI headless
└── requirements.txt              # Dependensi Python
```

---

## 🚀 Instalasi & Prasyarat

### 1. Prasyarat Sistem
- **OS**: Windows 10 / 11 / Windows Server
- **Python**: Versi 3.10 atau lebih baru

### 2. Setup Virtual Environment
```bash
# Clone repository
git clone https://github.com/pikidisini/JSON_LABEL_THERMAL_PRINTER_PARSER.git
cd JSON_LABEL_THERMAL_PRINTER_PARSER

# Buat virtual environment
python -m venv .venv

# Aktivasi virtual environment (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Install dependensi
pip install -r requirements.txt
```

---

## 💻 Penggunaan CLI (Command Line Interface)

Script `cli.py` digunakan untuk eksekusi headless (otomatisasi via SAP Background Job, Task Scheduler, atau integrasi backend):

```bash
# Render ke semua format (SVG, PNG, BMP, PDF, ZPL, TSPL, IPL)
python cli.py --json data_samples/sample_roll.json --template assets/templates/label_roll_80x200.svg --out-dir out

# Render khusus format PDF dokumen terkompresi
python cli.py --json data_samples/sample_roll.json --template assets/templates/label_roll_80x200.svg --format pdf

# Render khusus format ZPL untuk printer Zebra
python cli.py --json data_samples/sample_roll.json --template assets/templates/label_roll_80x200.svg --format zpl

# Render khusus format TSPL untuk printer TSC
python cli.py --json data_samples/sample_roll.json --template assets/templates/label_roll_80x200.svg --format tspl

# Render khusus format IPL untuk printer Intermec
python cli.py --json data_samples/sample_roll.json --template assets/templates/label_roll_80x200.svg --format ipl
```

### Parameter Opsi CLI:
| Parameter | Tipe | Wajib | Keterangan |
|---|---|---|---|
| `--json` | Path | Ya | Lokasi berkas input JSON contract |
| `--template` | Path | Ya | Lokasi berkas master SVG template |
| `--out-dir` | Path | Tidak | Direktori output hasil render (Default: `out/`) |
| `--format` | String | Tidak | Pilihan: `all`, `zpl`, `tspl`, `ipl`, `pdf`, `png`, `bmp`, `svg` (Default: `all`) |
| `--dpi` | Float | Tidak | Resolusi printhead thermal (Default: `203.2`) |

---

## 🖥️ Aplikasi Desktop GUI (Preview & Inspector)

Untuk operator, designer template, atau tim QA yang ingin melakukan review visual dan tes cetak manual:

```bash
python -m gui.app
```

### Fitur Antarmuka:
1. **JSON Inspector**: Memuat dan memvalidasi struktur data secara interaktif.
2. **Dynamic Preview Canvas**: Menampilkan hasil rasterisasi pixel-perfect dengan kemampuan Zoom (Scroll / Slider) dan Pan Canvas.
3. **Print Dialog**: Mengirim payload native (ZPL / TSPL / IPL) langsung ke printer Windows Spooler lokal/jaringan atau via TCP/IP Raw Port 9100.

---

## 🖨️ Dukungan Bahasa Printer & Format Ekspor

| Bahasa / Format | Produsen / Tipe | Format Perintah / Dokumen | Modus Data / Kompresi |
|---|---|---|---|
| **ZPL II** | Zebra Technologies | `^XA ... ^GFA,...^FS ... ^XZ` | ASCII Hexadecimal |
| **TSPL2** | TSC / POSTEK | `SIZE ... BITMAP X,Y,W,H,0,<raw_bytes> ... PRINT 1` | Binary 1-Bit Stream |
| **IPL** | Intermec / Honeywell | `<STX>L<ETX> ... <STX>G1;...;<data><ETX> ... <STX>Q1;1<ETX>` | Graphic Field Layout |
| **PDF** | Portable Document Format | Single-page standard vector wrapper | CCITT Group 4 / Flate Lossless (< 100 KB) |
| **BMP** | Windows Bitmap | 1-bit monochrome uncompressed | Byte-aligned row packing |
| **PNG / SVG** | Preview & Vector | Standard visual raster & SVG DOM | Full dynamic resolution preview |

---

## 📋 Format Kontrak Data JSON (v1.1)

Format JSON yang dihasilkan oleh Layer 1 SAP (`ZMMR_LABELROL_JSON`):

```json
{
  "contract_version": "1.1",
  "metadata": {
    "generated_at": "2026-08-19T10:00:00Z",
    "source_system": "SAP_ECC_PRD"
  },
  "fields": {
    "material_number": "RM-ST-00129",
    "material_description": "Cold Rolled Steel Coil 1.2mm x 1200mm",
    "batch_number": "B260819001",
    "gross_weight": "2,450.50 KG",
    "net_weight": "2,430.00 KG",
    "production_date": "19.08.2026",
    "operator_id": "OP-9821"
  },
  "codes": {
    "barcode_batch": "B260819001",
    "qr_traceability": "https://trace.company.com/label?batch=B260819001&mat=RM-ST-00129"
  }
}
```

---

## 🎨 Panduan Pembuatan Template SVG

Buat template menggunakan software vector seperti **Adobe Illustrator**, **Inkscape**, atau code editor:

1. **Ukuran Canvas**: Sesuaikan dengan ukuran fisik label (contoh: `width="200mm" height="80mm" viewBox="0 0 1600 640"`).
2. **Text Field**: Gunakan placeholder `{{field_name}}` di dalam tag `<text>`:
   ```xml
   <text x="50" y="100" font-family="Arial" font-size="28">{{material_number}}</text>
   ```
3. **1D Barcode Placeholder**: Tambahkan elemen `<rect>` dengan atribut `data-barcode`:
   ```xml
   <rect x="50" y="200" width="600" height="120" data-barcode="barcode_batch" fill="none" />
   ```
4. **QR Code Placeholder**: Tambahkan elemen `<rect>` dengan atribut `data-qr`:
   ```xml
   <rect x="1300" y="200" width="200" height="200" data-qr="qr_traceability" fill="none" />
   ```

---

## 📦 Build Standalone Executable (.exe)

Proyek ini menyediakan automation script untuk mem-bundle aplikasi menjadi standalone `.exe` menggunakan PyInstaller:

```bash
python scripts/build_executables.py
```

File output binary akan tersedia di direktori `dist/`:
- `dist/label_engine.exe`: Headless CLI executable untuk integrasi SAP / background worker.
- `dist/LabelPreviewApp.exe`: Desktop GUI executable untuk operator.

---

## 🧪 Pengujian Unit (Unit Testing)

Jalankan seluruh rangkaian unit test otomatis menggunakan `pytest`:

```bash
pytest -v
```

Hasil test mencakup:
- ✅ **Renderer Test**: Validasi kontrak JSON v1.1, injeksi teks, escaping karakter XML, dan deteksi token orphan.
- ✅ **Barcode & QR Test**: Validasi Code128 pattern dan QR Code matrix injection.
- ✅ **Rasterizer Test**: Validasi ukuran 1600x640, binarisasi monokrom 1-bit, dan bit-packing MSB first.
- ✅ **Encoders Test**: Validasi format output stream ZPL, TSPL, dan IPL.
- ✅ **Printer Sender Test**: Validasi komunikasi RAW spooler dan TCP socket mock.
- ✅ **GUI Components Test**: Validasi lifecycle widget PySide6 dan worker thread.

---

## 📄 Lisensi

Proyek ini dilisensikan di bawah [MIT License](LICENSE).

