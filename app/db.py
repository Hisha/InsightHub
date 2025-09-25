import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import pandas as pd
import re
from datetime import datetime

# Load .env
load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")

DB_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
engine = create_engine(DB_URL)

def slugify(text):
    """Sanitize filename/table name parts."""
    text = re.sub(r"[^\w]+", "_", text)
    return text.strip("_").lower()

def insert_uploaded_file_metadata(filename, table_name, uploaded_by, header_row, row_count):
    """Insert metadata into uploaded_files and return the inserted ID."""
    with engine.begin() as conn:
        result = conn.execute(text("""
            INSERT INTO uploaded_files
            (filename, table_name, uploaded_by, header_row, row_count, uploaded_at)
            VALUES (:filename, :table_name, :uploaded_by, :header_row, :row_count, :uploaded_at)
        """), {
            "filename": filename,
            "table_name": table_name,
            "uploaded_by": uploaded_by,
            "header_row": header_row,
            "row_count": row_count,
            "uploaded_at": datetime.now(),
        })
        return result.lastrowid

def insert_dynamic_table(df: pd.DataFrame, table_name: str):
    """Create new table and insert parsed DataFrame."""
    df.to_sql(name=table_name, con=engine, if_exists="replace", index=False)
