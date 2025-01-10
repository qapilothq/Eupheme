from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import os
import base64
from urllib.parse import urlparse
from static_a11y_framework import StaticAccessibilityAnalyzer

app = FastAPI()

class AccessibilityCheckRequest(BaseModel):
    xml_url: str
    image_url: str

def get_file_content(file_path_or_url: str, is_image: bool = False) -> str:
    if file_path_or_url.startswith(('http://', 'https://')):
        # It's a URL
        try:
            response = requests.get(file_path_or_url)
            response.raise_for_status()
            content = response.content
        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=400, detail=f"Error fetching file from URL: {e}")
    else:
        # It's a local file path
        if not os.path.exists(file_path_or_url):
            raise HTTPException(status_code=400, detail=f"File not found: {file_path_or_url}")
        try:
            with open(file_path_or_url, 'rb') as file:
                content = file.read()
        except IOError as e:
            raise HTTPException(status_code=400, detail=f"Error reading file: {e}")

    if is_image:
        # Return base64-encoded string for images
        return base64.b64encode(content).decode('utf-8')
    else:
        # Return string for XML content
        return content.decode('utf-8')

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/invoke")
async def check_accessibility_endpoint(request_body: AccessibilityCheckRequest):
    xml_content = get_file_content(request_body.xml_url)
    image_content_base64 = get_file_content(request_body.image_url, is_image=True)

    # Extract image name without extension
    parsed_url = urlparse(request_body.image_url)
    image_name = os.path.splitext(os.path.basename(parsed_url.path))[0]

    analyzer = StaticAccessibilityAnalyzer(image_content_base64, xml_content, image_name)
    return analyzer.run_analysis()
    

def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()