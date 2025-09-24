import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
import pandas as pd

# Load from .env file
load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")

# Build connection URL
DB_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"

# Create SQLAlchemy engine
engine = create_engine(DB_URL)

def insert_dataframe(df: pd.DataFrame, table_name: str):
    """Insert a DataFrame into a specified MariaDB table."""
    df.to_sql(name=table_name, con=engine, if_exists="append", index=False)
