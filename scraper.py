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
    """Menyiapkan browser headless dengan mode Stealth untuk bypass deteksi"""
    opts = Options()
    # PENTING: Gunakan headless=new agar lebih mirip browser asli
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    
    # User Agent wajib diset manual
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Sembunyikan flag otomatisasi
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option('useAutomationExtension', False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    
    # Script CDP untuk memalsukan navigator
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
    print("=== ROULETTE SCRAPER (GITHUB ACTION VERSION) ===")
    print(f"Target: {URL}")
    print(f"Output: {FILE_CSV}")
    
    driver = init_driver()
    
    try:
        print(f"[{time.strftime('%H:%M:%S')}] Mengambil data terbaru...")
        driver.get(URL)
        
        # Tunggu loading awal (sedikit lebih lama untuk GitHub Actions)
        time.sleep(10)
        
        print("Mencari section 'History of rounds'...")
        
        container = None
        
        # Coba cara 1: CSS Selector Spesifik
        try:
            container = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.live-game-page__block__results"))
            )
            print("✓ Container ditemukan (Selector 1)")
        except Exception:
            print("⚠ Selector 1 gagal, mencoba Selector 2...")
            
        # Coba cara 2: Class Name (jika cara 1 gagal)
        if not container:
            try:
                container = WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "live-game-page__block__content"))
                )
                print("✓ Container ditemukan (Selector 2)")
            except Exception as e:
                # Jika Gagal Total -> Ambil Screenshot untuk Debugging
                print("✗ GAGAL: Container tidak ditemukan sama sekali.")
                driver.save_screenshot("error_screenshot.png")
                with open("error_page.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                print("📸 Screenshot & HTML disimpan untuk debug artifact.")
                raise e

        # Ambil teks dari container
        container_text = container.text
        raw_numbers = extract_numbers_from_container(container_text)
        print(f"✓ Ditemukan {len(raw_numbers)} angka dalam container")
        
        if not raw_numbers:
            print("⚠ Container ditemukan tapi kosong!")
            driver.save_screenshot("empty_container.png")
            return

        # Ambil elemen individual untuk warna
        individual_elements = driver.find_elements(By.CSS_SELECTOR, "div.roulette-number")
        
        individual_data = []
        for el in individual_elements[:min(len(raw_numbers), len(individual_elements))]:
            text = el.text.strip()
            if text.isdigit():
                classes = el.get_attribute('class')
                individual_data.append({
                    'number': text,
                    'classes': classes
                })
        
        # Gabungkan data
        current_batch = []
        for i, num in enumerate(raw_numbers):
            if i >= len(individual_data):
                break
                
            data = get_roulette_stats(num)
            
            # Deteksi Warna
            classes = individual_data[i]['classes'].lower()
            if 'red' in classes: data['Warna'] = 'Merah'
            elif 'black' in classes: data['Warna'] = 'Hitam'
            elif 'green' in classes: data['Warna'] = 'Hijau'
            else:
                # Fallback manual
                n = int(num)
                if n == 0: data['Warna'] = 'Green'
                elif n in [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]: data['Warna'] = 'Merah'
                else: data['Warna'] = 'Hitam'
            
            data['WaktuScrape'] = time.strftime('%Y-%m-%d %H:%M:%S')
            current_batch.append(data)
        
        # Balik urutan untuk kronologis (Lama -> Baru)
        chronological_batch = list(reversed(current_batch))
        
        # --- PENCOCOKAN DATA ---
        last_recorded = get_last_recorded_data(FILE_CSV, limit=10)
        new_items_to_save = []
        
        if not last_recorded:
            new_items_to_save = chronological_batch
            print("\nFile CSV kosong/baru. Menyimpan semua data.")
        else:
            # Logika pencocokan sederhana (cek overlap)
            current_numbers = [str(item['Angka']) for item in current_batch]
            
            # Cari di mana data CSV terakhir muncul di data baru
            found_index = -1
            
            # Cek pola urutan sama
            for i in range(len(current_numbers) - len(last_recorded) + 1):
                if current_numbers[i:i+len(last_recorded)] == last_recorded:
                    found_index = i
                    break
            
            # Cek pola urutan terbalik (kadang website berubah urutan)
            if found_index == -1:
                reversed_last = list(reversed(last_recorded))
                for i in range(len(current_numbers) - len(reversed_last) + 1):
                    if current_numbers[i:i+len(reversed_last)] == reversed_last:
                        found_index = i
                        break
            
            if found_index > 0:
                # Ada data baru sebelum index yang cocok
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
        # Re-raise error supaya GitHub Action status-nya Failed
        raise e
        
    finally:
        driver.quit()
        print("\n✅ Driver ditutup.")

if __name__ == "__main__":
    main()
