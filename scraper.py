import time
import csv
import os
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# --- KONFIGURASI ---
URL = "https://gamblingcounting.com/pragmatic-auto-roulette"
FILE_CSV = "roulette_data.csv"

# --- LOGIKA RULET (TIDAK BERUBAH) ---
def get_roulette_stats(number):
    """Menghitung properti angka rulet (Kolom, Lusin, dll)"""
    if not number.isdigit(): return None
    n = int(number)
    
    if n == 0:
        return {'Angka': 0, 'Warna': 'Green', 'GanjilGenap': 'Zero', 'BesarKecil': 'Zero', 'Kolom': 0, 'Lusin': 0}

    # Tentukan Kolom (1, 2, atau 3)
    if n % 3 == 1: col = 1
    elif n % 3 == 2: col = 2
    else: col = 3

    stats = {
        'Angka': n,
        'Warna': 'Unknown', 
        'GanjilGenap': 'Ganjil' if n % 2 != 0 else 'Genap',
        'BesarKecil': 'Kecil (1-18)' if n <= 18 else 'Besar (19-36)',
        'Kolom': f"Kolom {col}",
        'Lusin': f"Lusin {((n-1)//12)+1}"
    }
    return stats

def get_last_recorded_data(filepath, limit=10):
    """Membaca N data terakhir dari CSV untuk pencocokan"""
    if not os.path.exists(filepath):
        return []
    
    with open(filepath, 'r', newline='') as f:
        reader = list(csv.DictReader(f))
        if not reader: return []
        return [row['Angka'] for row in reader[-limit:]]

def save_to_csv(data_list):
    """Menyimpan list data baru ke CSV"""
    file_exists = os.path.exists(FILE_CSV)
    
    fieldnames = ['WaktuScrape', 'Angka', 'Warna', 'Kolom', 'Lusin', 'GanjilGenap', 'BesarKecil']
    
    with open(FILE_CSV, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerows(data_list)

def extract_numbers_from_container(text):
    """Mengambil semua angka dari teks container"""
    numbers = []
    if not text: return numbers
    for word in text.split():
        if word.isdigit():
            numbers.append(word)
    return numbers

def run():
    print("=== ROULETTE SCRAPER (PLAYWRIGHT VERSION) ===")
    print(f"Target: {URL}")
    print(f"Output: {FILE_CSV}")

    # Menjalankan Playwright
    with sync_playwright() as p:
        # Launch Browser. Headless=True agar berjalan di background (seperti Github Action)
        # Kami menggunakan args khusus agar terlihat seperti user asli
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"] 
        )
        
        # Membuat Context dengan User Agent spesifik untuk bypass Cloudflare
        # Viewport diset standar desktop
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080},
            locale="en-US",
            timezone_id="Asia/Jakarta"
        )
        
        page = context.new_page()

        try:
            print(f"[{time.strftime('%H:%M:%S')}] Mengambil data terbaru...")
            
            # Goto URL dengan timeout 60 detik
            page.goto(URL, timeout=60000, wait_until="domcontentloaded")
            
            # Tunggu sebentar untuk animasi loading halaman (wajib untuk Cloudflare kadang-kadang)
            page.wait_for_timeout(5000) 

            print("Mencari section 'History of rounds'...")
            
            container = None
            
            # Logika Selector (Sama seperti kode asli: Coba Selector 1, lalu Selector 2)
            try:
                # Selector 1: div.live-game-page__block__results
                page.wait_for_selector("div.live-game-page__block__results", timeout=15000)
                container = page.query_selector("div.live-game-page__block__results")
                print("✓ Container ditemukan (Selector 1)")
            except PlaywrightTimeoutError:
                print("⚠ Selector 1 timeout, mencoba Selector 2...")
                try:
                    # Selector 2: .live-game-page__block__content
                    page.wait_for_selector(".live-game-page__block__content", timeout=15000)
                    container = page.query_selector(".live-game-page__block__content")
                    print("✓ Container ditemukan (Selector 2)")
                except PlaywrightTimeoutError:
                     # Jika Gagal Total
                    print("✗ GAGAL: Container tidak ditemukan sama sekali.")
                    page.screenshot(path="error_screenshot.png")
                    with open("error_page.html", "w", encoding="utf-8") as f:
                        f.write(page.content())
                    print("📸 Screenshot & HTML disimpan untuk debug.")
                    # Kita stop di sini jika tidak ada container
                    return

            # Ambil teks dari container untuk list angka mentah
            container_text = container.inner_text()
            raw_numbers = extract_numbers_from_container(container_text)
            print(f"✓ Ditemukan {len(raw_numbers)} angka dalam container")
            
            if not raw_numbers:
                print("⚠ Container ditemukan tapi kosong!")
                page.screenshot(path="empty_container.png")
                return

            # Ambil elemen individual untuk deteksi warna (div.roulette-number)
            individual_elements = page.query_selector_all("div.roulette-number")
            
            individual_data = []
            # Loop elemen untuk ambil class (warna)
            # Limit loop berdasarkan jumlah angka yang ditemukan di teks agar sinkron
            limit = min(len(raw_numbers), len(individual_elements))
            
            for i in range(limit):
                el = individual_elements[i]
                text = el.inner_text().strip()
                if text.isdigit():
                    classes = el.get_attribute('class')
                    individual_data.append({
                        'number': text,
                        'classes': classes
                    })

            # --- GABUNGKAN DATA (LOGIKA SAMA PERSIS DENGAN KODE ASLI) ---
            current_batch = []
            for i, num in enumerate(raw_numbers):
                if i >= len(individual_data):
                    break
                    
                data = get_roulette_stats(num)
                
                # Deteksi Warna dari Class
                classes = individual_data[i]['classes'].lower() if individual_data[i]['classes'] else ""
                
                if 'red' in classes: data['Warna'] = 'Merah'
                elif 'black' in classes: data['Warna'] = 'Hitam'
                elif 'green' in classes: data['Warna'] = 'Hijau'
                else:
                    # Fallback manual jika class tidak jelas
                    n = int(num)
                    if n == 0: data['Warna'] = 'Green'
                    elif n in [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]: data['Warna'] = 'Merah'
                    else: data['Warna'] = 'Hitam'
                
                data['WaktuScrape'] = time.strftime('%Y-%m-%d %H:%M:%S')
                current_batch.append(data)
            
            # Balik urutan agar menjadi Kronologis (Lama -> Baru) untuk logic penyimpanan
            chronological_batch = list(reversed(current_batch))
            
            # --- PENCOCOKAN DATA (LOGIKA DEDUPLIKASI) ---
            last_recorded = get_last_recorded_data(FILE_CSV, limit=10)
            new_items_to_save = []
            
            if not last_recorded:
                new_items_to_save = chronological_batch
                print("\nFile CSV kosong/baru. Menyimpan semua data.")
            else:
                # Logika pencocokan overlap
                current_numbers = [str(item['Angka']) for item in current_batch]
                
                found_index = -1
                
                # Cek pola urutan
                for i in range(len(current_numbers) - len(last_recorded) + 1):
                    if current_numbers[i:i+len(last_recorded)] == last_recorded:
                        found_index = i
                        break
                
                # Cek pola urutan terbalik (antisipasi anomali website)
                if found_index == -1:
                    reversed_last = list(reversed(last_recorded))
                    for i in range(len(current_numbers) - len(reversed_last) + 1):
                        if current_numbers[i:i+len(reversed_last)] == reversed_last:
                            found_index = i
                            break
                
                if found_index > 0:
                    raw_new = current_batch[:found_index]
                    new_items_to_save = list(reversed(raw_new))
                    print(f"✓ Ditemukan {len(new_items_to_save)} data baru.")
                elif found_index == 0:
                    print("✓ Tidak ada data baru (sudah update).")
                else:
                    print("⚠ Pola tidak cocok sempurna. Mencoba mencocokkan angka terakhir saja...")
                    last_csv_num = last_recorded[-1]
                    found_at = -1
                    for i, data in enumerate(current_batch):
                        if str(data['Angka']) == last_csv_num:
                            found_at = i
                            break
                    
                    if found_at > 0:
                        raw_new = current_batch[:found_at]
                        new_items_to_save = list(reversed(raw_new))
                        print(f"✓ Menambah {len(new_items_to_save)} data baru (berdasarkan angka terakhir).")
                    elif found_at == 0:
                        print("✓ Data sudah update.")
                    else:
                        print("⚠ Data CSV dan Website berbeda jauh. Menyimpan semua data website.")
                        new_items_to_save = chronological_batch

            # --- SIMPAN ---
            if new_items_to_save:
                save_to_csv(new_items_to_save)
                print(f"\n✓ BERHASIL: {len(new_items_to_save)} baris disimpan ke CSV.")
                
        except Exception as e:
            print(f"\n[ERROR FATAL] {e}")
            page.screenshot(path="fatal_error.png")
            raise e
        
        finally:
            context.close()
            browser.close()
            print("\n✅ Browser ditutup.")

if __name__ == "__main__":
    run()
