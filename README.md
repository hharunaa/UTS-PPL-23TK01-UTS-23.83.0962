# UTS-PPL-23TK01-UTS
UTS Pemrograman Python Lanjut

Muhammad Nur Huda_23.83.0962

# 🔄 Terminal ZigZag Automation Program  
**Python Animation with Adaptive Behavior**

Program ini merupakan implementasi animasi terminal sederhana yang bergerak bolak-balik (zigzag).  
Walaupun dasar idenya sangat kecil, proyek ini dikembangkan menjadi versi yang lebih cerdas dengan sejumlah mekanisme otomatis yang membuat animasi tampak “hidup”.

Seluruh otomatisasi terjadi tanpa input pengguna setelah program berjalan — sehingga animasi dapat menyesuaikan dirinya terhadap kondisi tertentu.

---

## 🧠 Konsep Utama

Alih-alih hanya mencetak teks bergerak, program ini memodifikasi beberapa aspek animasi secara otomatis:

1. **Kecepatan berubah secara dinamis**  
   Jumlah jeda antar-frame tidak konstan. Program memanfaatkan informasi waktu dan parameter internal untuk mengatur tempo animasi.

2. **Karakter animasi dapat berganti otomatis**  
   Simbol yang bergerak tidak statis. Pola teks dapat berubah berdasarkan kondisi tertentu (misal pergantian arah).

3. **Batas gerakan tidak tetap**  
   Panjang langkah zig-zag dapat berubah selama program berjalan, sehingga jalurnya tidak selalu sama di setiap iterasi.

Tujuannya adalah membuat perilaku animasi lebih variatif, lebih fleksibel, dan terlihat lebih dinamis dibanding versi dasar.

---

## ⚙️ Ringkasan Fitur Otomatis

Berikut fitur yang diterapkan di dalam program:

### 1. **Dynamic Speed Controller**
Program mengubah durasi `sleep()` secara otomatis.  
Faktor pemicunya dapat berasal dari waktu sistem atau parameter internal seperti jumlah iterasi.

### 2. **Auto Pattern Rotation**
Karakter yang bergerak bisa berubah dengan sendirinya.  
Saat terjadi pergantian arah (kiri ➜ kanan atau sebaliknya), sistem memilih pola teks lain dari daftar yang tersedia.

### 3. **Adaptive Boundary Logic**
Rentang maksimum gerakan zig-zag dapat berubah selama animasi berlangsung.  
Ini membuat panjang langkah kiri–kanan tidak monoton dan lebih acak.

---

## 🖥 Contoh Output  
![Bukti](bukti%20ss%200962.png)

Contoh animasi yang bisa ditampilkan:

    ********
   ********
  ###########
 ***************
=======


Gerakan maju–mundur akan terlihat jelas saat dijalankan di terminal.

---

## ▶️ Menjalankan Program

Pastikan Python sudah terpasang:

```bash
piton_0962.py
