import asyncio
import httpx
import os
import shutil

async def main():
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8004", timeout=10) as client:
        # TEST 2: clear_qa_assets
        print("=== TEST clear_qa_assets ===")
        # Create brief path
        brief_path = "uploads/current_brief.xlsx"
        os.makedirs("uploads", exist_ok=True)
        with open(brief_path, "w") as f:
            f.write("fake")
        # Lock file by making directory read only? Or chmod file to 000. Wait, root can still delete it.
        # It's better to just chmod the directory to not allow deletion.
        os.chmod("uploads", 0o555)
        
        try:
            r = await client.post("/api/v1/clear-qa-assets")
            print("clear-qa-assets:", r.status_code, r.json())
        except Exception as e:
            print(e)
            
        os.chmod("uploads", 0o755)

        # TEST 3: upload_file error
        print("=== TEST upload_file processing error ===")
        os.chmod("uploads", 0o555) # Cannot write to uploads
        try:
            files = {'file': ('test.mp4', b'dummy content', 'video/mp4')}
            data = {'file_type': 'video'}
            r = await client.post("/api/v1/files/upload", data=data, files=files)
            print("upload status:", r.status_code, r.text)
            if r.status_code == 200:
                file_id = r.json()["file_id"]
                await asyncio.sleep(0.5)
                r2 = await client.get(f"/api/v1/files/{file_id}")
                print("status check:", r2.status_code, r2.json())
        except Exception as e:
            print(e)
            
        os.chmod("uploads", 0o755)
        
        # TEST 4: invalid base64 in analyze_elements
        print("=== TEST analyze_elements imdecode ===")
        try:
            payload = {
                "image_base64": "data:image/png;base64,badbase64notanimage",
                "filename": "video_FR_1080x1080_15s.mp4",
                "is_start": True
            }
            r = await client.post("/api/v1/analyze-elements", json=payload)
            print("analyze status:", r.status_code, r.text)
        except Exception as e:
            print(e)

        # TEST 5: exception bomb logging
        print("=== TEST exception bomb ===")
        # We will lock /tmp/vito_error.log if we can, or just /tmp. Usually we can't lock /tmp.
        # But we can create a directory with the same name!
        if os.path.exists("/tmp/vito_error.log"):
            if os.path.isdir("/tmp/vito_error.log"):
                pass
            else:
                os.remove("/tmp/vito_error.log")
                os.makedirs("/tmp/vito_error.log")
        else:
            os.makedirs("/tmp/vito_error.log")
        
        try:
            # send payload that causes an error in analyze_elements (missing expected rating base64 etc. which causes it to throw an exception down the line)
            # Actually, `analyze-elements` catches Exception and tries to log to `/tmp/vito_error.log`.
            payload = {
                "image_base64": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=",
                "filename": "video_FR_1080x1080_15s.mp4",
                "is_start": True
            }
            r = await client.post("/api/v1/analyze-elements", json=payload)
            print("bomb status:", r.status_code, r.text)
        except Exception as e:
            print(e)
            
        shutil.rmtree("/tmp/vito_error.log", ignore_errors=True)

if __name__ == "__main__":
    asyncio.run(main())
