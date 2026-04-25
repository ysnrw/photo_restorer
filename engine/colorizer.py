import os
import sys
import torch
import shutil
from pathlib import Path

# =========================================================================
# FIX UNTUK PYTORCH 2.6+: Matikan fitur weights_only secara paksa
# agar model lawas (DeOldify/FastAI) bisa di-load tanpa terblokir sistem keamanan.
# =========================================================================
original_load = torch.load
def legacy_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return original_load(*args, **kwargs)
torch.load = legacy_load
# =========================================================================

# Daftarkan path external/DeOldify agar Python mengenali modulnya
ENGINE_DIR = os.path.dirname(os.path.abspath(__file__))
EXTERNAL_DIR = os.path.join(ENGINE_DIR, 'external', 'DeOldify')
if EXTERNAL_DIR not in sys.path:
    sys.path.insert(0, EXTERNAL_DIR)

# Mengimpor modul dari source code asli DeOldify
from deoldify import device
from deoldify.device_id import DeviceId
from deoldify.visualize import get_image_colorizer

class DeOldifyWrapper:
    def __init__(self):
        self.model = None

    def load_model(self):
        """Memuat model DeOldify secara aman ke RAM/VRAM"""
        print("Memuat DeOldify (Artistic)...")
        if torch.cuda.is_available():
            device.set(device=DeviceId.GPU0)
        else:
            torch.backends.cudnn.benchmark = False

        # Inisialisasi model. DeOldify otomatis mencari folder 'models' di dalam ENGINE_DIR
        self.model = get_image_colorizer(artistic=True, root_folder=Path(ENGINE_DIR))
        
        # Atur folder temporary untuk output bawaan DeOldify
        self.temp_dir = Path(os.path.join(ENGINE_DIR, 'temp_deoldify'))
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.model.result_folder = self.temp_dir

    def process(self, input_path, output_path):
        """Mengeksekusi pewarnaan gambar dan memindahkan hasilnya"""
        if self.model is None:
            self.load_model()
            
        # render_factor=35 adalah standar seimbang untuk kualitas dan beban VRAM
        result_path = self.model.plot_transformed_image(path=input_path, render_factor=35, compare=False)
        
        if result_path and os.path.exists(result_path):
            shutil.copy(result_path, output_path)
            os.remove(result_path)
            return True
        return False

    def unload(self):
        """Pembersihan memori yang ketat (Garbage Collection)"""
        if self.model is not None:
            del self.model
            self.model = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            print("DeOldify berhasil dihapus dari memori.")