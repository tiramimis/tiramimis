import time
import csv
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

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
    """Menyiapkan browser untuk GitHub Actions"""
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    
    # Untuk GitHub Actions
    opts.binary_location = "/usr/bin/chromium-browser"
    driver = webdriver.Chrome(options=opts)
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

def main():
    print("=== ROULETTE SCRAPER - GITHUB ACTIONS ===")
    print(f"Waktu: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    driver = init_driver()
    
    try:
        print("Mengambil data dari website...")
        driver.get(URL)
        time.sleep(5)  # Tunggu loading
        
        # Tunggu container muncul
        container = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.live-game-page__block__results"))
        )
        
        # Ambil teks container
        container_text = container.text
        
        # Ekstrak angka dari teks
        raw_numbers = []
        for word in container_text.split():
            if word.isdigit():
                raw_numbers.append(word)
        
        print(f"Ditemukan {len(raw_numbers)} angka")
        
        # Ambil elemen individual untuk warna
        individual_elements = driver.find_elements(By.CSS_SELECTOR, "div.roulette-number")
        
        # Parsing data
        current_batch = []
        for i, num in enumerate(raw_numbers[:len(individual_elements)]):
            data = get_roulette_stats(num)
            
            # Ambil warna dari element
            classes = individual_elements[i].get_attribute('class').lower()
            if 'red' in classes:
                data['Warna'] = 'Merah'
            elif 'black' in classes:
                data['Warna'] = 'Hitam'
            elif 'green' in classes:
                data['Warna'] = 'Hijau'
            
            data['WaktuScrape'] = time.strftime('%Y-%m-%d %H:%M:%S')
            current_batch.append(data)
        
        # Logika update dengan 10 angka terakhir
        last_recorded = get_last_recorded_data(FILE_CSV, limit=10)
        
        if last_recorded:
            current_numbers = [str(item['Angka']) for item in current_batch]
            
            # Cari pola
            found_index = -1
            for i in range(len(current_numbers) - len(last_recorded) + 1):
                if current_numbers[i:i+len(last_recorded)] == last_recorded:
                    found_index = i
                    break
            
            if found_index > 0:
                # Simpan data baru
                new_data = list(reversed(current_batch[:found_index]))
                save_to_csv(new_data)
                print(f"✓ Disimpan {len(new_data)} data baru")
            else:
                print("✓ Tidak ada data baru")
        else:
            # File CSV kosong, simpan semua
            save_to_csv(list(reversed(current_batch)))
            print("✓ Disimpan semua data (file baru)")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        driver.quit()
        print("Selesai")

if __name__ == "__main__":
    main()