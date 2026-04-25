import os
import sys
import torch
import cv2
import numpy as np
import importlib.util

# =========================================================================
# 1. PATH SETUP
# =========================================================================
ENGINE_DIR = os.path.dirname(os.path.abspath(__file__))
CODEFORMER_ROOT = os.path.join(ENGINE_DIR, 'external', 'CodeFormer')

if not os.path.isdir(CODEFORMER_ROOT):
    raise FileNotFoundError(
        f"Folder CodeFormer tidak ditemukan di:\n{CODEFORMER_ROOT}\n"
        "Jalankan: git clone https://github.com/sczhou/CodeFormer.git engine/external/CodeFormer"
    )

if CODEFORMER_ROOT not in sys.path:
    sys.path.insert(0, CODEFORMER_ROOT)

# =========================================================================
# 2. FUNGSI BANTU INJEKSI MODUL
# =========================================================================
def _register_module(module_name, file_path):
    if module_name in sys.modules:
        return
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None:
        raise ImportError(f"Tidak bisa membuat spec untuk {module_name} dari {file_path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)

def _force_load_basicsr():
    basicsr_dir = os.path.join(CODEFORMER_ROOT, 'basicsr')
    if not os.path.isdir(basicsr_dir):
        raise FileNotFoundError(f"Folder basicsr tidak ditemukan di {basicsr_dir}")
    basicsr_init = os.path.join(basicsr_dir, '__init__.py')
    _register_module('basicsr', basicsr_init)

    archs_dir = os.path.join(basicsr_dir, 'archs')
    archs_init = os.path.join(archs_dir, '__init__.py')
    if os.path.exists(archs_init):
        _register_module('basicsr.archs', archs_init)

    if os.path.isdir(archs_dir):
        for fname in os.listdir(archs_dir):
            if fname.endswith('.py') and fname != '__init__.py':
                mod_name = f'basicsr.archs.{fname[:-3]}'
                file_path = os.path.join(archs_dir, fname)
                if mod_name not in sys.modules:
                    try:
                        _register_module(mod_name, file_path)
                    except Exception as e:
                        print(f"Warning: Gagal mendaftarkan {mod_name}: {e}")

# =========================================================================
# 3. IMPORT
# =========================================================================
CodeFormer = None
FaceRestoreHelper = None

try:
    from basicsr.archs.codeformer_arch import CodeFormer
    print("[SUCCESS] CodeFormer diimpor secara normal.")
except ModuleNotFoundError:
    print("[INFO] Import normal gagal, melakukan injeksi paksa...")
    for m in list(sys.modules.keys()):
        if m.startswith('basicsr'):
            del sys.modules[m]
    _force_load_basicsr()
    from basicsr.archs.codeformer_arch import CodeFormer
    print("[SUCCESS] CodeFormer diimpor setelah injeksi manual.")

from facexlib.utils.face_restoration_helper import FaceRestoreHelper

# =========================================================================
# 4. WRAPPER CLASS
# =========================================================================
class CodeFormerWrapper:
    def __init__(self):
        self.model = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.face_helper = None
        self._loaded = False

    def load_model(self):
        if self._loaded:
            return
        print("Memuat arsitektur dan bobot CodeFormer...")
        try:
            self.model = CodeFormer(
                dim_embd=512,
                codebook_size=1024,
                connect_list=['32', '64', '128', '256']
            ).to(self.device)
        except TypeError:
            self.model = CodeFormer().to(self.device)

        ckpt_path = os.path.join(ENGINE_DIR, 'models', 'codeformer.pth')
        checkpoint = torch.load(ckpt_path, map_location='cpu')
        state_dict = checkpoint.get('params_ema', checkpoint.get('params', checkpoint))
        self.model.load_state_dict(state_dict, strict=True)
        self.model.eval()

        # Inisialisasi FaceRestoreHelper
        self.face_helper = FaceRestoreHelper(
            upscale_factor=1,
            face_size=512,
            crop_ratio=(1.0, 1.0),   # 1.0 agar crop tepat kotak deteksi, tidak ada ruang ekstra
            det_model='retinaface_resnet50',
            save_ext='png',
            device=self.device
        )
        self._loaded = True
        print("CodeFormer siap digunakan.")

    def process(self, input_path, output_path):
        if not self._loaded:
            self.load_model()

        img = cv2.imread(input_path)
        if img is None:
            raise FileNotFoundError(f"Tidak bisa membaca gambar: {input_path}")

        # Reset state helper
        if hasattr(self.face_helper, 'clean_all_list'):
            self.face_helper.clean_all_list()
        else:
            self.face_helper.clean_all()

        self.face_helper.read_image(img)
        self.face_helper.get_face_landmarks_5(only_center_face=False, eye_dist_threshold=5)
        self.face_helper.align_warp_face()

        if len(self.face_helper.cropped_faces) == 0:
            print("[CodeFormer] Tidak ada wajah terdeteksi. Menyimpan gambar asli.")
            cv2.imwrite(output_path, img)
            return True

        # Proses setiap crop wajah
        for idx, cropped_face in enumerate(self.face_helper.cropped_faces):
            # ** PERBAIKAN UTAMA: pastikan ukuran crop persis 512x512 **
            h, w = cropped_face.shape[:2]
            if h != 512 or w != 512:
                print(f"[WARNING] Crop wajah ke-{idx} berukuran {h}x{w}, di-resize ke 512x512.")
                cropped_face = cv2.resize(cropped_face, (512, 512), interpolation=cv2.INTER_LINEAR)

            # Konversi BGR -> RGB, normalisasi
            face_tensor = (
                torch.from_numpy(cv2.cvtColor(cropped_face, cv2.COLOR_BGR2RGB))
                .permute(2, 0, 1)
                .float()
                .unsqueeze(0)
                / 255.0
            ).to(self.device)

            # Inferensi
            with torch.no_grad():
                output = self.model(face_tensor, w=0.5, adain=True)[0]
                restored_face = output.squeeze().permute(1, 2, 0).cpu().clamp(0, 1).numpy()
                restored_face = (restored_face * 255).astype(np.uint8)
                restored_face = cv2.cvtColor(restored_face, cv2.COLOR_RGB2BGR)

            self.face_helper.add_restored_face(restored_face)

        # Gabungkan kembali ke gambar asli
        self.face_helper.get_inverse_affine(None)
        final_img = self.face_helper.paste_faces_to_input_image()
        cv2.imwrite(output_path, final_img)
        print(f"[CodeFormer] Output: {output_path}")
        return True

    def unload(self):
        if self.model:
            del self.model
            self.model = None
        if self.face_helper:
            del self.face_helper
            self.face_helper = None
        self._loaded = False
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        print("CodeFormer di-unload.")