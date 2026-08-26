from pydantic import BaseModel
from typing import List, Optional, Dict

class FileUploadResponse(BaseModel):
    file_id: int

class FileMetadata(BaseModel):
    transcode_progress: Optional[int] = None
    conversion_time: Optional[float] = None

class FileStatusResponse(BaseModel):
    is_processed: bool
    processing_error: Optional[str] = None
    file_metadata: FileMetadata

class DeleteFileResponse(BaseModel):
    status: str
    detail: str

class UploadBriefResponse(BaseModel):
    success: bool
    message: str
    copydeck_data: Optional[Dict] = None

class ClearAssetsResponse(BaseModel):
    success: bool
    message: str

class DebugAssetsResponse(BaseModel):
    p1_exists: bool
    cv_assets_dir: str
    bing_std_path: str
    bing_std_exists: bool
    bing_imread_loaded: bool
    bing_imdecode_loaded: bool
    bing_imdecode_shape: Optional[list] = None
    imdecode_err: Optional[str] = None
    current_working_dir: str

class CopydeckParseResponse(BaseModel):
    success: bool
    languages: Optional[List[str]] = None
    data: Optional[Dict[str, Dict[str, str]]] = None
    error: Optional[str] = None

class AnalyzeFrameRequest(BaseModel):
    image_base64: str
    filename: str
    country_code: Optional[str] = None
    timestamp: Optional[float] = None
