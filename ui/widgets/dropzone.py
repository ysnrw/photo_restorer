import os
from PyQt6.QtWidgets import QLabel, QFileDialog
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent

class DropZone(QLabel):
    # Membuat signal kustom
    file_dropped = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        
        self.setText("Drag & Drop Foto Hitam Putih / Buram ke Sini\nAtau Klik untuk Memilih File")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                border-radius: 8px;
                background-color: #f9f9f9;
                color: #555;
                font-size: 16px;
                padding: 20px;
            }
            QLabel:hover {
                border: 2px dashed #0078D7;
                background-color: #eef5fb;
            }
        """)
        
        # Mengaktifkan fitur drag & drop
        self.setAcceptDrops(True)
        # Mengubah kursor menjadi bentuk tangan saat diarahkan ke area ini (menandakan bisa diklik)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    # --- Fitur Klik  ---
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Membuka dialog pemilih file bawaan OS
            file_path, _ = QFileDialog.getOpenFileName(
                self, 
                "Pilih Gambar", 
                "", 
                "Gambar (*.png *.jpg *.jpeg *.webp)"
            )
            
            # Jika user memilih file (tidak membatalkan dialog)
            if file_path:
                self.file_dropped.emit(file_path)

    # --- Fitur Drag & Drop ---
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                file_path = urls[0].toLocalFile()
                ext = os.path.splitext(file_path)[1].lower()
                if ext in ['.png', '.jpg', '.jpeg', '.webp']:
                    event.acceptProposedAction()
                    self.setStyleSheet("border: 2px dashed #0078D7; background-color: #eef5fb;")
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            self.file_dropped.emit(file_path)
            
        # Kembalikan style ke semula
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                border-radius: 8px;
                background-color: #f9f9f9;
                color: #555;
                font-size: 16px;
                padding: 20px;
            }
        """)