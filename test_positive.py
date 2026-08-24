import asyncio
import httpx
import os
import json
import base64
import pandas as pd
import time
import cv2
import numpy as np
from pathlib import Path

async def main():
    upload_dir = Path("backend/uploads")
    upload_dir.mkdir(exist_ok=True, parents=True)
    brief_path = upload_dir / "current_brief.xlsx"

    # Tworzenie struktury CV_Assets
    cv_assets = Path("CV_Assets")
    pegi_dir = cv_assets / "RATINGS" / "PEGI"
    bong_dir = cv_assets / "BONG" / "16x9" / "Standard"
    pegi_dir.mkdir(parents=True, exist_ok=True)
    bong_dir.mkdir(parents=True, exist_ok=True)

    # Tworzenie małych obrazów-szablonów z konkretnym wzorem
    # PEGI (czerwony kwadrat z białym tekstem)
    img_pegi = np.zeros((50, 50, 3), dtype=np.uint8)
    img_pegi[:] = (0, 0, 255) # Czerwony w BGR
    cv2.putText(img_pegi, "18", (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)
    pegi_path = pegi_dir / "18_cropped.png"
    cv2.imwrite(str(pegi_path), img_pegi)

    # BONG (niebieski prostokąt)
    img_bong = np.zeros((30, 150, 3), dtype=np.uint8)
    img_bong[:] = (255, 0, 0) # Niebieski w BGR
    cv2.putText(img_bong, "BONG", (30, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)
    bong_path = bong_dir / "bong_cropped.png"
    cv2.imwrite(str(bong_path), img_bong)

    # Tworzenie "klatki wideo" która zawiera te elementy
    # BONG jest sprawdzane na "końcu" filmu. Rating na początku.
    # Musimy spreparować payload. Endpoint analyze-elements na końcu robi "bong_status = FOUND if has_bong else MISSING".
    # Spróbujemy trafić Rating (na starcie - timestamp 0.0) i ew. BONG w innym requestcie, lub oba.
    # Wysłanie current_time: 0.0 daje is_start=True.
    
    # Klatka główna z wklejonymi szablonami
    main_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    # Wklejamy PEGI na dole
    main_frame[900:950, 100:150] = img_pegi
    
    # Wklejamy BONG na środku
    main_frame[500:530, 800:950] = img_bong

    _, buffer = cv2.imencode('.png', main_frame)
    b64_img = "data:image/png;base64," + base64.b64encode(buffer).decode("utf-8")

    print("\n=== TEST POZYTYWNY: Cache Hit/Miss w analyze-elements ===")
    df = pd.DataFrame({
        "Col1": ["", "", "RATING", "PEGI"],
        "Col2": ["", "", "AGE", "18"],
        "Col3": ["", "", "BONG", "Standard"]
    })
    df.to_excel(brief_path, sheet_name="PL-PL", index=False)
    
    # Endpoint sprawdza BONG jeśli is_end=True, co wymaga timestamp >= duration - 2.0.
    # Zrobimy 2 testy: jeden na start (dla Rating) i jeden na end (dla Bong).
    payload_start = {
        "image_base64": b64_img,
        "file_id": 1,
        "filename": "video_PL-PL_1920x1080_15s.mp4",
        "timestamp": 0.0,
        "duration": 15.0,
        "sheet_name": "PL-PL"
    }

    payload_end = {
        "image_base64": b64_img,
        "file_id": 1,
        "filename": "video_PL-PL_1920x1080_15s.mp4",
        "timestamp": 14.0,
        "duration": 15.0,
        "sheet_name": "PL-PL"
    }

    async with httpx.AsyncClient(base_url="http://127.0.0.1:8006", timeout=30) as client:
        t0 = time.time()
        r1 = await client.post("/api/v1/analyze-elements", json=payload_start)
        t1 = time.time()
        
        with open("result_start.json", "w") as f:
            f.write(json.dumps(r1.json(), indent=2))
            
        r2 = await client.post("/api/v1/analyze-elements", json=payload_end)
        
        with open("result_end.json", "w") as f:
            f.write(json.dumps(r2.json(), indent=2))
        
        print(f"Start Frame Status: {r1.status_code}")
        print(f"End Frame Status: {r2.status_code}")
        
    print("DONE")

if __name__ == "__main__":
    asyncio.run(main())
