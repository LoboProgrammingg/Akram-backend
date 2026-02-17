"""XLSX → CSV transformer service.

Handles:
- Reading .xlsx and .csv files
- Normalizing column names
- Parsing dates (dd/mm/yyyy and datetime objects)
- Cleaning numeric fields (Brazilian format: 1.234,56)
- Exporting to CSV
- Bulk inserting into PostgreSQL
"""

import os
import re
import uuid
from datetime import datetime
from typing import Optional

import pandas as pd
from sqlalchemy.orm import Session

from app.config import get_settings
from app.domain.models.product import Product
from app.domain.models.upload import Upload

settings = get_settings()

# Column mapping: spreadsheet column name → database field name
COLUMN_MAP = {
    "Filial": "filial",
    "FILIAL": "filial",
    "Código": "codigo",
    "Descrição": "descricao",
    "Embalagem": "embalagem",
    "Estoque": "estoque",
    "Comprador": "comprador",
    "Quant.": "quantidade",
    "Validade": "validade",
    "Preço c/ST": "preco_com_st",
    "Status": "status",
    "UF": "uf",
    "Custo Médio": "custo_medio",
    "Custo Total": "custo_total",
    "Classe": "classe",
    "MULTIPLO": "multiplo",
    "VENDAS": "vendas",
}

# All valid DB column names
VALID_DB_COLS = set(COLUMN_MAP.values())


def _clean_column_name(col: str) -> str:
    """Strip whitespace from column names."""
    return col.strip() if isinstance(col, str) else col


def _parse_brazilian_number(value) -> Optional[float]:
    """Parse numbers in Brazilian format (e.g., '1.234,56' → 1234.56)."""
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if not s or s in ("#REF!", "#ERROR!", "#DIV/0!", "#N/A", "-"):
        return None
    # Remove R$ and whitespace
    s = re.sub(r"[R$\s]", "", s)
    # Brazilian format: replace dots (thousands) then comma (decimal)
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


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
    # Try dd/mm/yyyy
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _apply_parsing(df: pd.DataFrame) -> pd.DataFrame:
    """Apply data type parsing/cleaning to all columns."""
    # Numeric columns
    numeric_cols = ["estoque", "quantidade", "preco_com_st", "custo_medio", "custo_total", "multiplo", "vendas"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = df[col].apply(_parse_brazilian_number)

    # Date column
    if "validade" in df.columns:
        df["validade"] = df["validade"].apply(_parse_date)

    # Integer columns
    if "codigo" in df.columns:
        df["codigo"] = df["codigo"].apply(
            lambda x: int(float(x)) if x is not None and not pd.isna(x) and str(x).strip() not in ("#REF!", "#ERROR!", "#N/A") else None
        )

    # Status column
    if "status" in df.columns:
        df["status"] = df["status"].apply(
            lambda x: str(x).strip() if x is not None and not pd.isna(x) and str(x).strip() not in ("#REF!", "#ERROR!", "#N/A") else None
        )

    # String columns
    string_cols = ["filial", "descricao", "embalagem", "comprador", "uf", "classe"]
    for col in string_cols:
        if col in df.columns:
            df[col] = df[col].apply(
                lambda x: str(x).strip() if x is not None and not pd.isna(x) and str(x).strip() not in ("#REF!", "#ERROR!", "#N/A", "nan") else None
            )

    return df


def _rename_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename spreadsheet columns to DB field names using fuzzy matching."""
    rename_map = {}
    for original_col, db_col in COLUMN_MAP.items():
        for df_col in df.columns:
            cleaned = _clean_column_name(str(df_col))
            if cleaned.upper() == original_col.upper():
                rename_map[df_col] = db_col
                break

    df = df.rename(columns=rename_map)

    # Keep only valid DB columns
    valid_cols = [c for c in df.columns if c in VALID_DB_COLS]
    return df[valid_cols]


def _insert_products(df: pd.DataFrame, db: Session, upload_id: int) -> int:
    """Bulk insert products into DB."""
    products = []
    for _, row in df.iterrows():
        product_data = row.where(pd.notnull(row), None).to_dict()
        product_data["upload_id"] = upload_id
        products.append(Product(**product_data))

    db.bulk_save_objects(products)
    db.commit()
    return len(products)


def transform_xlsx_to_csv(
    file_path: str,
    db: Session,
    original_name: str,
    uploaded_by: str = None,
) -> dict:
    """
    Transform an XLSX file: read, normalize, save CSV, insert to DB.
    Returns dict with upload_id, row_count, csv_path.
    """
    upload = Upload(
        filename=os.path.basename(file_path),
        original_name=original_name,
        uploaded_by=uploaded_by,
        status="processing",
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)

    try:
        # Read XLSX — first sheet
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

        # Export to CSV
        os.makedirs(settings.EXPORT_DIR, exist_ok=True)
        csv_filename = f"{uuid.uuid4().hex}_{original_name.replace('.xlsx', '.csv')}"
        csv_path = os.path.join(settings.EXPORT_DIR, csv_filename)
        df.to_csv(csv_path, index=False, encoding="utf-8")

        # Insert into DB
        count = _insert_products(df, db, upload.id)

        upload.row_count = count
        upload.status = "completed"
        db.commit()

        return {
            "upload_id": upload.id,
            "row_count": count,
            "csv_path": csv_path,
            "status": "completed",
        }

    except Exception as e:
        upload.status = "failed"
        upload.error_message = str(e)[:1000]
        db.commit()
        raise


def _read_csv_with_encoding(file_path: str) -> pd.DataFrame:
    """Try to read CSV with multiple encodings (Brazilian Excel exports use Latin-1/Windows-1252)."""
    encodings = ["utf-8", "latin-1", "cp1252", "iso-8859-1"]
    separators = [",", ";"]
    
    for encoding in encodings:
        for sep in separators:
            try:
                df = pd.read_csv(file_path, encoding=encoding, sep=sep)
                # Check if we got valid columns (more than 1 column usually means correct separator)
                if len(df.columns) > 1:
                    return df
            except (UnicodeDecodeError, pd.errors.ParserError):
                continue
    
    # Last resort: try with error handling
    return pd.read_csv(file_path, encoding="latin-1", sep=";", on_bad_lines="skip")


def transform_csv_to_db(
    file_path: str,
    db: Session,
    original_name: str,
    uploaded_by: str = None,
) -> dict:
    """
    Read a CSV, normalize, and insert to DB.
    Supports multiple encodings (UTF-8, Latin-1, Windows-1252).
    """
    upload = Upload(
        filename=os.path.basename(file_path),
        original_name=original_name,
        uploaded_by=uploaded_by,
        status="processing",
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)

    try:
        df = _read_csv_with_encoding(file_path)
        df.columns = [_clean_column_name(c) for c in df.columns]
        df = df.dropna(how="all")
        df = _rename_columns(df)
        df = _apply_parsing(df)

        # Insert into DB
        count = _insert_products(df, db, upload.id)

        upload.row_count = count
        upload.status = "completed"
        db.commit()

        return {
            "upload_id": upload.id,
            "row_count": count,
            "csv_path": file_path,
            "status": "completed",
        }

    except Exception as e:
        upload.status = "failed"
        upload.error_message = str(e)[:1000]
        db.commit()
        raise
