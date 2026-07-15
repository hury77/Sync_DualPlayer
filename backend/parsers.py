import re
import pandas as pd
import os
import zipfile
import xml.etree.ElementTree as ET

class ParserError(Exception):
    pass

def extract_rating_icon_from_brief(brief_path: str, language_code: str) -> bytes:
    """
    Wyciąga ikonę ratingu wklejoną w kolumnie A (wiersze 5-8) z zakładki danego języka.
    Parsuje wewnętrzną strukturę ZIP pliku .xlsx (drawingN.xml + rels).
    Zwraca surowe bajty PNG ikony lub None jeśli nie znaleziono.
    """
    if not os.path.exists(brief_path):
        return None

    ns_xdr = 'http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing'
    ns_a = 'http://schemas.openxmlformats.org/drawingml/2006/main'
    ns_r = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'

    try:
        import openpyxl
        wb = openpyxl.load_workbook(brief_path, read_only=True)
        sheet_names = wb.sheetnames
        wb.close()
    except Exception:
        return None

    # Znajdź indeks arkusza (1-based) na podstawie nazwy języka
    sheet_index = None
    for idx, name in enumerate(sheet_names):
        if name == language_code:
            sheet_index = idx + 1
            break
    if sheet_index is None:
        return None

    try:
        with zipfile.ZipFile(brief_path, 'r') as z:
            # 1. Znajdź drawing powiązany z tym arkuszem
            rels_path = f'xl/worksheets/_rels/sheet{sheet_index}.xml.rels'
            try:
                rels_xml = z.read(rels_path).decode()
            except KeyError:
                return None

            rels_root = ET.fromstring(rels_xml)
            drawing_file = None
            for rel in rels_root:
                if 'drawing' in rel.get('Target', ''):
                    drawing_file = rel.get('Target').replace('../drawings/', '')
                    break
            if not drawing_file:
                return None

            # 2. Parsuj powiązania drawing -> media
            drawing_rels_path = f'xl/drawings/_rels/{drawing_file}.rels'
            rid_to_media = {}
            try:
                dr_rels = z.read(drawing_rels_path).decode()
                dr_root = ET.fromstring(dr_rels)
                for rel in dr_root:
                    rid = rel.get('Id')
                    target = rel.get('Target', '')
                    if 'image' in target:
                        rid_to_media[rid] = target.replace('../media/', '')
            except KeyError:
                return None

            # 3. Parsuj drawing XML i szukaj kotwicy w kolumnie A, wiersze 4-7 (Excel 5-8)
            drawing_xml = z.read(f'xl/drawings/{drawing_file}').decode()
            root = ET.fromstring(drawing_xml)

            for anchor in root:
                from_el = anchor.find(f'{{{ns_xdr}}}from')
                if from_el is None:
                    continue
                col_el = from_el.find(f'{{{ns_xdr}}}col')
                row_el = from_el.find(f'{{{ns_xdr}}}row')
                if col_el is None or row_el is None:
                    continue

                col = int(col_el.text)
                row = int(row_el.text)

                # Szukamy w kolumnie A (col=0), wiersze 4-7 (Excel 5-8)
                if col == 0 and 4 <= row <= 7:
                    # Szukaj blipa z embed ref
                    for blip in anchor.iter(f'{{{ns_a}}}blip'):
                        embed = blip.get(f'{{{ns_r}}}embed')
                        if embed and embed in rid_to_media:
                            media_file = rid_to_media[embed]
                            return z.read(f'xl/media/{media_file}')

    except Exception:
        return None

    return None

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
        expected_headers = ['RATING', 'AGE', 'BING', 'BONG']
        # Przeszukujemy wszystkie komórki by znaleźć gdzie są nagłówki wymogów
        for i, row in df.iterrows():
            row_vals = [str(v).strip().upper() for v in row.values]
            if any(v in expected_headers or 'PHNL' in v for v in row_vals):
                target_row = i
                break
                
        if target_row is None:
            raise ParserError(f"Nie znaleziono tabeli wymogów (RATING, AGE, BING, BONG, PHNL) w zakładce {language_code}")
            
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
            elif 'PHNL' in col_name:
                val = str(values.iloc[col_idx]).strip()
                if val.lower() == 'nan': val = ""
                req['PHNL'] = val
                
        # Zabezpieczenie: jeśli wiek jest liczbą z kropką (np. 12.0)
        if req.get("AGE") and req["AGE"].endswith(".0"):
            req["AGE"] = req["AGE"].replace(".0", "")
            
        return req
        
    except ValueError:
        # Prawdopodobnie brak zakładki o takiej nazwie
        raise ParserError(f"Nie znaleziono zakładki '{language_code}' w Briefie.")
    except Exception as e:
        raise ParserError(f"Błąd podczas analizy Briefu dla języka {language_code}: {e}")
