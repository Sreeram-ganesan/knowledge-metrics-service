"""Data Loader Service - CSV loading and caching with pandas."""

import logging
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Coroutine, Optional

import pandas as pd

from app.core.config import get_settings
from app.core.exceptions import (
    VendorNotFoundError,
    NoDataInRangeError,
    FileTooLargeError,
)

logger = logging.getLogger(__name__)


class DataLoaderService:
    """
    Service for loading and accessing vendor metrics data.

    Responsibilities:
    - Load CSV data into a pandas DataFrame
    - Provide filtered views by vendor, date range, universe
    - Cache data to avoid repeated I/O

    Design decisions:
    - DataFrame is loaded once and cached (small dataset, static data)
    - Filtering methods return copies to prevent accidental mutation
    - Date parsing is done at load time for query efficiency
    """

    def __init__(self, csv_path: Optional[Path] = None):
        """
        Initialize the data loader.

        Args:
            csv_path: Path to CSV file. Defaults to config path.
        """
        self._csv_path = csv_path or get_settings().csv_path
        self._df: Optional[pd.DataFrame] = None

    def _load_data(self) -> pd.DataFrame:
        """Load CSV data into DataFrame with proper type parsing."""
        logger.info(f"Loading data from {self._csv_path}")
        df = pd.read_csv(
            self._csv_path,
            parse_dates=["date"],
            dtype={
                "vendor": "string",
                "universe": "string",
                "feature_x": "float64",
                "feature_y": "float64",
                "signal_strength": "float64",
                "drawdown_flag": "int64",
            },
        )
        # Sort by vendor and date for consistent ordering
        df = df.sort_values(["vendor", "date"]).reset_index(drop=True)

        # Log dataset summary (without sensitive data)
        vendor_count = df["vendor"].nunique()
        universe_count = df["universe"].nunique()
        date_min, date_max = df["date"].min(), df["date"].max()
        logger.info(
            f"Data loaded: {len(df)} records, {vendor_count} vendors, "
            f"{universe_count} universes, date range {date_min.date()} to {date_max.date()}"
        )
        return df

    @property
    def dataframe(self) -> pd.DataFrame:
        """
        Get the full DataFrame (lazy-loaded and cached).

        Returns:
            pd.DataFrame: Copy of the vendor metrics data.
        """
        if self._df is None:
            self._df = self._load_data()
        return self._df.copy()

    def get_vendors(self) -> list[str]:
        """Get list of unique vendor names."""
        if self._df is None:
            self._df = self._load_data()
        vendors: list[str] = self._df["vendor"].unique().tolist()
        return vendors

    def get_universes(self) -> list[str]:
        """Get list of unique universe/asset class names."""
        if self._df is None:
            self._df = self._load_data()
        universes: list[str] = self._df["universe"].unique().tolist()
        return universes

    def get_date_range(self) -> tuple[date, date]:
        """Get the min and max dates in the dataset."""
        if self._df is None:
            self._df = self._load_data()
        return (
            self._df["date"].min().date(),
            self._df["date"].max().date(),
        )

    def get_vendor_data(
        self,
        vendor: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> pd.DataFrame:
        """
        Get data for a specific vendor with optional date filtering.

        Args:
            vendor: Vendor name (case-sensitive).
            start_date: Include data from this date onwards.
            end_date: Include data up to and including this date.

        Returns:
            pd.DataFrame: Filtered data for the vendor.

        Raises:
            ValueError: If vendor is not found.
        """
        logger.debug(
            f"Getting vendor data: vendor=***, "
            f"start_date={start_date}, end_date={end_date}"
        )

        if self._df is None:
            self._df = self._load_data()

        df = self._df[self._df["vendor"] == vendor].copy()

        if df.empty:
            available = self._df["vendor"].unique().tolist()
            logger.warning("Vendor not found (requested vendor hidden for privacy)")
            raise VendorNotFoundError(vendor=vendor, available=available)

        if start_date:
            df = df[df["date"] >= pd.Timestamp(start_date)]
        if end_date:
            df = df[df["date"] <= pd.Timestamp(end_date)]

        # raise NoDataInRangeError if no data in range
        if df.empty:
            logger.warning(
                f"No data in range: start_date={start_date}, end_date={end_date}"
            )
            raise NoDataInRangeError(
                start_date=str(start_date) if start_date else "N/A",
                end_date=str(end_date) if end_date else "N/A",
            )

        logger.debug(f"Returning {len(df)} records for vendor query")
        return df.reset_index(drop=True)

    def get_data_by_universe(self, universe: str) -> pd.DataFrame:
        """
        Get all data for a specific universe/asset class.

        Args:
            universe: Universe name (e.g., 'Equities', 'FX', 'Macro').

        Returns:
            pd.DataFrame: Filtered data for the universe.
        """
        if self._df is None:
            self._df = self._load_data()
        return self._df[self._df["universe"] == universe].copy()

    def get_data_by_date_range(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> pd.DataFrame:
        """
        Get all data within a date range.

        Args:
            start_date: Include data from this date onwards.
            end_date: Include data up to and including this date.

        Returns:
            pd.DataFrame: Filtered data within the date range.
        """
        if self._df is None:
            self._df = self._load_data()

        df = self._df.copy()

        if start_date:
            df = df[df["date"] >= pd.Timestamp(start_date)]
        if end_date:
            df = df[df["date"] <= pd.Timestamp(end_date)]

        if df.empty:
            raise NoDataInRangeError(
                start_date=str(start_date) if start_date else "N/A",
                end_date=str(end_date) if end_date else "N/A",
            )

        return df.reset_index(drop=True)

    def get_drawdown_periods(self, vendor: Optional[str] = None) -> pd.DataFrame:
        """
        Get data points flagged as drawdown/stress periods.

        Args:
            vendor: Optional vendor filter.

        Returns:
            pd.DataFrame: Rows where drawdown_flag == 1.
        """
        if self._df is None:
            self._df = self._load_data()

        df = self._df[self._df["drawdown_flag"] == 1].copy()

        if vendor:
            df = df[df["vendor"] == vendor]

        return df.reset_index(drop=True)

    def reload(self) -> None:
        """Force reload of data from CSV (clears cache)."""
        logger.info("Reloading data from CSV (cache cleared)")
        self._df = None
        self._df = self._load_data()

    def load_data_from_bytes(self, data: bytes) -> None:
        """
        Load data from CSV bytes (for testing or dynamic loading).

        Args:
            data: CSV data in bytes.
        """
        from io import BytesIO

        logger.debug(f"Loading data from bytes: {len(data)} bytes")
        self._df = pd.read_csv(
            BytesIO(data),
            parse_dates=["date"],
            dtype={
                "vendor": "string",
                "universe": "string",
                "feature_x": "float64",
                "feature_y": "float64",
                "signal_strength": "float64",
                "drawdown_flag": "int64",
            },
        )
        # Sort by vendor and date for consistent ordering
        self._df = self._df.sort_values(["vendor", "date"]).reset_index(drop=True)
        logger.info(f"Data loaded from bytes: {len(self._df)} records")

    async def load_data_from_upload(
        self,
        read_chunk: "Callable[[int], Coroutine[Any, Any, bytes]]",
        content_type: Optional[str],
        filename: Optional[str],
        max_file_size: int = 10 * 1024 * 1024,
        chunk_size: int = 1024 * 1024,
    ) -> dict:
        """
        Load data from an uploaded file with validations.

        Production-ready upload with:
        - File size limit validation
        - Content-type validation
        - Filename extension validation
        - Streaming read (doesn't load entire file at once)

        Args:
            read_chunk: Async callable that reads chunks from the file.
            content_type: MIME type of the uploaded file.
            filename: Name of the uploaded file.
            max_file_size: Maximum allowed file size in bytes (default 10MB).
            chunk_size: Size of chunks to read at a time (default 1MB).

        Returns:
            dict with upload results (total_records, vendors, file_size_bytes).

        Raises:
            ValueError: If validation fails or file processing fails.
        """
        allowed_content_types = ["text/csv", "application/csv", "text/plain"]

        logger.info(
            f"Processing file upload: filename={filename}, "
            f"content_type={content_type}, max_size={max_file_size // (1024 * 1024)}MB"
        )

        # 1. Validate content type
        if content_type not in allowed_content_types:
            logger.warning(f"Upload rejected: invalid content type {content_type}")
            raise ValueError(
                f"Invalid file type: {content_type}. Allowed: {allowed_content_types}"
            )

        # 2. Validate filename extension
        if filename and not filename.lower().endswith(".csv"):
            logger.warning("Upload rejected: invalid file extension")
            raise ValueError("Invalid file extension. Only .csv files allowed.")

        # 3. Read file with size limit (streaming read)
        contents = b""
        bytes_read = 0
        while chunk := await read_chunk(chunk_size):
            bytes_read += len(chunk)
            if bytes_read > max_file_size:
                logger.warning(f"Upload rejected: file too large ({bytes_read} bytes)")
                raise FileTooLargeError(max_size_mb=max_file_size // (1024 * 1024))
            contents += chunk

        logger.debug(f"Read {bytes_read} bytes from upload")

        # 4. Validate not empty
        if not contents:
            logger.warning("Upload rejected: empty file")
            raise ValueError("Empty file")

        # 5. Process the file
        self.load_data_from_bytes(contents)

        result = {
            "total_records": len(self.dataframe),
            "vendors": self.get_vendors(),
            "file_size_bytes": bytes_read,
        }
        logger.info(
            f"Upload successful: {result['total_records']} records, "
            f"{len(result['vendors'])} vendors, {bytes_read} bytes"
        )
        return result


# Singleton instance for dependency injection
@lru_cache(maxsize=1)
def get_data_loader() -> DataLoaderService:
    """Get cached DataLoaderService instance."""
    return DataLoaderService()
