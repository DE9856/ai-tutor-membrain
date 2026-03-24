import os
from dotenv import load_dotenv

load_dotenv()

MEMBRAIN_API_KEY = os.getenv("MEMBRAIN_API_KEY")
MEMBRAIN_BASE_URL = os.getenv("MEMBRAIN_BASE_URL")