import time
import csv
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- KONFIGURASI ---
URL = "https://gamblingcounting.com/pragmatic-auto-roulette"
FILE_CSV = "roulette_data.csv"

# --- LOGIKA RULET ---
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

def init_driver():
    """Menyiapkan browser headless dengan mode Stealth"""
    opts = Options()
    # PENTING: Gunakan --headless=new (fitur baru Chrome yang lebih sulit dideteksi)
    opts.add_argument("--headless=new") 
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    
    # User Agent biasa (seolah-olah Windows Desktop)
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Sembunyikan fakta bahwa ini dikontrol otomatis
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option('useAutomationExtension', False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    
    # Script tambahan untuk memalsukan properti navigator
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {
        "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    
    return driver

def get_last_recorded_data(filepath, limit=10):
    """Membaca N data terakhir dari CSV untuk pencocokan"""
    if not os.path.exists(filepath):
        return []
    
    with open(filepath, 'r', newline='') as f:
        reader = list(csv.DictReader(f))
        if not reader: return []
        # Ambil kolom 'Angka' saja untuk fingerprint sederhana
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
    for word in text.split():
        if word.isdigit():
            numbers.append(word)
    return numbers

def main():
    print("=== ROULETTE SCRAPER (MANUAL UPDATE) ===")
    print(f"Target: {URL}")
    print(f"Output: {FILE_CSV}")
    print("Hanya mengambil data dari section 'History of rounds' (Last 200 spins)")
    print("Update manual - run script saat ada update baru di website\n")
    
driver = init_driver()
    
try:
        print(f"[{time.strftime('%H:%M:%S')}] Mengambil data terbaru...")
        driver.get(URL)
        
        # Tunggu loading awal
        time.sleep(10) 
        
        print("Mencari section 'History of rounds'...")
        
        try:
            # Coba selector utama
            container = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.live-game-page__block__results"))
            )
            print("✓ Container ditemukan!")
            
        except Exception as e:
            print(f"✗ Gagal Selector 1. Mencoba Selector 2...")
            try:
                # Coba selector alternatif
                container = WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "live-game-page__block__content"))
                )
                print("✓ Container alternatif ditemukan!")
            except Exception as e2:
                # --- LOGIKA DEBUGGING JIKA GAGAL ---
                print("✗ GAGAL TOTAL. Website mungkin memblokir atau layout berubah.")
                
                # Ambil Screenshot untuk dilihat di GitHub
                driver.save_screenshot("error_screenshot.png")
                print("📸 Screenshot error disimpan sebagai 'error_screenshot.png'")
                
                # Simpan HTML source code
                with open("error_page.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                print("📄 HTML error disimpan sebagai 'error_page.html'")
                
                raise e2 # Lempar error agar GitHub Action tahu ini gagal  
        
        # Gabungkan data: angka dari container dengan warna dari elemen individual
        current_batch = []
        
        for i, num in enumerate(raw_numbers):
            if i >= len(individual_data):
                break
                
            # Analisis properti angka
            data = get_roulette_stats(num)
            
            # Deteksi Warna dari Class HTML
            classes = individual_data[i]['classes'].lower()
            
            if 'roulette-number--red' in classes or 'red' in classes:
                data['Warna'] = 'Merah'
            elif 'roulette-number--black' in classes or 'black' in classes:
                data['Warna'] = 'Hitam'
            elif 'roulette-number--green' in classes or 'green' in classes:
                data['Warna'] = 'Hijau'
            else:
                # Fallback: tentukan warna berdasarkan angka
                n = int(num)
                if n == 0:
                    data['Warna'] = 'Green'
                elif n in [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]:
                    data['Warna'] = 'Merah'
                else:
                    data['Warna'] = 'Hitam'
            
            data['WaktuScrape'] = time.strftime('%Y-%m-%d %H:%M:%S')
            current_batch.append(data)
        
        print(f"\n✓ Berhasil parsing {len(current_batch)} angka")
        
        # PENTING: Website biasanya menampilkan angka terbaru di KIRI/ATAS
        # Jadi current_batch[0] adalah yang PALING BARU
        # Untuk CSV, kita ingin urutan kronologis (terlama -> terbaru)
        # Jadi kita perlu membalik urutan sebelum menyimpan
        
        # Tampilkan urutan asli (dari website)
        print("\nUrutan dari website (10 terbaru → terlama):")
        for i, data in enumerate(current_batch[:10]):
            print(f"  {i+1}. Angka {data['Angka']} ({data['Warna']})")
        
        # Balik urutan untuk mendapatkan kronologis
        chronological_batch = list(reversed(current_batch))
        
        print("\nUrutan kronologis (10 terlama → terbaru):")
        for i, data in enumerate(chronological_batch[-10:]):
            print(f"  {i+1}. Angka {data['Angka']} ({data['Warna']})")
        
        # --- LOGIKA PENCOCOKAN DENGAN 10 ANGKA TERAKHIR ---
        last_recorded = get_last_recorded_data(FILE_CSV, limit=10)
        
        new_items_to_save = []
        
        if not last_recorded:
            # Jika file CSV kosong, simpan semua data dalam urutan kronologis
            new_items_to_save = chronological_batch
            print("\nFile CSV kosong. Menyimpan semua data...")
        else:
            print(f"\n10 angka terakhir di CSV: {last_recorded}")
            
            # Konversi current_batch (website) ke list angka untuk pencocokan
            # Ingat: current_batch adalah [TERBARU, ..., TERLAMA]
            current_numbers = [str(item['Angka']) for item in current_batch]
            
            # Karena CSV menyimpan terlama → terbaru, maka angka terakhir CSV
            # seharusnya cocok dengan angka TERBARU di website (current_batch[0])
            # TAPI perlu dicocokkan dengan benar
            
            # Coba cari pola: kita cari 10 angka terakhir CSV di current_numbers
            # current_numbers = [terbaru, ..., terlama]
            # last_recorded = [terlama_di_csv, ..., terbaru_di_csv]
            
            # Karena CSV terlama → terbaru, dan website terbaru → terlama,
            # kita perlu membalik salah satunya untuk pencocokan
            
            # Versi 1: Cari last_recorded di current_numbers
            found_index = -1
            for i in range(len(current_numbers) - len(last_recorded) + 1):
                if current_numbers[i:i+len(last_recorded)] == last_recorded:
                    found_index = i
                    print(f"✓ Pola ditemukan di index: {i} (urutan sama)")
                    break
            
            if found_index == -1:
                # Versi 2: Cari last_recorded yang dibalik (karena mungkin urutan beda)
                reversed_last = list(reversed(last_recorded))
                for i in range(len(current_numbers) - len(reversed_last) + 1):
                    if current_numbers[i:i+len(reversed_last)] == reversed_last:
                        found_index = i
                        print(f"✓ Pola ditemukan di index: {i} (urutan terbalik)")
                        break
            
            if found_index >= 0:
                # Data baru adalah data sebelum pola ditemukan
                if found_index > 0:
                    # Ambil data dari index 0 sampai sebelum found_index
                    # Ini adalah data terbaru yang belum ada di CSV
                    raw_new = current_batch[:found_index]
                    # Balik urutan untuk kronologis
                    new_items_to_save = list(reversed(raw_new))
                    print(f"✓ Ditemukan {len(new_items_to_save)} data baru untuk disimpan")
                else:
                    print("✓ Tidak ada data baru (semua data sudah ada di CSV)")
            else:
                # Pola tidak ditemukan, mungkin data website sangat berbeda
                print("✗ Pola tidak ditemukan. Mencocokkan satu per satu...")
                
                # Ambil angka terbaru dari CSV
                last_csv_number = last_recorded[-1] if last_recorded else None
                
                if last_csv_number:
                    # Cari angka ini di current_batch (website)
                    found_at = -1
                    for i, data in enumerate(current_batch):
                        if str(data['Angka']) == last_csv_number:
                            found_at = i
                            break
                    
                    if found_at >= 0:
                        if found_at > 0:
                            # Ada data baru sebelum angka yang cocok
                            raw_new = current_batch[:found_at]
                            new_items_to_save = list(reversed(raw_new))
                            print(f"✓ Ditemukan {len(new_items_to_save)} data baru (berdasarkan angka terakhir)")
                        else:
                            print("✓ Tidak ada data baru (angka terakhir cocok di posisi 0)")
                    else:
                        # Angka terakhir CSV tidak ditemukan di website
                        # Simpan semua data website sebagai data baru
                        print("⚠ Angka terakhir CSV tidak ditemukan di website.")
                        print("  Menyimpan semua data website sebagai data baru...")
                        new_items_to_save = chronological_batch
                else:
                    print("✗ Tidak ada data di CSV untuk dibandingkan")
        
        # --- SIMPAN DATA ---
        if new_items_to_save:
            save_to_csv(new_items_to_save)
            print(f"\n✓ Berhasil menyimpan {len(new_items_to_save)} data baru ke CSV.")
            
            if len(new_items_to_save) <= 5:
                print("Data yang disimpan:")
                for data in new_items_to_save:
                    print(f"  Angka {data['Angka']} ({data['Warna']})")
            else:
                print("5 data terbaru yang disimpan:")
                for data in new_items_to_save[-5:]:
                    print(f"  Angka {data['Angka']} ({data['Warna']})")
        else:
            print("\n⚠ Tidak ada data baru. Website mungkin belum update atau data sudah sama dengan CSV.")
            print("  Silakan cek website dan run script lagi nanti.")
        
        # Tampilkan info file
        if os.path.exists(FILE_CSV):
            with open(FILE_CSV, 'r', newline='') as f:
                reader = list(csv.DictReader(f))
                print(f"\n📊 Total data di CSV: {len(reader)}")
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()
        print("\n✅ Selesai. Browser ditutup.")

if __name__ == "__main__":
    main()
