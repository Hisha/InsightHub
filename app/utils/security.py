import os
from dotenv import load_dotenv
from passlib.context import CryptContext

load_dotenv()

# Config from .env
USERNAME = os.getenv("INSIGHTHUB_USERNAME", "admin")
PASSWORD_HASH = os.getenv("INSIGHTHUB_PASSWORD_HASH", "")
SESSION_SECRET = os.getenv("SESSION_SECRET", "change-this")

# Passlib context (uses bcrypt under the hood)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_credentials(username: str, password: str) -> bool:
    """
    Returns True only if username matches and password verifies against the stored hash.
    """
    if not PASSWORD_HASH:
        return False
    return username == USERNAME and pwd_context.verify(password, PASSWORD_HASH)

# Optional helper if you want to generate hashes from inside the app
def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)
