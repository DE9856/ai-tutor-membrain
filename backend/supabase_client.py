from supabase import create_client
import os
from dotenv import load_dotenv

# Load env variables
load_dotenv()

# Get values
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

if not url or not key:
	raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY in environment")

# Create client
supabase = create_client(url, key)