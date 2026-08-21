import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    cv_assets_path: str = "/Volumes/PL-EGplusww/Administrative and corporate files/DEPARTMENTS/QA/VITO/CV_Assets"

    model_config = SettingsConfigDict(
        # The latter file overwrites the former if both exist.
        env_file=[os.path.expanduser("~/.sync_dualplayer.env"), ".env"],
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
