import os
import shutil
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QStackedLayout, 
                             QPushButton, QHBoxLayout, QProgressBar, QLabel, QFileDialog)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QGuiApplication
from ui.widgets.dropzone import DropZone
from ui.widgets.before_after import BeforeAfterWidget
from engine.pipeline import AIPipelineWorker 

class MainWindow(QMainWindow):
    PAGE_DROPZONE = 0
    PAGE_PREVIEW = 1
    PAGE_LOADING = 2
    PAGE_RESULT = 3

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Restorer - Ultimate Pipeline")

        screen = QGuiApplication.primaryScreen().availableGeometry()

        window_width = screen.width() // 2
        window_height = screen.height() // 2

        self.resize(window_width, window_height)

        margin = 40 
        
        x_pos = screen.x() + margin
        y_pos = screen.y() + margin
        self.move(x_pos, y_pos)

        self.current_input_path = None
        self.current_output_path = None

        # =========================================================================
        # LOAD EXTERNAL STYLESHEET (styles.qss)
        # =========================================================================
        ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        qss_path = os.path.join(ROOT_DIR, 'assets', 'styles.qss')
        
        if os.path.exists(qss_path):
            with open(qss_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
            print("[SUCCESS] styles.qss berhasil dimuat.")
        else:
            print(f"[WARN] File styles.qss tidak ditemukan di: {qss_path}")

        # Container Utama
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Stacked Layout
        self.stacked_layout = QStackedLayout()
        main_layout.addLayout(self.stacked_layout)

        # Inisialisasi Halaman
        self.setup_dropzone_page()
        self.setup_preview_page()
        self.setup_loading_page()
        self.setup_result_page()

    def setup_dropzone_page(self):
        self.drop_zone = DropZone()
        # Mengarahkan ke Preview, bukan langsung proses
        self.drop_zone.file_dropped.connect(self.show_preview_page)
        self.stacked_layout.addWidget(self.drop_zone)

    def setup_preview_page(self):
        self.preview_page = QWidget()
        layout = QVBoxLayout(self.preview_page)
        layout.setSpacing(20)

        title = QLabel("Preview Foto")
        title.setObjectName("previewTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.preview_image_label = QLabel()
        self.preview_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_image_label.setObjectName("previewImageContainer")
        
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(15)
        
        self.btn_cancel_preview = QPushButton("Ganti Foto")
        self.btn_cancel_preview.setObjectName("btnCancel")
        self.btn_cancel_preview.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.btn_start_enhance = QPushButton("Mulai Enhance HD")
        self.btn_start_enhance.setObjectName("btnEnhance")
        self.btn_start_enhance.setCursor(Qt.CursorShape.PointingHandCursor)
        
        actions_layout.addStretch()
        actions_layout.addWidget(self.btn_cancel_preview)
        actions_layout.addWidget(self.btn_start_enhance)
        actions_layout.addStretch()

        layout.addWidget(title)
        layout.addWidget(self.preview_image_label, stretch=1)
        layout.addLayout(actions_layout)
        
        self.stacked_layout.addWidget(self.preview_page)

        # Connections
        self.btn_cancel_preview.clicked.connect(lambda: self.stacked_layout.setCurrentIndex(self.PAGE_DROPZONE))
        self.btn_start_enhance.clicked.connect(self.start_pipeline)

    def setup_loading_page(self):
        self.loading_page = QWidget()
        layout = QVBoxLayout(self.loading_page)
        
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.status_label = QLabel("Menyiapkan Mesin AI...")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(30)
        self.progress_bar.setFixedWidth(500)
        
        center_layout.addWidget(self.status_label)
        center_layout.addSpacing(20)
        center_layout.addWidget(self.progress_bar, alignment=Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(center_widget)
        self.stacked_layout.addWidget(self.loading_page)

    def setup_result_page(self):
        self.result_page = QWidget()
        layout = QVBoxLayout(self.result_page)
        layout.setSpacing(20)
        
        self.slider_widget = BeforeAfterWidget()
        layout.addWidget(self.slider_widget, stretch=1)
        
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(15)
        
        self.btn_back = QPushButton("Proses Foto Lain")
        self.btn_back.setObjectName("btnBack")
        self.btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.btn_save = QPushButton("Simpan Hasil Final HD")
        self.btn_save.setObjectName("btnSave")
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        
        actions_layout.addStretch()
        actions_layout.addWidget(self.btn_back)
        actions_layout.addWidget(self.btn_save)
        actions_layout.addStretch()
        
        layout.addLayout(actions_layout)
        self.stacked_layout.addWidget(self.result_page)
        
        self.btn_back.clicked.connect(lambda: self.stacked_layout.setCurrentIndex(self.PAGE_DROPZONE))
        self.btn_save.clicked.connect(self.save_file)

    # =========================================================================
    # CORE LOGIC & FILE MANAGEMENT
    # =========================================================================
    def show_preview_page(self, file_path):
        self.current_input_path = file_path
        
        pixmap = QPixmap(file_path)
        scaled_pixmap = pixmap.scaled(
            800, 600, 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        )
        self.preview_image_label.setPixmap(scaled_pixmap)
        
        self.stacked_layout.setCurrentIndex(self.PAGE_PREVIEW)

    def start_pipeline(self):
        if not self.current_input_path: return

        self.stacked_layout.setCurrentIndex(self.PAGE_LOADING)
        self.progress_bar.setValue(0)
        
        self.worker = AIPipelineWorker(self.current_input_path)
        self.worker.progress_updated.connect(self.handle_progress)
        self.worker.process_finished.connect(self.handle_finished)
        self.worker.start()

    def handle_progress(self, value, text):
        self.progress_bar.setValue(value)
        self.status_label.setText(text)

    def handle_finished(self, original, restored):
        self.current_output_path = restored
        self.slider_widget.set_images(original, restored)
        self.stacked_layout.setCurrentIndex(self.PAGE_RESULT)

    def save_file(self):
        if not self.current_output_path: return
        
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Simpan Foto Sempurna", "Foto_Restorasi_HD.jpg", "Images (*.jpg *.png)"
        )
        
        if save_path:
            # 1. Pindahkan file dari temp ke lokasi yang dipilih user
            shutil.copy(self.current_output_path, save_path)
            
            # 2. Hapus file temp untuk mencegah storage leak (Garbage Collection)
            try:
                if os.path.exists(self.current_output_path):
                    os.remove(self.current_output_path)
                    print(f"[CLEANUP] File sementara dihapus: {self.current_output_path}")
            except Exception as e:
                print(f"[WARN] Gagal menghapus file sementara: {e}")
            
            # 3. Reset state dan kembali ke halaman awal
            self.current_output_path = None
            self.current_input_path = None
            self.stacked_layout.setCurrentIndex(self.PAGE_DROPZONE)

    # =========================================================================
    # EVENT LISTENER: SAAT APLIKASI DITUTUP (TOMBOL X)
    # =========================================================================
    def closeEvent(self, event):
        """Fungsi bawaan PyQt yang mendeteksi saat user menutup jendela aplikasi."""
        print("\n[SISTEM] Menutup aplikasi, melakukan pembersihan memori (Garbage Collection)...")
        
        # 1. Tentukan path folder result_image
        ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        temp_dir = os.path.join(ROOT_DIR, 'result_image')
        
        # 2. Hapus SEMUA file yang tersisa di dalam folder result_image
        if os.path.exists(temp_dir):
            for file_name in os.listdir(temp_dir):
                file_path = os.path.join(temp_dir, file_name)
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        print(f"[CLEANUP EXIT] Berhasil menghapus file sampah: {file_name}")
                except Exception as e:
                    print(f"[WARN] Gagal menghapus {file_name}: {e}")
        
        # 3. Hentikan proses AI jika user iseng menutup aplikasi saat sedang loading
        if hasattr(self, 'worker') and self.worker.isRunning():
            print("[SISTEM] Mematikan paksa mesin AI yang sedang berjalan...")
            self.worker.terminate()
            self.worker.wait()
            
        # 4. Izinkan aplikasi untuk benar-benar ditutup
        event.accept()