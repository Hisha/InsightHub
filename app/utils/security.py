import os
from passlib.hash import bcrypt
from dotenv import load_dotenv

load_dotenv()

USERNAME = os.getenv("INSIGHTHUB_USERNAME", "admin")
PASSWORD_HASH = os.getenv("INSIGHTHUB_PASSWORD_HASH", "")
SESSION_SECRET = os.getenv("SESSION_SECRET", "change-this")

def verify_credentials(username: str, password: str) -> bool:
    return (
        username == USERNAME and
        bcrypt.verify(password, PASSWORD_HASH)
    )
