"""Shared helpers for loading data and validating columns."""

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_csv(uploaded_file, sample_name: str) -> tuple[pd.DataFrame, str]:
    """Return (dataframe, source_label).

    Uses the uploaded file when one is supplied, otherwise falls back to the
    bundled sample in data/.
    """
    if uploaded_file is not None:
        return pd.read_csv(uploaded_file), f"uploaded: {uploaded_file.name}"

    path = DATA_DIR / sample_name
    return pd.read_csv(path), f"sample: {sample_name}"


def require_columns(df: pd.DataFrame, required: set[str], label: str) -> None:
    """Raise a readable error when expected columns are absent."""
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"{label} is missing required column(s): {', '.join(sorted(missing))}. "
            f"Found: {', '.join(df.columns)}"
        )


def to_csv_bytes(df: pd.DataFrame, index: bool = False) -> bytes:
    """Encode a dataframe for Streamlit download buttons."""
    return df.to_csv(index=index).encode("utf-8")
