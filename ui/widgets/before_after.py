from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QPixmap, QColor, QPen
from PyQt6.QtCore import Qt, QRect

class BeforeAfterWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.pixmap_before = None
        self.pixmap_after = None
        
        # Posisi slider (0.0 sampai 1.0). Default 0.5 berarti di tengah (50%)
        self.slider_pos = 0.5 
        self.dragging = False

    def set_images(self, path_before, path_after):
        """Memuat gambar ke memori UI"""
        self.pixmap_before = QPixmap(path_before)
        self.pixmap_after = QPixmap(path_after)
        self.slider_pos = 0.5 # Kembalikan ke tengah setiap gambar baru dimuat
        self.update() # Memaksa UI untuk menggambar ulang

    def paintEvent(self, event):
        """Fungsi inti yang dipanggil PyQt setiap kali ukuran jendela berubah atau di-update"""
        if self.pixmap_before is None or self.pixmap_after is None:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Skala gambar agar pas dengan ukuran jendela tanpa mengubah rasio asli (Aspect Ratio)
        scaled_before = self.pixmap_before.scaled(
            self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        scaled_after = self.pixmap_after.scaled(
            self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )

        # Hitung posisi X dan Y agar gambar selalu berada di tengah (centered)
        x_offset = (self.width() - scaled_before.width()) // 2
        y_offset = (self.height() - scaled_before.height()) // 2

        # 1. Gambar 'After' sebagai latar belakang (penuh)
        painter.drawPixmap(x_offset, y_offset, scaled_after)

        # 2. Gambar 'Before' dipotong (clipping) menggunakan QRect
        split_x = int(scaled_before.width() * self.slider_pos)
        clip_rect = QRect(x_offset, y_offset, split_x, scaled_before.height())
        
        painter.setClipRect(clip_rect)
        painter.drawPixmap(x_offset, y_offset, scaled_before)
        
        # Hapus batas kliping untuk menggambar garis batas
        painter.setClipping(False)

        # 3. Gambar Garis Pemisah (Handle Slider)
        line_x = x_offset + split_x
        pen = QPen(QColor(255, 255, 255)) # Warna garis putih
        pen.setWidth(3)
        painter.setPen(pen)
        painter.drawLine(line_x, y_offset, line_x, y_offset + scaled_before.height())
        
        # Gambar lingkaran kecil sebagai tuas penarik di tengah garis
        painter.setBrush(QColor(255, 255, 255))
        painter.drawEllipse(line_x - 10, y_offset + (scaled_before.height() // 2) - 10, 20, 20)

    # --- Logika Interaksi Mouse ---
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.update_slider_position(event.position().x())

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.update_slider_position(event.position().x())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False

    def update_slider_position(self, mouse_x):
        """Menghitung persentase posisi mouse relatif terhadap lebar gambar"""
        if self.pixmap_before is None: return
        
        scaled_before = self.pixmap_before.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio)
        x_offset = (self.width() - scaled_before.width()) // 2
        
        # Konversi posisi kursor menjadi skala 0.0 - 1.0
        rel_x = mouse_x - x_offset
        self.slider_pos = max(0.0, min(1.0, rel_x / scaled_before.width()))
        self.update() # Panggil paintEvent untuk merender ulang posisi garis