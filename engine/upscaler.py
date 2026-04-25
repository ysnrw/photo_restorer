import os
import sys
import torch
import cv2
import numpy as np
import torch.nn.functional as F

# =========================================================================
# FIX UNTUK PYTORCH 2.6+
# =========================================================================
try:
    import torchvision.transforms.functional_tensor # type: ignore
except ImportError:
    import torchvision.transforms.functional as functional
    sys.modules['torchvision.transforms.functional_tensor'] = functional

# =========================================================================
# PATH SETUP: Arahkan ke folder SwinIR yang sudah di-clone
# =========================================================================
ENGINE_DIR = os.path.dirname(os.path.abspath(__file__))
SWINIR_ROOT = os.path.join(ENGINE_DIR, 'external', 'SwinIR')
if SWINIR_ROOT not in sys.path:
    sys.path.insert(0, SWINIR_ROOT)

# Import arsitektur dari modul asli SwinIR
from models.network_swinir import SwinIR as SwinIRModel # type: ignore


class SwinIRWrapper:
    def __init__(self):
        self.model = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        # Konfigurasi tile untuk stabilitas memori
        self.tile_size = 400
        self.tile_pad = 32

    def load_model(self):
        print("Memuat SwinIR (Real-World SR x4) dari models/SwinIR_x4.pth...")
        # Konfigurasi arsitektur: nearest+conv
        # Ini adalah konfigurasi yang cocok dengan bobot yang memiliki
        # conv_up1, conv_up2, conv_hr, dll.
        self.model = SwinIRModel(
            upscale=4,
            img_size=64,
            window_size=8,
            img_range=1.0,
            depths=[6, 6, 6, 6, 6, 6],
            embed_dim=180,
            num_heads=[6, 6, 6, 6, 6, 6],
            mlp_ratio=2,
            upsampler='nearest+conv',
            resi_connection='1conv'
        ).to(self.device)

        # Path model langsung di engine/models/
        model_path = os.path.join(ENGINE_DIR, 'models', 'SwinIR_x4.pth')
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Weights SwinIR tidak ditemukan di:\n{model_path}\n"
                "Letakkan file model dengan nama SwinIR_x4.pth di folder engine/models/"
            )

        checkpoint = torch.load(model_path, map_location=self.device)
        # Mengambil state_dict (bisa 'params_ema' atau 'params')
        state_dict = checkpoint.get('params_ema', checkpoint.get('params', checkpoint))
        self.model.load_state_dict(state_dict, strict=True)
        self.model.eval()
        print("SwinIR siap digunakan.")

    def _pad_to_multiple(self, tensor, multiple=16):
        """Padding reflektif agar dimensi menjadi kelipatan multiple."""
        _, _, h, w = tensor.size()
        pad_h = (multiple - h % multiple) % multiple
        pad_w = (multiple - w % multiple) % multiple
        if pad_h > 0 or pad_w > 0:
            tensor = F.pad(tensor, (0, pad_w, 0, pad_h), 'reflect')
        return tensor, h, w

    def _process_tile(self, tile):
        """Proses satu tile gambar melalui SwinIR."""
        tile, h_orig, w_orig = self._pad_to_multiple(tile, 16)
        with torch.no_grad():
            out = self.model(tile)
        # Hapus padding (skala 4x)
        out = out[:, :, :h_orig*4, :w_orig*4]
        return out

    def _merge_tiles(self, tiles, h, w, upscale=4):
        """Gabungkan tile-tile hasil inferensi menjadi satu gambar utuh."""
        out = torch.zeros((1, 3, h * upscale, w * upscale), device=self.device)
        idx = 0
        tile_h, tile_w = self.tile_size, self.tile_size
        for y in range(0, h, tile_h):
            cy = y * upscale
            h_out = min(tile_h * upscale, h * upscale - cy)
            for x in range(0, w, tile_w):
                cx = x * upscale
                w_out = min(tile_w * upscale, w * upscale - cx)
                out[:, :, cy:cy+h_out, cx:cx+w_out] = tiles[idx][:, :, :h_out, :w_out]
                idx += 1
        return out

    def process(self, input_path, output_path):
        if self.model is None:
            self.load_model()

        img = cv2.imread(input_path, cv2.IMREAD_COLOR)
        if img is None:
            raise FileNotFoundError(f"Gambar tidak bisa dibaca: {input_path}")

        h_orig, w_orig = img.shape[:2]
        # Konversi BGR -> RGB -> tensor [0,1]
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img_tensor = torch.from_numpy(img_rgb).permute(2, 0, 1).float().unsqueeze(0) / 255.0
        img_tensor = img_tensor.to(self.device)

        # ============================
        # PROSES TILE‑BASED
        # ============================
        tiles = []
        tile_h, tile_w = self.tile_size, self.tile_size
        for y in range(0, h_orig, tile_h):
            for x in range(0, w_orig, tile_w):
                # Area dengan overlap
                y_pad = max(0, y - self.tile_pad)
                x_pad = max(0, x - self.tile_pad)
                y_end = min(h_orig, y + tile_h + self.tile_pad)
                x_end = min(w_orig, x + tile_w + self.tile_pad)

                tile = img_tensor[:, :, y_pad:y_end, x_pad:x_end]
                h_tile_in = y_end - y_pad
                w_tile_in = x_end - x_pad

                out_tile = self._process_tile(tile)

                # Crop bagian tengah (buang overlap)
                start_h = (y - y_pad) * 4
                start_w = (x - x_pad) * 4
                end_h = start_h + min(tile_h, h_orig - y) * 4
                end_w = start_w + min(tile_w, w_orig - x) * 4
                cropped = out_tile[:, :, start_h:end_h, start_w:end_w]
                tiles.append(cropped)

        # Gabungkan semua tile
        out = self._merge_tiles(tiles, h_orig, w_orig, upscale=4)

        # Konversi kembali ke OpenCV (BGR)
        out_np = out.squeeze().cpu().clamp(0, 1).numpy()
        out_np = (out_np.transpose(1, 2, 0) * 255).round().astype(np.uint8)
        out_np = cv2.cvtColor(out_np, cv2.COLOR_RGB2BGR)
        cv2.imwrite(output_path, out_np)
        print(f"[SwinIR] Output disimpan di: {output_path}")
        return True

    def unload(self):
        if self.model:
            del self.model
            self.model = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            print("SwinIR dihapus dari memori.")