@echo off
title AI Image Restorer - Setup ^& Run
echo ========================================================
echo   Memulai Instalasi Image Restorer
echo ========================================================
echo.

echo [1/5] Membuat Virtual Environment...
python -m venv venv
echo Mengaktifkan Virtual Environment...
call venv\Scripts\activate.bat

echo.
echo [2/5] Menginstal pustaka dari requirements.txt...
pip install -r requirements.txt

echo.
echo [3/5] Mengunduh arsitektur (CodeFormer, DeOldify, SwinIR)...
if not exist "engine\external" mkdir "engine\external"
cd engine\external

if not exist "CodeFormer" git clone https://github.com/sczhou/CodeFormer.git
if not exist "DeOldify" git clone https://github.com/jantic/DeOldify.git
if not exist "SwinIR" git clone https://github.com/JingyunLiang/SwinIR.git

cd ..\..

echo.
echo [4/5] Mengunduh Weights Model (Ini mungkin memakan waktu)...
if not exist "engine\models" mkdir "engine\models"
cd engine\models

if not exist "codeformer.pth" curl -L -o codeformer.pth https://github.com/sczhou/CodeFormer/releases/download/v0.1.0/codeformer.pth
if not exist "ColorizeArtistic_gen.pth" curl -L -o ColorizeArtistic_gen.pth https://data.deepai.org/deoldify/ColorizeArtistic_gen.pth
if not exist "SwinIR_x4.pth" curl -L -o SwinIR_x4.pth https://github.com/JingyunLiang/SwinIR/releases/download/v0.0/003_realSR_BSRGAN_DFOWMFC_s64w8_SwinIR-L_x4_GAN.pth

cd ..\..

echo.
echo [5/5] Instalasi Selesai! Menjalankan Aplikasi...
echo ========================================================
python main.py

pause