import os
from supabase import create_client, Client
import dotenv

dotenv.load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

users = (
    supabase.table("users")
    .select("*")
    .execute()
)
for user in users.data:
    print(user)