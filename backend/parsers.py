import re
import pandas as pd
import os

class ParserError(Exception):
    pass

def parse_filename(filename: str) -> dict:
    """
    Ekstrahuje metadane z nazwy pliku wideo.
    Rzuca błąd ParserError jeśli brakuje kluczowych danych (Język lub Wymiary).
    """
    # 1. Szukamy języka. Wzorzec: otoczony '_' np. _PL_ lub _SE-SV_
    lang_match = re.search(r'_([A-Z]{2}(?:-[A-Z]{2})?)_', filename)
    if not lang_match:
        raise ParserError(f"Błąd krytyczny QA: Niezgodna konwencja nazewnictwa. Brak kodu języka w nazwie pliku: {filename}")
    language = lang_match.group(1)

    # 2. Szukamy wymiarów (np. 1080x1080, 1920x1080, 4K, 1080p)
    dim_match = re.search(r'_(\d+x\d+|4K|1080p)_', filename, re.IGNORECASE)
    if not dim_match:
        raise ParserError(f"Błąd krytyczny QA: Niezgodna konwencja nazewnictwa. Brak wymiarów w nazwie pliku: {filename}")
    dimension = dim_match.group(1)

    # 3. Szukamy czasu trwania (np. 15s, 30s)
    dur_match = re.search(r'_(\d+s)', filename)
    duration = dur_match.group(1) if dur_match else "Unknown"

    return {
        "language": language,
        "dimension": dimension,
        "duration": duration
    }

def get_requirements_from_brief(brief_path: str, language_code: str) -> dict:
    """
    Otwiera plik Brief XLSX, przechodzi do zakładki danego języka i odczytuje
    wymagania (Rating, Age, Bing, Bong) z wierszy 10-11.
    """
    if not os.path.exists(brief_path):
        raise ParserError(f"Nie odnaleziono pliku Brief: {brief_path}")
        
    try:
        # Odczytujemy arkusz dla konkretnego języka. Nrows=15 bo interesuje nas tylko 10-11 wiersz.
        df = pd.read_excel(brief_path, sheet_name=language_code, nrows=15)
        
        # Wiersz 10 w Excelu to indeks 9 w Pandas, jeśli nie ma headerów, ale my ładujemy z domyślnym header=0, 
        # więc wiersze mogą być przesunięte. Lepiej przeszukać DataFrame w poszukiwaniu słowa "RATING".
        
        target_row = None
        # Przeszukujemy wszystkie komórki by znaleźć gdzie jest nagłówek 'RATING'
        for i, row in df.iterrows():
            if 'RATING' in row.values:
                target_row = i
                break
                
        if target_row is None:
            raise ParserError(f"Nie znaleziono tabeli wymogów (RATING, AGE, BING, BONG) w zakładce {language_code}")
            
        # Wiersz z wartościami jest zazwyczaj zaraz pod nagłówkami
        headers = df.iloc[target_row].fillna('').astype(str).str.strip().str.upper()
        values = df.iloc[target_row + 1]
        
        # Tworzymy mapowanie
        req = {}
        for col_idx, col_name in enumerate(headers):
            if col_name in ['RATING', 'AGE', 'BING', 'BONG']:
                val = str(values.iloc[col_idx]).strip()
                if val.lower() == 'nan': val = ""
                req[col_name] = val
                
        # Zabezpieczenie: jeśli wiek jest liczbą z kropką (np. 12.0)
        if req.get("AGE") and req["AGE"].endswith(".0"):
            req["AGE"] = req["AGE"].replace(".0", "")
            
        return req
        
    except ValueError:
        # Prawdopodobnie brak zakładki o takiej nazwie
        raise ParserError(f"Nie znaleziono zakładki '{language_code}' w Briefie.")
    except Exception as e:
        raise ParserError(f"Błąd podczas analizy Briefu dla języka {language_code}: {e}")
