# Pembuat File SRT

Aplikasi web berbasis Python untuk membuat file subtitle `.srt` — bisa secara otomatis dari file video/audio menggunakan AI (Whisper), atau secara manual.

---

## Fitur

- **Transkripsi otomatis** — upload video/audio, AI transkripsi suara jadi teks subtitle
- **Progress realtime** — progress bar + persentase diupdate langsung dari server
- **Kata per baris** — atur berapa kata yang muncul per baris subtitle (2–10 kata)
- **Petunjuk kosakata** — bantu AI kenali nama, istilah teknis, atau singkatan khusus
- **Editor manual** — tambah, edit, dan hapus baris subtitle secara bebas
- **Preview langsung** — lihat hasil SRT sebelum diunduh
- **Drag & drop** — seret file langsung ke halaman

---

## Persyaratan

- Python 3.8+
- [ffmpeg](https://ffmpeg.org/) — wajib untuk pemrosesan audio

Cek apakah ffmpeg sudah terinstal:

```bash
ffmpeg -version
```

Jika belum, install via Homebrew (Mac):

```bash
brew install ffmpeg
```

---

## Instalasi

```bash
# 1. Clone atau download project ini
git clone <url-repo>
cd bikinsrt

# 2. Buat virtual environment
python3 -m venv venv

# 3. Aktifkan virtual environment
source venv/bin/activate        # Mac / Linux
venv\Scripts\activate           # Windows

# 4. Install dependensi
pip install -r requirements.txt
```

---

## Menjalankan Aplikasi

```bash
source venv/bin/activate
python app.py
```

Buka browser ke: **http://127.0.0.1:5001**

---

## Cara Pakai

### Transkripsi Otomatis (AI)

1. Buka tab **Otomatis (AI)**
2. Upload file video atau audio (drag & drop atau klik)
3. Pilih pengaturan:

   | Pengaturan | Keterangan |
   |---|---|
   | **Model Whisper** | Semakin besar model, semakin akurat tapi lebih lambat |
   | **Bahasa** | Pilih bahasa atau biarkan deteksi otomatis |
   | **Beam Size** | Semakin besar = lebih teliti, lebih lambat. Rekomendasi: 5 |
   | **Kata per baris** | Jumlah kata per baris subtitle. Default: 3 |
   | **Petunjuk kosakata** | Opsional — tulis nama/istilah khusus agar tidak salah transkripsi |

4. Klik **Transkripsi Otomatis** — progress tampil realtime
5. Hasil otomatis dimuat ke tab **Manual** untuk diedit
6. Klik **Unduh SRT**

### Manual

1. Buka tab **Manual**
2. Klik **+ Tambah Baris** untuk setiap subtitle
3. Isi waktu mulai, waktu selesai, dan teks
4. Klik **Unduh SRT**

**Format waktu yang diterima:**

```
00:01:23,456   →  jam:menit:detik,milidetik
00:01:23       →  jam:menit:detik
01:23          →  menit:detik
83.456         →  detik desimal
```

---

## Model Whisper

| Model | Ukuran | Kecepatan | Akurasi |
|---|---|---|---|
| tiny | ~75 MB | ⚡⚡⚡⚡⚡ | ★☆☆☆☆ |
| base | ~145 MB | ⚡⚡⚡⚡ | ★★☆☆☆ |
| small | ~465 MB | ⚡⚡⚡ | ★★★☆☆ |
| medium | ~1.5 GB | ⚡⚡ | ★★★★☆ |
| large | ~2.9 GB | ⚡ | ★★★★☆ |
| large-v2 | ~2.9 GB | ⚡ | ★★★★★ |
| large-v3 | ~2.9 GB | ⚡ | ★★★★★ |

> Model didownload otomatis pertama kali dipakai dan disimpan di cache lokal.

---

## Format File yang Didukung

| Tipe | Format |
|---|---|
| Video | MP4, MKV, MOV, AVI, WEBM |
| Audio | MP3, WAV, M4A, OGG, FLAC, AAC |
| Maks. ukuran | 500 MB |

---

## Struktur Project

```
bikinsrt/
├── app.py              # Flask backend + logika transkripsi
├── requirements.txt    # Dependensi Python
├── templates/
│   └── index.html      # Halaman web (UI)
└── venv/               # Virtual environment (tidak di-commit)
```

---

## Dependensi

- [Flask](https://flask.palletsprojects.com/) — web framework
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — transkripsi suara ke teks
- [ffmpeg](https://ffmpeg.org/) — pemrosesan audio/video
