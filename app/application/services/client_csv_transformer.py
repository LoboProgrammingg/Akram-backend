"""Client CSV transformer service.

Handles:
- Reading .csv and .xlsx files with client data
- Normalizing column names (semicolon-delimited CSVs)
- Parsing dates (dd/mm/yyyy)
- Cleaning phone numbers
- Bulk inserting into PostgreSQL (clients table)
"""

import os
import re
import uuid
from datetime import datetime
from typing import Optional

import pandas as pd
from sqlalchemy.orm import Session

from app.config import get_settings
from app.domain.models.client import Client
from app.domain.models.client_upload import ClientUpload

settings = get_settings()

# Column mapping: spreadsheet column name → database field name
CLIENT_COLUMN_MAP = {
    "Cod. Cliente": "codigo",
    "COD. CLIENTE": "codigo",
    "Razão Social": "razao_social",
    "RAZÃO SOCIAL": "razao_social",
    "Razao Social": "razao_social",
    "Fantasia": "fantasia",
    "FANTASIA": "fantasia",
    "Cod. Rede": "cod_rede",
    "COD. REDE": "cod_rede",
    "Cidade": "cidade",
    "CIDADE": "cidade",
    "Estado": "estado",
    "ESTADO": "estado",
    "Telefone": "telefone",
    "TELEFONE": "telefone",
    "Celular": "celular",
    "CELULAR": "celular",
    "DTULTCOMPRA_GERAL": "dt_ult_compra",
    "dtultcompra_geral": "dt_ult_compra",
    "DtUltCompra_Geral": "dt_ult_compra",
}

# All valid DB column names for clients
VALID_CLIENT_COLS = set(CLIENT_COLUMN_MAP.values())


def _clean_column_name(col: str) -> str:
    """Strip whitespace from column names."""
    return col.strip() if isinstance(col, str) else col


def _parse_date(value) -> Optional[datetime]:
    """Parse date from multiple formats."""
    if value is None or pd.isna(value):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, pd.Timestamp):
        return value.date()
    s = str(value).strip()
    if not s or s in ("#REF!", "#ERROR!", "#N/A"):
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _clean_phone(value) -> Optional[str]:
    """Clean phone number, removing non-digits. Returns None for invalid entries."""
    if value is None or pd.isna(value):
        return None
    s = str(value).strip()
    if not s or s.upper() in ("VERIFICAR", "-", "N/A", "#REF!", "#ERROR!"):
        return None
    # Keep only digits
    digits = re.sub(r"\D", "", s)
    return digits if len(digits) >= 8 else None


def _rename_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename spreadsheet columns to DB field names using case-insensitive matching."""
    rename_map = {}
    for original_col, db_col in CLIENT_COLUMN_MAP.items():
        for df_col in df.columns:
            cleaned = _clean_column_name(str(df_col))
            if cleaned.upper() == original_col.upper():
                rename_map[df_col] = db_col
                break

    df = df.rename(columns=rename_map)

    # Keep only valid DB columns
    valid_cols = [c for c in df.columns if c in VALID_CLIENT_COLS]
    return df[valid_cols]


def _apply_parsing(df: pd.DataFrame) -> pd.DataFrame:
    """Apply data type parsing/cleaning to all client columns."""
    # Date column
    if "dt_ult_compra" in df.columns:
        df["dt_ult_compra"] = df["dt_ult_compra"].apply(_parse_date)

    # Integer columns
    for col in ("codigo", "cod_rede"):
        if col in df.columns:
            def _safe_int(x):
                if x is None or (isinstance(x, float) and pd.isna(x)):
                    return None
                s = str(x).strip()
                if not s or s in ("#REF!", "#ERROR!", "#N/A", ""):
                    return None
                try:
                    return int(float(s))
                except (ValueError, TypeError):
                    return None
            df[col] = df[col].apply(_safe_int)

    # Phone columns
    for col in ("telefone", "celular"):
        if col in df.columns:
            df[col] = df[col].apply(_clean_phone)

    # String columns
    for col in ("razao_social", "fantasia", "cidade", "estado"):
        if col in df.columns:
            df[col] = df[col].apply(
                lambda x: str(x).strip()
                if x is not None and not pd.isna(x) and str(x).strip() not in ("#REF!", "#ERROR!", "#N/A", "nan")
                else None
            )

    return df


def _detect_encoding(file_path: str) -> str:
    """Detect file encoding by trying common encodings."""
    for enc in ("utf-8", "latin-1", "cp1252", "iso-8859-1"):
        try:
            with open(file_path, "r", encoding=enc) as f:
                f.read(4096)  # Read a chunk to validate
            return enc
        except (UnicodeDecodeError, UnicodeError):
            continue
    return "latin-1"  # Safe fallback — never raises on any byte


def _detect_separator(file_path: str, encoding: str = "latin-1") -> str:
    """Detect CSV separator by reading the first line."""
    with open(file_path, "r", encoding=encoding, errors="replace") as f:
        first_line = f.readline()
    if ";" in first_line:
        return ";"
    if "\t" in first_line:
        return "\t"
    return ","


def _insert_clients(df: pd.DataFrame, db: Session, upload_id: int) -> int:
    """Bulk insert clients into DB."""
    clients = []
    for _, row in df.iterrows():
        client_data = row.where(pd.notnull(row), None).to_dict()
        client_data["upload_id"] = upload_id
        clients.append(Client(**client_data))

    db.bulk_save_objects(clients)
    db.commit()
    return len(clients)


def transform_client_csv_to_db(
    file_path: str,
    db: Session,
    original_name: str,
    uploaded_by: str = None,
) -> dict:
    """
    Read a client CSV, normalize, and insert to DB.
    Returns dict with upload_id, row_count, status.
    """
    upload = ClientUpload(
        filename=os.path.basename(file_path),
        original_name=original_name,
        uploaded_by=uploaded_by,
        status="processing",
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)

    try:
        encoding = _detect_encoding(file_path)
        sep = _detect_separator(file_path, encoding)
        df = pd.read_csv(file_path, encoding=encoding, sep=sep, on_bad_lines="skip")
        df.columns = [_clean_column_name(c) for c in df.columns]
        df = df.dropna(how="all")
        df = _rename_columns(df)
        df = _apply_parsing(df)

        count = _insert_clients(df, db, upload.id)

        upload.row_count = count
        upload.status = "completed"
        db.commit()

        return {
            "upload_id": upload.id,
            "row_count": count,
            "status": "completed",
        }

    except Exception as e:
        upload.status = "failed"
        upload.error_message = str(e)[:1000]
        db.commit()
        raise


def transform_client_xlsx_to_db(
    file_path: str,
    db: Session,
    original_name: str,
    uploaded_by: str = None,
) -> dict:
    """
    Transform a client XLSX file: read, normalize, insert to DB.
    """
    upload = ClientUpload(
        filename=os.path.basename(file_path),
        original_name=original_name,
        uploaded_by=uploaded_by,
        status="processing",
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)

    try:
        df = pd.read_excel(file_path, engine="openpyxl", sheet_name=0)
        df.columns = [_clean_column_name(c) for c in df.columns]

        # If first sheet is empty or just a date, try other sheets
        if len(df.columns) < 3:
            wb_sheets = pd.ExcelFile(file_path, engine="openpyxl").sheet_names
            for sheet in wb_sheets:
                test_df = pd.read_excel(file_path, engine="openpyxl", sheet_name=sheet)
                if len(test_df.columns) >= 5:
                    df = test_df
                    df.columns = [_clean_column_name(c) for c in df.columns]
                    break

        df = df.dropna(how="all")
        df = _rename_columns(df)
        df = _apply_parsing(df)

        count = _insert_clients(df, db, upload.id)

        upload.row_count = count
        upload.status = "completed"
        db.commit()

        return {
            "upload_id": upload.id,
            "row_count": count,
            "status": "completed",
        }

    except Exception as e:
        upload.status = "failed"
        upload.error_message = str(e)[:1000]
        db.commit()
        raise
