import os

SERVER = r'DAIKAHOAAAA\MSSQLSERVER01'
DATABASE = 'SmartGarden_Core'
CONN_STR = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER};DATABASE={DATABASE};Trusted_Connection=yes"

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.normpath(os.path.join(CURRENT_DIR, "..", "..", "AI_Models", "qwen_vlm.gguf"))
CLIP_PATH = os.path.normpath(os.path.join(CURRENT_DIR, "..", "..", "AI_Models", "mmproj.gguf"))