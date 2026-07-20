import cv2
import numpy as np
import os
from pathlib import Path

def crop_image(img_path, out_path):
    img = cv2.imread(str(img_path), cv2.IMREAD_UNCHANGED)
    if img is None:
        print(f"Błąd ładowania {img_path}")
        return False
        
    # Tworzymy kopię do analizy
    gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY) if img.shape[-1] == 4 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Odcinamy dolne 25% klatki na czas szukania bounding boxa (żeby wykluczyć teksty prawne - legal text)
    h, w = gray.shape
    cutoff = int(h * 0.75)
    
    mask = np.zeros_like(gray)
    mask[:cutoff, :] = gray[:cutoff, :]
    
    # Szukamy jasnych pikseli (logo jest białe/bardzo jasne)
    _, thresh = cv2.threshold(mask, 150, 255, cv2.THRESH_BINARY)
    
    # Znajdujemy koordynaty wszystkich białych pikseli
    coords = cv2.findNonZero(thresh)
    if coords is not None:
        x, y, bw, bh = cv2.boundingRect(coords)
        
        # Dodajemy mały margines (10 pikseli)
        pad = 20
        x = max(0, x - pad)
        y = max(0, y - pad)
        bw = min(w - x, bw + 2*pad)
        bh = min(h - y, bh + 2*pad)
        
        cropped = img[y:y+bh, x:x+bw]
        cv2.imwrite(str(out_path), cropped)
        print(f"Zapisano wykadrowany: {out_path} (Wymiary: {bw}x{bh})")
        return True
    else:
        print(f"Nie znaleziono jasnych punktów w {img_path}")
        return False

# Przeszukujemy BING i BONG
base_dir = Path("/Volumes/PL-EGplusww/Administrative and corporate files/DEPARTMENTS/QA/VITO/CV_Assets")
count = 0

for category in ["BING", "BONG"]:
    cat_dir = base_dir / category
    if not cat_dir.exists():
        continue
        
    for p in cat_dir.rglob("*.png"):
        if "_cropped" in p.name:
            continue
            
        out_name = p.stem + "_cropped" + p.suffix
        out_path = p.parent / out_name
        
        # Nawet jeśli istnieje, nadpisujemy, żeby zaktualizować (dla testu)
        success = crop_image(p, out_path)
        if success:
            count += 1

print(f"Zakończono. Wykadrowano {count} plików.")
