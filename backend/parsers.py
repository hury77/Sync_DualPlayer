import re
import pandas as pd
import os
import zipfile
import xml.etree.ElementTree as ET
import cv2
import numpy as np

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

def extract_rating_image_aspect_ratio(brief_path: str, language_code: str) -> float:
    """
    Ekstrahuje obraz z kolumny A (w pobliżu wiersza 6) z arkusza Excel i zwraca jego proporcje (Szerokość/Wysokość).
    """
    try:
        with zipfile.ZipFile(brief_path, 'r') as z:
            namespaces = {
                'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
                'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
                'xdr': 'http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing',
                'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
                'rel': 'http://schemas.openxmlformats.org/package/2006/relationships'
            }
            workbook_xml = z.read('xl/workbook.xml')
            wb_root = ET.fromstring(workbook_xml)
            sheet_rId = None
            for sheet in wb_root.findall('.//main:sheet', namespaces):
                if sheet.attrib.get('name') == language_code:
                    sheet_rId = sheet.attrib.get(f"{{{namespaces['r']}}}id")
                    break
            if not sheet_rId: return None
            
            wb_rels_xml = z.read('xl/_rels/workbook.xml.rels')
            wb_rels_root = ET.fromstring(wb_rels_xml)
            sheet_path = None
            for rel in wb_rels_root.findall('rel:Relationship', namespaces):
                if rel.attrib.get('Id') == sheet_rId:
                    sheet_path = rel.attrib.get('Target')
                    break
            if not sheet_path: return None
            
            sheet_full_path = f"xl/{sheet_path}"
            sheet_xml = z.read(sheet_full_path)
            sheet_root = ET.fromstring(sheet_xml)
            drawing = sheet_root.find('.//main:drawing', namespaces)
            if drawing is None: return None
            drawing_rId = drawing.attrib.get(f"{{{namespaces['r']}}}id")
            
            sheet_name = sheet_path.split('/')[-1]
            sheet_rels_path = f"xl/worksheets/_rels/{sheet_name}.rels"
            sheet_rels_xml = z.read(sheet_rels_path)
            sheet_rels_root = ET.fromstring(sheet_rels_xml)
            drawing_path = None
            for rel in sheet_rels_root.findall('rel:Relationship', namespaces):
                if rel.attrib.get('Id') == drawing_rId:
                    drawing_path = rel.attrib.get('Target')
                    break
            if not drawing_path: return None
            
            if drawing_path.startswith('../'):
                drawing_full_path = f"xl/{drawing_path[3:]}"
            else:
                drawing_full_path = f"xl/worksheets/{drawing_path}"
                
            drawing_xml = z.read(drawing_full_path)
            drawing_root = ET.fromstring(drawing_xml)
            
            image_rId = None
            best_dist = 999
            for anchor in drawing_root.findall('.//xdr:twoCellAnchor', namespaces) + drawing_root.findall('.//xdr:oneCellAnchor', namespaces):
                from_marker = anchor.find('xdr:from', namespaces)
                if from_marker is not None:
                    col = from_marker.find('xdr:col', namespaces)
                    row = from_marker.find('xdr:row', namespaces)
                    if col is not None and row is not None:
                        try:
                            anchor_col = int(col.text)
                            anchor_row = int(row.text)
                            if anchor_col == 0:
                                dist = abs(anchor_row - 5)
                                if dist < best_dist and dist <= 2:
                                    blip = anchor.find('.//a:blip', namespaces)
                                    if blip is not None:
                                        best_dist = dist
                                        image_rId = blip.attrib.get(f"{{{namespaces['r']}}}embed")
                        except:
                            pass
            
            if not image_rId: return None
            
            drawing_name = drawing_full_path.split('/')[-1]
            drawing_rels_path = f"xl/drawings/_rels/{drawing_name}.rels"
            drawing_rels_xml = z.read(drawing_rels_path)
            drawing_rels_root = ET.fromstring(drawing_rels_xml)
            media_path = None
            for rel in drawing_rels_root.findall('rel:Relationship', namespaces):
                if rel.attrib.get('Id') == image_rId:
                    media_path = rel.attrib.get('Target')
                    break
                    
            if not media_path: return None
            
            if media_path.startswith('../'):
                media_full_path = f"xl/{media_path[3:]}"
            else:
                media_full_path = f"xl/drawings/{media_path}"
                
            img_bytes = z.read(media_full_path)
            img_np = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
            if img_np is not None:
                h, w = img_np.shape[:2]
                return float(w) / float(h)
    except Exception as e:
        print(f"Error extracting image AR: {e}")
    return None

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
            if col_name in ['RATING', 'AGE', 'BING', 'BONG'] or 'PHNL' in col_name:
                val = str(values.iloc[col_idx]).strip()
                if val.lower() == 'nan': val = ""
                req[col_name] = val
                
        # Zabezpieczenie: jeśli wiek jest liczbą z kropką (np. 12.0)
        if req.get("AGE") and req["AGE"].endswith(".0"):
            req["AGE"] = req["AGE"].replace(".0", "")
            
        # Ekstrakcja proporcji obrazka z pliku Excel
        ar = extract_rating_image_aspect_ratio(brief_path, language_code)
        if ar is not None:
            req["RATING_ASPECT_RATIO"] = ar
            
        return req
        
    except ValueError:
        # Prawdopodobnie brak zakładki o takiej nazwie
        raise ParserError(f"Nie znaleziono zakładki '{language_code}' w Briefie.")
    except Exception as e:
        raise ParserError(f"Błąd podczas analizy Briefu dla języka {language_code}: {e}")
