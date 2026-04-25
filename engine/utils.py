import cv2
import torch
import numpy as np

def load_image_to_tensor(image_path, device):
    """Membaca gambar dari disk dan mengubahnya menjadi PyTorch Tensor"""
    # Baca gambar menggunakan OpenCV (format BGR)
    img = cv2.imread(image_path, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"Gagal membaca gambar di path: {image_path}")
        
    # Konversi BGR (OpenCV) ke RGB (standar umum)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # Normalisasi nilai piksel dari 0-255 menjadi 0.0-1.0
    img = img.astype(np.float32) / 255.0
    
    # Ubah dimensi dari (Tinggi, Lebar, Channel) ke (Channel, Tinggi, Lebar)
    img = np.transpose(img, (2, 0, 1))
    
    # Ubah ke PyTorch Tensor, tambah dimensi Batch di depan, dan kirim ke RAM/VRAM
    tensor = torch.from_numpy(img).float().unsqueeze(0).to(device)
    return tensor

def save_tensor_to_image(tensor, output_path):
    """Mengubah PyTorch Tensor kembali menjadi file gambar JPG/PNG"""
    # Pindahkan tensor dari GPU ke CPU, hilangkan dimensi Batch, dan ubah ke numpy array
    output = tensor.data.squeeze().float().cpu().clamp_(0, 1).numpy()
    
    # Kembalikan dimensi dari CHW ke HWC
    if output.ndim == 3:
        output = np.transpose(output, (1, 2, 0))
        
    # Denormalisasi nilai dari 0.0-1.0 kembali ke 0-255
    output = (output * 255.0).round().astype(np.uint8)
    
    # Konversi kembali dari RGB ke BGR untuk disimpan oleh OpenCV
    output = cv2.cvtColor(output, cv2.COLOR_RGB2BGR)
    cv2.imwrite(output_path, output)