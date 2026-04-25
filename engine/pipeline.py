import os
import torch
import gc
from PyQt6.QtCore import QThread, pyqtSignal

# Import Wrapper
from engine.colorizer import DeOldifyWrapper
from engine.upscaler import SwinIRWrapper
from engine.face_restorer import CodeFormerWrapper

class AIPipelineWorker(QThread):
    progress_updated = pyqtSignal(int, str) 
    process_finished = pyqtSignal(str, str) 

    def __init__(self, input_path):
        super().__init__()
        self.input_path = input_path
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    def run(self):
        try:
            # ================================================================
            # 0. SETUP & PATHING (DIARAHKAN KE FOLDER RESULT_IMAGE)
            # ================================================================
            self.progress_updated.emit(5, "Menyiapkan mesin restorasi...")
            
            # Cari direktori root (satu tingkat di atas folder 'engine')
            engine_dir = os.path.dirname(os.path.abspath(__file__))
            root_dir = os.path.dirname(engine_dir)
            
            # Tentukan folder penampung sementara agar folder user tidak kotor
            temp_dir = os.path.join(root_dir, 'result_image')
            os.makedirs(temp_dir, exist_ok=True) 
            
            # Ambil nama file asli
            filename = os.path.basename(self.input_path)
            base, ext = os.path.splitext(filename)
            
            # Arahkan semua output file ke folder result_image
            path_step1 = os.path.join(temp_dir, f"{base}_tmp_color{ext}")
            path_step2 = os.path.join(temp_dir, f"{base}_tmp_upscale{ext}")
            output_path = os.path.join(temp_dir, f"{base}_Perfect_Restored{ext}")

            # ================================================================
            # TAHAP 1: DEOLDIFY (Pewarnaan)
            # ================================================================
            self.progress_updated.emit(10, "Tahap 1/3: Memberi warna (DeOldify)...")
            self.process_colorization(self.input_path, path_step1)
            self.clear_gpu_memory()

            # ================================================================
            # TAHAP 2: SWINIR (Upscale & Pembersihan Tekstur Badan)
            # ================================================================
            if os.path.exists(path_step1):
                self.progress_updated.emit(40, "Tahap 2/3: Upscale 4x & Menghaluskan badan (SwinIR)...")
                self.process_upscaling(path_step1, path_step2)
                self.clear_gpu_memory()
            else:
                raise Exception("Gagal: Hasil pewarnaan tidak ditemukan.")

            # ================================================================
            # TAHAP 3: CODEFORMER (Restorasi Wajah HD)
            # ================================================================
            if os.path.exists(path_step2):
                self.progress_updated.emit(70, "Tahap 3/3: Mempertajam detail wajah (CodeFormer)...")
                self.process_face_restoration(path_step2, output_path)
                self.clear_gpu_memory()
            else:
                raise Exception("Gagal: Hasil upscale tidak ditemukan.")

            # ================================================================
            # 4. FINALISASI & CLEANUP
            # ================================================================
            self.progress_updated.emit(95, "Membersihkan file transisi...")
            
            # Hapus HANYA file temporary step 1 dan 2
            for temp_file in [path_step1, path_step2]:
                if os.path.exists(temp_file):
                    os.remove(temp_file)

            self.progress_updated.emit(100, "Restorasi Sempurna Selesai!")
            self.process_finished.emit(self.input_path, output_path)

        except Exception as e:
            self.progress_updated.emit(0, f"Error: {str(e)}")
            print(f"[PIPELINE ERROR] {e}")

    def clear_gpu_memory(self):
        """Memaksa Python melepaskan VRAM setiap pergantian model"""
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def process_colorization(self, input_p, output_p):
        worker = DeOldifyWrapper()
        success = worker.process(input_p, output_p)
        worker.unload()
        del worker
        if not success: raise Exception("Pewarnaan gagal.")

    def process_upscaling(self, input_p, output_p):
        worker = SwinIRWrapper()
        success = worker.process(input_p, output_p)
        worker.unload()
        del worker
        if not success: raise Exception("Upscaling SwinIR gagal.")

    def process_face_restoration(self, input_p, output_p):
        worker = CodeFormerWrapper()
        success = worker.process(input_p, output_p)
        worker.unload()
        del worker
        if not success: raise Exception("Restorasi wajah gagal.")