# Centralized Factory Label Printing System (3-Layer Architecture)
- **19-08-2026**: Implementasi Phase 1: Perbaikan Bounding Box Coordinate Alignment dan Dotted Path Utilities:
  - **Akar Masalah Horizontal Shift**: `engine/binding_map.py` sebelumnya menghitung scaling factor menggunakan offset `root_box` (`target_width_px / (root_box[0] * 2 + root_box[2])`), menyebabkan penyimpangan koordinat hingga ~118px ke kanan pada elemen tengah/kanan kanvas.
  - **Perbaikan Formula Scaling**: Mengganti kalkulasi dengan rasio dimensi fisik murni:
    $$\text{Scale}_X = \frac{\text{PNG Target Width}}{\frac{\text{SVG Width (mm)}}{25.4} \times \text{DPI}}, \quad \text{Scale}_Y = \frac{\text{PNG Target Height}}{\frac{\text{SVG Height (mm)}}{25.4} \times \text{DPI}}$$
  - **Resolusi Hierarki `<text>`**: Memperbarui `_find_queryable_id()` di `engine/binding_map.py` agar memprioritaskan ancestor `<text>` daripada elemen anak `<tspan>` sehingga bounding box mencakup keseluruhan teks target.
  - **Utilitas Kontrak Dotted Path (`engine/binding_utils.py`)**: Membuat fungsi `get_json_value_at_path`, `set_json_value_at_path`, dan `validate_json_value_type` untuk manipulasi data leaf JSON secara terisolasi.
  - **Zoom-Aware Hit Testing**: Memperbarui `BoundingBox.contains_point()` dan `RasterCanvasWidget._find_box_at()` agar toleransi margin klik menyesuaikan faktor zoom viewport kanvas.
  - **Pengujian & Build**: Menambahkan pengujian komprehensif di `tests/test_coordinate_alignment.py` (total 43 test suite lulus 100%) dan me-rebuild binary `dist/label_engine.exe` serta `dist/LabelPreviewApp.exe`.

- **19-08-2026**: Perbaikan Bug Preview Canvas "Failed to render preview image (preview.png not found)" ketika Target Format bukan "all":
  - Memperbarui `engine/processor.py` agar selalu mendaftarkan path `preview.png` dan `label.svg` ke dictionary `results` (`results["png"] = png_path` dan `results["svg"] = svg_path`) pada setiap proses render, tanpa memandang target export format yang dipilih (`svg`, `zpl`, `tspl`, `ipl`, `bmp`, atau `all`).
  - Menambahkan unit test komprehensif `tests/test_processor.py` untuk memvalidasi ketersediaan `preview.png` dan artefak SVG pada berbagai opsi target format.
  - Melakukan rebuild kedua executable (`dist/label_engine.exe` dan `dist/LabelPreviewApp.exe`) serta memverifikasi eksekusi CLI dan GUI rendering preview berjalan mulus.


- **19-08-2026**: Melakukan rebuild penuh binary standalone PyInstaller untuk kedua executable:
  - `dist/label_engine.exe` (CLI Headless Engine)
  - `dist/LabelPreviewApp.exe` (Desktop Preview & Two-Way Inspection GUI)
  - Menguji eksekusi binary `label_engine.exe` dengan opsi `--help` dan integrasi rendering preview format PNG berhasil tanpa error.


- **19-08-2026**: Mengimplementasikan fitur **Interactive Two-Way Inspection Mode & Live Value Editing** antara SAP JSON Contract Tree dan Visual Thermal Canvas Preview:
  - Membuat modul `engine/binding_map.py` (`SVGInspectionEngine`) untuk mengekstrak data binding (`data-field`, `data-code`, `{{token}}`), memanggil `resvg.exe --query-all`, dan mengkalibrasi koordinat bounding box ke target raster canvas.
  - Memperbarui `gui/components/json_inspector.py` dengan tracking path hierarki, metode `select_path()`, event selection, dan inline double-click editing nilai leaf JSON.
  - Memperbarui `gui/components/raster_canvas.py` dengan vector glowing highlight overlays, translation klik kanvas ke JSON path, auto-centering viewport, dan hover indicator.
  - Memperbarui `gui/main_window.py` untuk mengintegrasikan dua arah binding JSON <-> Canvas, debounce live re-render saat nilai diedit (350ms), serta menambahkan opsi target format `svg` di `gui/components/control_panel.py`.
  - Menambahkan unit test baru di `tests/test_gui_components.py` untuk memvalidasi pemetaan bounding box dan interaktivitas seleksi/edit.


- **19-08-2026**: Membuat file `README.md` komprehensif yang mencakup ringkasan arsitektur 3-layer, fitur, struktur direktori, instalasi, panduan CLI & GUI, panduan kontrak JSON v1.1, pembuatan template SVG, dan build executable.

- **19-08-2026**: Menginisialisasi Git repository lokal, melengkapi `.gitignore`, mengonfigurasi remote origin (`https://github.com/pikidisini/JSON_LABEL_THERMAL_PRINTER_PARSER.git`), dan melakukan initial push ke branch `main`.


## Architecture Overview
Sistem pencetakan label terpusat yang memisahkan **Data (SAP ERP)**, **Layout (SVG Template)**, dan **Rendering Engine (Python Native Executable)**.

1. **Layer 1: SAP ERP (`ZMMR_LABELROL_JSON`)**
   - Menghasilkan payload Pure Data Contract v1.1 ke disk lokal operator (`C:\tslabel\in\<MATNR>_<CHARG>.json`).
   - Tidak melakukan evaluasi rule/kondisional bisnis (`has_splice`, dsb.).
2. **Layer 2: Layout Template (`assets/templates/*.svg`)**
   - File template SVG berbasis ukuran fisik (e.g. 200mm x 80mm monokrom 203 DPI).
   - Menggunakan atribut `data-field`, `data-code`, `data-barcode`, `data-qr` serta placeholder `{{field_name}}` / `{{code_name}}`.
3. **Layer 3: Rendering & Native Engine (`engine/`)**
   - `renderer.py`: Pure data injection dengan fail-fast orphan token detection.
   - `barcode_generator.py`: Pembuat modul Barcode 1D (Code128-B) & 2D (QR Code).
   - `rasterizer.py`: Konversi SVG ke 1-Bit Monochrome Bitmap (203 DPI).
   - `printer_encoders/`: Konverter bitmap ke bahasa printer native (ZPL Zebra, TSPL TSC, IPL Intermec).
   - `processor.py`: Orchestrator alur pencetakan dan ekspor preview PNG.
4. **Desktop GUI App (`gui/`)**
   - Inspector data JSON, dry-run template SVG baru, dan test print manual.

---

## Directory Structure
```
0009_JSON_SVG_LABEL/
├── PROJECT_SUMMARY.md
├── requirements.txt
├── .gitignore
├── cli.py
├── assets/
│   └── templates/
│       └── label_roll_80x200.svg
├── data_samples/
│   └── sample_roll.json
├── dist/
│   ├── label_engine.exe       (CLI headless binary untuk SAP background process)
│   └── LabelPreviewApp.exe    (Desktop Preview & Inspector GUI)
├── engine/
│   ├── __init__.py
│   ├── renderer.py
│   ├── barcode_generator.py
│   ├── bit_packer.py
│   ├── rasterizer.py
│   ├── processor.py
│   ├── printer_sender.py
│   ├── bin/
│   │   ├── .gitkeep
│   │   └── resvg.exe (binary v0.44.0)
│   └── printer_encoders/
│       ├── __init__.py
│       ├── zpl_encoder.py
│       ├── tspl_encoder.py
│       └── ipl_encoder.py
├── gui/
│   ├── __init__.py
│   ├── app.py
│   ├── main_window.py
│   └── components/
│       ├── __init__.py
│       ├── json_inspector.py
│       ├── raster_canvas.py
│       ├── control_panel.py
│       └── print_dialog.py
├── scripts/
│   └── build_executables.py
└── tests/
    ├── __init__.py
    ├── test_renderer.py
    ├── test_renderer_unittest.py
    ├── test_barcode_generator.py
    ├── test_rasterizer.py
    ├── test_encoders.py
    ├── test_printer_sender.py
    └── test_gui_components.py
```

---

## Recent Changes

### 19-08-2026 - Phase 3: Desktop Preview & Inspector GUI, RAW Printer Sender, and PyInstaller Packaging
### 19-08-2026 - Intermec IPL Standard Command Sequence Refactoring
- **Refactoring Total Protokol IPL (`engine/printer_encoders/ipl_encoder.py`)**:
  - Mengadopsi 7-tahap sekuens standar Intermec IPL yang tervalidasi:
    1. `<STX>C<ETX>` — Reset / Clear buffer
    2. `<STX>L<ETX>` — Masuk ke Label Format / Layout Mode
    3. `<STX>D<ETX>` — Masuk ke Define Mode
    4. `<STX>G1;o<x>,<y>;w<w>;h<h>;d<data_mode>;<ETX>` — Definisi Graphic Field 1 (`d0002` = uncompressed hex graphic mode)
    5. `<STX>u<HEX_STREAM_DATA><ETX>` — Upload data bitmap hex **dalam satu frame utuh** (tanpa prefix `0002` per baris dan tanpa pemecahan 640 frame)
    6. `<STX>R<ETX>` — Return / End of Definition Mode
    7. `<STX>E1;F1;<ETX>` — Form Select (E1) & Eksekusi Print (F1), diulang sesuai parameter `copies`
  - Menambahkan guard validation:
    * `width_px % 8 == 0` (mencegah desinkronisasi bit stream continuous).
    * `len(raw_bytes) == (width_px // 8) * height_px` (mencegah bitmap terpotong/overflow).
- **Verifikasi File Output & Rebuild**:
  - Berkas sampel `out/label.ipl` di-generate ulang (**256,050 bytes** murni, terverifikasi `Contains CRLF/LF: False`).
  - Unit tests lulus 100% (**31 dari 31 tests** lulus).
  - Binary executable `dist/label_engine.exe` dan `dist/LabelPreviewApp.exe` telah berhasil di-rebuild.


### 19-08-2026 - Intermec IPL Native Stream & Protocol Framing Fix
- **Eliminasi Karakter Separator CRLF (`engine/printer_encoders/ipl_encoder.py`)**:
  - Mengubah tipe kembalian fungsi `encode_ipl` dari `str` berpemisah `\n` / `\r\n` menjadi **`bytes` murni** (`b"".join(frames)`).
  - Stream frame `<STX>...<ETX>` kini dikirim tanpa karakter whitespace atau delimiter newline.
- **Perbaikan Framing Program Mode & Print Trigger**:
  - Masuk dan keluar Program Mode kini menggunakan sequence toggle identik: `<STX><ESC>P;<ETX>` (`\x02\x1bP;\x03`).
  - Menambahkan sequence trigger pencetakan IPL lengkap di akhir payload:
    * `<STX>R<ETX>` (atau `<STX><copies>R<ETX>`)
    * `<STX><RS>1<ETX>` (`RS = \x1e`)
    * `<STX><US>1<ETX>` (`US = \x1f`)
    * `<STX><ETB><ETX>` (`ETB = \x17`)
- **Graphic ID Binding Dialek IPL**:
  - Menambahkan parameter `graphic_id: str = "0002"`.
  - Definisi Graphic Field kini mengikat ID: `G1;o0,0;w<w>;h<h>;d0002;`.
  - Baris upload bitmap `u` kini diawali ID grafik: `<STX>u0002<HEX_ROW_DATA><ETX>`.
- **Processor & Binary Update**:
  - `engine/processor.py` diperbarui menulis file `.ipl` via mode binary (`wb`).
  - Berkas sampel `out/label.ipl` di-generate ulang (**260,543 bytes**, terverifikasi `Contains CRLF: False`, `Contains LF: False`).
  - Seluruh 30 unit tests lulus (`tests/test_encoders.py` lulus 100%).
  - `dist/label_engine.exe` dan `dist/LabelPreviewApp.exe` berhasil di-rebuild.


### 19-08-2026 - Intermec IPL Encoder Native Control Bytes & Exit/Print Execution Fix
- **Native ASCII Control Characters (`engine/printer_encoders/ipl_encoder.py`)**:
  - Memperbaiki representasi kontrol IPL dari string teks literal (misal `"<STX>"`, `"<ESC>"`, `"<ETX>"`) menjadi karakter byte ASCII asli:
    * `STX = "\x02"` (0x02 Start of TeXt)
    * `ETX = "\x03"` (0x03 End of TeXt)
    * `ESC = "\x1b"` (0x1B Escape)
  - Menghilangkan bug printer Intermec tidak merespon yang disebabkan oleh penerimaan data kontrol sebagai teks string biasa.
- **Payload Exit Mode & Execution Flow**:
  - Menambahkan perintah resmi **Exit Program Mode**: `f"{STX}{ESC}E{ETX}"` setelah seluruh baris bitmap `u<HEX>` dikirim.
  - Menambahkan parameter `copies: int = 1` dengan perintah eksekusi cetak di akhir payload:
    * 1 copy: `f"{STX}R{ETX}"`
    * >1 copies: `f"{STX}{copies}R{ETX}"`
- **Output Sample & Validation**:
  - Berkas sampel `out/label.ipl` telah di-generate ulang dengan urutan byte kontrol asli yang valid dan terverifikasi di header (`\x02\x1bC\x03\r\n\x02\x1bP\x03...`) dan trailer (`...\x02\x1bE\x03\r\n\x02R\x03\r\n`).
  - Seluruh 30 unit tests lulus 100% (`tests/test_encoders.py` diperbarui).
  - Berkas binary standalone `dist/label_engine.exe` dan `dist/LabelPreviewApp.exe` telah berhasil di-rebuild.


### 19-08-2026 - Save Export As Feature Implementation
- **Save Export As UI (`gui/components/control_panel.py`)**:
  - Menambahkan tombol aksi netral beraksen biru `" Save Export As... "` di sebelah tombol `" Send RAW to Printer "` dalam grup *Engine Actions*.
  - Menambahkan lightweight tooltip helper `_ToolTip` dengan teks: `"Simpan file hasil render (SVG/PNG/BMP/ZPL/TSPL/IPL) ke folder tujuan"`.
  - Mengalirkan callback `on_export_clicked` ke controller window.
- **Export File Handler (`gui/main_window.py`)**:
  - Mengimplementasikan `MainWindow.export_files()`:
    * Melakukan validasi awal ketersediaan hasil render `self.last_results`.
    * **Format Spesifik**: Jika dropdown format memilih selain `"all"` (PNG, BMP, SVG, ZPL, TSPL, IPL), dialog `filedialog.asksaveasfilename()` dibuka dengan filter ekstensi terkait dan menyalin file via `shutil.copy2()`.
    * **Format 'all'**: Jika dropdown format `"all"`, dialog `filedialog.askdirectory()` dibuka untuk memilih folder tujuan dan menyalin seluruh paket file yang digenerate sekaligus.
    * Memberikan notifikasi status sukses di status bar dan message dialog box.
- **Test & Executable Build**:
  - Seluruh 30 unit tests lulus 100%.
  - `dist/LabelPreviewApp.exe` berhasil di-rebuild dengan fitur ekspor baru.


### 19-08-2026 - Responsive Header Layout & Window Bounds Fix
- **Canvas Header Reorganization (`gui/components/raster_canvas.py`)**:
  - Menyusun ulang header kanvas menjadi container 2 sub-frame bertumpuk:
    * **Top Row**: Judul preview "Visual Thermal Print Preview (203.2 DPI)" dan Label Dimensi/Resolusi.
    * **Bottom Row**: Label instruksi "(Drag = Pan  |  Scroll = Zoom)" (kiri) dan kelompok tombol kontrol Zoom ("Fit Window", "100%", "Zoom In", "Zoom Out", persentase zoom) (kanan).
  - Menghilangkan bug terpotongnya tombol Zoom saat lebar jendela aplikasi diperkecil.
- **Window Minimum Size Enforcement (`gui/main_window.py`)**:
  - Mengubah batas minimal ukuran jendela dari `1000x600` menjadi `1024x680` via `self.minsize(1024, 680)`.
- **Validation & Build**:
  - Seluruh 30 unit tests lulus 100%.
  - `dist/LabelPreviewApp.exe` berhasil di-rebuild dengan layout responsif terbaru.


### 19-08-2026 - Canvas Interaction Update: Direct MouseWheel Zoom (No Ctrl Required)
- **Direct Scroll Zoom (`gui/components/raster_canvas.py`)**:
  - Menghapus kewajiban menekan tombol `Ctrl` saat memutar mouse wheel untuk memperbesar (*zoom in*) atau memperkecil (*zoom out*) label pada kanvas.
  - Event `<MouseWheel>` (Windows) dan `<Button-4>` / `<Button-5>` (Linux) kini langsung memicu fungsi zoom-at-cursor secara instan.
  - Mengupdate teks petunjuk pada toolbar atas kanvas menjadi `"(Drag = Pan  |  Scroll = Zoom)"`.
- **Executable Rebuild**:
  - Rebuild binary `dist/LabelPreviewApp.exe` telah berhasil diperbarui dengan interaksi baru ini.


### 19-08-2026 - Critical Bug Fix: Subprocess Hang, Timeout Handling, and Canvas Fallback/Error Messaging
- **Subprocess & Execution Hardening (`engine/rasterizer.py`)**:
  - Menambahkan parameter `timeout: float = 15.0` pada `svg_to_png()` untuk mencegah proses rasterisasi menggantung tanpa batas waktu.
  - Menambahkan `stdin=subprocess.DEVNULL` dan `creationflags=subprocess.CREATE_NO_WINDOW` (khusus Windows) untuk mencegah subprocess `resvg.exe` *hang* saat dijalankan di lingkungan PyInstaller `--windowed` (ketiadaan handle stdio/console).
  - Menambahkan exception handling eksplisit untuk `subprocess.TimeoutExpired` dan `OSError`.
- **Render Worker Module (`gui/worker.py`) & UI Thread Decoupling (`gui/main_window.py`)**:
  - Dibuat modul thread worker terdedikasi `RenderWorker` yang menjamin semua callback kegagalan/sukses selalu didispatch ke Tkinter main loop via `parent.after(0, ...)`, mencegah status UI stuck di "Rendering...".
- **Canvas Fallback Scale & Visual Error Message (`gui/components/raster_canvas.py`)**:
  - Ditambahkan konstanta fallback dimensi default `DEFAULT_FALLBACK_WIDTH = 800` dan `DEFAULT_FALLBACK_HEIGHT = 400` untuk `_fit_window()` saat canvas belum ter-render sempurna di awal pembukaan window.
  - Ditambahkan method `show_error(message: str)` yang menampilkan pesan visual berwarna merah di tengah kanvas jika berkas render hilang atau gagal dimuat.
- **Unit Test & Rebuild**:
  - Seluruh 30 unit tests lulus **100%** (termasuk unit test baru `test_raster_canvas_show_error`).
  - Rebuild executables `dist/label_engine.exe` dan `dist/LabelPreviewApp.exe` berhasil dilakukan secara bersih.


### 19-08-2026 - Phase 3 Polish: Canvas Panning, Ctrl+Wheel Zoom, Auto-Center Fit Window, Button Styling, and JSON Search Filter
- **Interactive Raster Canvas (`gui/components/raster_canvas.py`)**:
  - Implementasi *Drag & Drop Panning* (`canvas.scan_mark` / `canvas.scan_dragto` dengan cursor tangan/fleur saat digeser), setara dengan fungsi `ScrollHandDrag`.
  - Implementasi *Ctrl+MouseWheel Zooming* terpusat pada posisi koordinat kursor mouse (*zoom-at-cursor*).
  - Mode **Fit Window** (Auto Scale & Auto-Center) dijadikan sebagai tampilan standar default saat label dimuat, memastikan kanvas 1600x640 px tampil utuh di tengah tanpa terpotong di sisi kanan.
  - Auto-refit responsif saat jendela di-resize selama operator belum melakukan zoom manual.
- **Control Panel Styling (`gui/components/control_panel.py`)**:
  - Tombol **Render & Inspect** diberi styling aksen Biru primer (`bg="#0078D4"`).
  - Tombol **Send RAW to Printer** diberi styling aksen Hijau tua (`bg="#107C10"`).
  - Tombol **Template Dry-Run** tetap dengan tampilan netral standar sistem.
  - Lebar QComboBox **Format** diperlebar (`width=12`, `fill="x"`) agar opsi seperti `tspl` dan `ipl` tidak terpotong.
- **JSON Inspector Real-Time Filter (`gui/components/json_inspector.py`)**:
  - Penambahan Search / Filter Bar di atas Tree View dengan responsifitas instan saat mengetik.
  - Otomatis melakukan filter hierarkis pada key dan value data SAP JSON v1.1, dengan tombol Clear (X).
- **Unit Test Suite**:
  - Ditambahkan pengujian filter pencarian JSON pada `tests/test_gui_components.py`. Total **29 unit tests lulus 100%**.
- **PyInstaller Rebuild**:
  - Kedua executable `dist/label_engine.exe` dan `dist/LabelPreviewApp.exe` telah berhasil di-rebuild secara bersih.


- **Printer Direct Sender Engine (`engine/printer_sender.py`)**:
  - `send_tcp_raw`: Mengirim stream bytes langsung ke port RAW printer (default TCP Port 9100) menggunakan modul `socket`.
  - `list_windows_printers` & `send_windows_spooler_raw`: Menggunakan native Windows `winspool.drv` API via `ctypes` untuk membuka koneksi RAW print spooler Windows (USB / Network driverless print jobs).
  - Dilengkapi unit test `tests/test_printer_sender.py` dengan mock TCP server.
- **Desktop Preview & Inspector GUI (`gui/`)**:
  - `gui/components/json_inspector.py`: Treeview hierarkis untuk inspeksi payload data JSON dari SAP (memeriksa fields, codes, batch attributes).
  - `gui/components/raster_canvas.py`: Visual preview monokrom 1600x640 px dengan kontrol zoom (Fit Width, 100% Actual, Zoom In/Out).
  - `gui/components/control_panel.py`: Action bar untuk load JSON/SVG, pemilihan target format, dan trigger render/dry-run/print.
  - `gui/components/print_dialog.py`: Dialog modal pengujian kirim stream cetak langsung (TCP 9100 atau Windows Spooler).
  - `gui/main_window.py` & `gui/app.py`: Integrasi layout 3 panel dengan background worker thread rendering agar UI responsif.
- **Packaging Single-File Executables (`dist/`)**:
  - Dibuat skrip otomatis `scripts/build_executables.py` menggunakan PyInstaller 6.22.
  - Dihasilkan berkas executable mandiri (*portable*):
    * `dist/label_engine.exe` (~18 MB): Engine CLI untuk dipanggil SAP via background RFC/OS command.
    * `dist/LabelPreviewApp.exe` (~21 MB): Aplikasi Desktop GUI untuk IT/PPIC/Operator.
    * Berkas `engine/bin/resvg.exe`, template SVG, dan data sampel otomatis ter-bundle via PyInstaller `--add-binary` dan `sys._MEIPASS` lookup.
- **Test Suite**: Total 28 unit tests lulus 100% via pytest.

### 19-08-2026 - Phase 2: Barcode/QR Injection, 203.2 DPI Rasterizer, Bit Packing & Printer Encoders
- **Environment & Binaries**:
  - Diinisialisasi `.venv` dengan Python 3.14 + modul `pytest`, `Pillow`, `python-barcode`, `qrcode`.
  - Ditambahkan `.gitignore` untuk melindungi `.venv/`, output build, dan binary files.
  - Ditambahkan standalone binary `engine/bin/resvg.exe` (v0.44.0) untuk rasterisasi SVG cepat dan stabil tanpa ketergantungan runtime GTK Cairo.
- **Barcode & QR Generator (`engine/barcode_generator.py`)**:
  - `generate_code128_pattern`: Ekstraksi bit string modul Code128-B via `python-barcode`.
  - `generate_qr_matrix`: Ekstraksi matrix 2D modul QR Code via `qrcode`.
  - `create_barcode_svg_group` & `create_qr_svg_group`: Mengonversi pola ke elemen `<g>` berisi `<rect fill="#000000">` yang pas presisi pada bounding box.
  - `inject_barcodes_and_qr`: Otomatis mengganti elemen placeholder `<rect data-barcode="...">` dan `<rect data-qr="...">` menjadi modul vektor SVG riil.
- **Bit Packing & 1-Bit Rasterizer (`engine/bit_packer.py`, `engine/rasterizer.py`)**:
  - `svg_to_png`: Rasterisasi SVG presisi 1600 x 640 piksel pada resolusi thermal printhead 203.2 DPI (8 dots/mm) menghasilkan output byte-aligned (200 byte per baris).
  - `png_to_1bit_monochrome`: Binarisasi tanpa dither ke mode `1` (1-bit monochrome).
  - `pack_bits_per_row` & `get_raw_bitmap_data`: Bit-packing horizontal row (MSB first, 1 = Black / Burn, 0 = White) menghasilkan array bytes presisi 128,000 bytes (1600x640).
- **Native Printer Encoders (`engine/printer_encoders/`)**:
  - `zpl_encoder.py`: Konversi bitmap ke format Zebra ZPL II `^GFA` (Graphic Field ASCII Hex).
  - `tspl_encoder.py`: Konversi bitmap ke TSC TSPL2 `BITMAP` command stream.
  - `ipl_encoder.py`: Konversi bitmap ke Intermec IPL graphics command stream.
- **Orchestration & CLI (`engine/processor.py`, `cli.py`)**:
  - `process_label`: Pipeline penuh dari JSON contract -> Injeksi Data SVG -> Injeksi Barcode & QR -> Rasterisasi PNG -> Binarisasi 1-bit BMP -> Bit Packing -> Enkoding printer (ZPL, TSPL, IPL).
  - `cli.py`: Diperbarui dengan opsi `--out-dir`, `--format` (`all`, `zpl`, `tspl`, `ipl`, `png`, `bmp`, `svg`), dan `--dpi`.
- **Test Suite (`tests/`)**:
  - Ditambahkan `test_barcode_generator.py`, `test_rasterizer.py`, dan `test_encoders.py`.
  - Seluruh 22 unit test lulus 100% via pytest.

### 19-08-2026 - Phase 1: Project Setup & Pure Data SVG Injection Engine
- **Created**: Struktur folder standar modular (`engine/`, `gui/`, `assets/templates/`, `data_samples/`, `tests/`).
- **Created**: `data_samples/sample_roll.json` sesuai spesifikasi Kontrak Data v1.1 (Pure Data Contract).
- **Created**: `assets/templates/label_roll_80x200.svg` (Ukuran 200mm x 80mm, layout monokrom bersih tanpa rule logic `data-when`, dilengkapi atribut `data-field`, `data-code`, `data-barcode`, dan `data-qr`).
- **Created**: `engine/renderer.py` dengan fungsi:
  - `load_json_contract`: Validasi struktur JSON v1.1.
  - `inject_data`: Injeksi nilai placeholder `{{token}}` dengan penanganan XML entity escaping.
  - `validate_no_orphan_tokens`: Fail-fast check melempar `OrphanTokenError` jika ada placeholder tertinggal.
  - `render_svg`: Pipeline penuh injeksi dan penyimpanan berkas SVG.
- **Created**: `engine/processor.py` sebagai orkestrator pipeline.
- **Created**: Stub modul `engine/barcode_generator.py`, `engine/rasterizer.py`, dan `engine/printer_encoders/` untuk persiapan Tahap 2.
- **Created**: `cli.py` sebagai entrypoint CLI untuk background process SAP.
- **Created**: `tests/test_renderer.py` dan `tests/test_renderer_unittest.py` dengan 6 unit test lulus 100% (testing validasi kontrak, injeksi sukses, orphan tokens fail-fast, XML escaping).
- **Note on legacy files**: File `label_80x200.svg` di direktori root dipertahankan sebagai arsip draft (tidak dihapus sesuai SOP boundary project). Template acuan resmi yang dipakai engine berada di `assets/templates/label_roll_80x200.svg`.

