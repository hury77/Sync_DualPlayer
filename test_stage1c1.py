import asyncio
import httpx
import os
import json
import pandas as pd
from pathlib import Path

async def main():
    # 1. Stworzenie danych źródłowych
    copydeck_data = {
        "Source": ["Play now", "Buy now"],
        "PL-PL": ["Zagraj teraz", "Kup teraz"],
        "EN-US": ["Play now", "Buy now"]
    }
    df_copydeck = pd.DataFrame(copydeck_data)
    
    brief_data = {
        "Col1": ["", "", "RATING", "PEGI"],
        "Col2": ["", "", "AGE", "18"],
        "Col3": ["", "", "BONG", "Standard"]
    }
    df_brief = pd.DataFrame(brief_data)

    # Zapisz stary Copydeck
    df_copydeck.to_excel("old_copydeck.xlsx", index=False)
    
    # Zapisz stary Brief
    df_brief.to_excel("old_brief.xlsx", sheet_name="PL-PL", index=False)

    # Zapisz nowy konsolidowany Brief
    with pd.ExcelWriter("new_brief.xlsx") as writer:
        df_copydeck.to_excel(writer, sheet_name="COPY DECK", index=False)
        df_brief.to_excel(writer, sheet_name="PL-PL", index=False)

    print("Pliki wygenerowane.")

    async with httpx.AsyncClient(base_url="http://127.0.0.1:8003", timeout=30) as client:
        # TEST 1a: Upload starego Copydecku
        with open("old_copydeck.xlsx", "rb") as f:
            res_old_copydeck = await client.post("/api/v1/copydeck/parse", files={"file": ("old_copydeck.xlsx", f)})
        
        with open("result_old_copydeck.json", "w") as f:
            f.write(json.dumps(res_old_copydeck.json(), indent=2))
            
        print(f"Stary Copydeck Status: {res_old_copydeck.status_code}")

        # TEST 1b: Upload nowego Briefu (z wbudowanym copydeckiem)
        with open("new_brief.xlsx", "rb") as f:
            res_new_brief = await client.post("/api/v1/brief/upload", files={"file": ("new_brief.xlsx", f)})
            
        # Wyciągnij copydeck_data z odpowiedzi
        new_brief_json = res_new_brief.json()
        with open("result_new_copydeck.json", "w") as f:
            f.write(json.dumps(new_brief_json.get("copydeck_data", {}), indent=2))
            
        print(f"Nowy Brief Status: {res_new_brief.status_code}")
        print(f"Nowy Brief Zwrócił Copydeck: {'copydeck_data' in new_brief_json}")
        
        # TEST 2: Upload starego Briefu (bez copydecka)
        with open("old_brief.xlsx", "rb") as f:
            res_old_brief = await client.post("/api/v1/brief/upload", files={"file": ("old_brief.xlsx", f)})
            
        old_brief_json = res_old_brief.json()
        print(f"Stary Brief Status: {res_old_brief.status_code}")
        print(f"Stary Brief Zwrócił Copydeck: {'copydeck_data' in old_brief_json}")
        
    print("DONE")

if __name__ == "__main__":
    asyncio.run(main())
