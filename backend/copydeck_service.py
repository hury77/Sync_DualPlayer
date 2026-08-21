import io
import pandas as pd
from fastapi import UploadFile

async def process_copydeck_file(file: UploadFile) -> dict:
    try:
        contents = await file.read()
        
        # Read excel file
        # We try to read it assuming headers might be on row 1 or 2
        # A robust way is to read the whole thing and find the header row containing "Source"
        df = pd.read_excel(io.BytesIO(contents), header=None)
        
        # Find the header row (the one that contains actual language names)
        header_row_idx = 0
        for idx, row in df.iterrows():
            row_str = row.astype(str).str.lower()
            
            # If row contains common language names, it's the right header
            if row_str.str.contains('polish|french|spanish|german|italian|portuguese|english|dutch|swedish|norwegian|danish|finnish').any():
                header_row_idx = idx
                break
                
            # Fallback to 'source' if we haven't found anything better yet
            if row_str.str.contains('source').any() or row_str.str.contains('language').any():
                header_row_idx = idx
                # Do NOT break immediately. The NEXT row might contain the actual languages!
                
        # Re-read with correct header
        df = pd.read_excel(io.BytesIO(contents), header=header_row_idx)
        
        # Clean column names
        df.columns = df.columns.astype(str).str.strip()
        
        # If 'Source' column is not found, take the first column as source
        source_col = None
        for col in df.columns:
            if 'source' in col.lower():
                source_col = col
                break
                
        if not source_col:
            source_col = df.columns[0]
            
        result_dict = {}
        # Iterate over all other columns treating them as languages
        for col in df.columns:
            if col == source_col or 'unnamed' in col.lower():
                continue
                
            # Build dictionary for this language
            lang_dict = {}
            for _, row in df.iterrows():
                src_val = str(row[source_col]).strip() if pd.notna(row[source_col]) else ""
                tgt_val = str(row[col]).strip() if pd.notna(row[col]) else ""
                
                if src_val and tgt_val and src_val.lower() != 'nan' and tgt_val.lower() != 'nan':
                    lang_dict[src_val] = tgt_val
                    
            if lang_dict:
                # Use first line or word as language name if there are multiple lines in header
                clean_col_name = col.split('\\n')[0].split('\\r')[0].strip()
                result_dict[clean_col_name] = lang_dict
                
        return {"success": True, "languages": list(result_dict.keys()), "data": result_dict}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}
