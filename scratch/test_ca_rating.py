import sys
import os
from pathlib import Path
sys.path.append('/Users/hubert.rycaj/Documents/Sync_DualPlayer/backend')
from parsers import get_requirements_from_brief

brief_path = "/Users/hubert.rycaj/Documents/Sync_DualPlayer/backend/uploads/current_brief.xlsx"
try:
    reqs = get_requirements_from_brief(brief_path, "CA-FR")
    print("Requirements from Excel for CA-FR:", reqs)
except Exception as e:
    print("Error:", e)
