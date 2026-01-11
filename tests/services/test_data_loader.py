"""Unit tests for DataLoaderService."""

from datetime import date

import pytest

from app.core.exceptions import (
    VendorNotFoundError,
    NoDataInRangeError,
    FileTooLargeError,
)
from app.services.data_loader import DataLoaderService


# =============================================================================
# Fixtures
# =============================================================================

SAMPLE_CSV = b"""date,vendor,universe,feature_x,feature_y,signal_strength,drawdown_flag
2023-01-01,Vendor_A,Equities,1.0,2.0,0.5,0
2023-01-02,Vendor_A,Equities,1.5,2.5,0.6,1
2023-01-01,Vendor_B,FX,0.8,1.8,0.4,0
2023-01-02,Vendor_B,FX,0.9,1.9,0.45,0
"""


@pytest.fixture
def data_loader():
    """Create a DataLoaderService loaded with sample data."""
    loader = DataLoaderService()
    loader.load_data_from_bytes(SAMPLE_CSV)
    return loader


# =============================================================================
# Tests
# =============================================================================


class TestDataLoaderBasics:
    """Test basic data access methods."""

    def test_dataframe_returns_copy(self, data_loader: DataLoaderService):
        """Dataframe property returns a copy to prevent mutation."""
        df1 = data_loader.dataframe
        df2 = data_loader.dataframe
        assert df1 is not df2
        assert len(df1) == 4

    def test_get_vendors(self, data_loader: DataLoaderService):
        """Get unique vendor names."""
        vendors = data_loader.get_vendors()
        assert set(vendors) == {"Vendor_A", "Vendor_B"}

    def test_get_universes(self, data_loader: DataLoaderService):
        """Get unique universe names."""
        universes = data_loader.get_universes()
        assert set(universes) == {"Equities", "FX"}

    def test_get_date_range(self, data_loader: DataLoaderService):
        """Get min and max dates."""
        start, end = data_loader.get_date_range()
        assert start == date(2023, 1, 1)
        assert end == date(2023, 1, 2)


class TestVendorData:
    """Test vendor-specific data retrieval."""

    def test_get_vendor_data(self, data_loader: DataLoaderService):
        """Get data for a specific vendor."""
        df = data_loader.get_vendor_data("Vendor_A")
        assert len(df) == 2
        assert all(df["vendor"] == "Vendor_A")

    def test_get_vendor_data_with_date_filter(self, data_loader: DataLoaderService):
        """Filter vendor data by date range."""
        df = data_loader.get_vendor_data(
            "Vendor_A",
            start_date=date(2023, 1, 2),
            end_date=date(2023, 1, 2),
        )
        assert len(df) == 1

    def test_get_vendor_data_not_found(self, data_loader: DataLoaderService):
        """Raise error for unknown vendor."""
        with pytest.raises(VendorNotFoundError):
            data_loader.get_vendor_data("Unknown_Vendor")

    def test_get_vendor_data_no_data_in_range(self, data_loader: DataLoaderService):
        """Raise error when no data in date range."""
        with pytest.raises(NoDataInRangeError):
            data_loader.get_vendor_data(
                "Vendor_A",
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 2),
            )


class TestFiltering:
    """Test filtering methods."""

    def test_get_data_by_universe(self, data_loader: DataLoaderService):
        """Filter by universe."""
        df = data_loader.get_data_by_universe("Equities")
        assert len(df) == 2
        assert all(df["universe"] == "Equities")

    def test_get_data_by_date_range(self, data_loader: DataLoaderService):
        """Filter by date range."""
        df = data_loader.get_data_by_date_range(
            start_date=date(2023, 1, 2),
        )
        assert len(df) == 2

    def test_get_data_by_date_range_no_data(self, data_loader: DataLoaderService):
        """Raise error when no data in range."""
        with pytest.raises(NoDataInRangeError):
            data_loader.get_data_by_date_range(
                start_date=date(2025, 1, 1),
            )

    def test_get_drawdown_periods(self, data_loader: DataLoaderService):
        """Get rows with drawdown flag set."""
        df = data_loader.get_drawdown_periods()
        assert len(df) == 1
        assert all(df["drawdown_flag"] == 1)

    def test_get_drawdown_periods_by_vendor(self, data_loader: DataLoaderService):
        """Get drawdown periods for specific vendor."""
        df = data_loader.get_drawdown_periods(vendor="Vendor_B")
        assert len(df) == 0  # Vendor_B has no drawdowns


class TestUpload:
    """Test file upload functionality."""

    @pytest.mark.anyio
    async def test_load_data_from_upload(self):
        """Upload valid CSV file."""
        loader = DataLoaderService()
        chunks = [SAMPLE_CSV]

        async def read_chunk(size: int) -> bytes:
            return chunks.pop(0) if chunks else b""

        result = await loader.load_data_from_upload(
            read_chunk=read_chunk,
            content_type="text/csv",
            filename="test.csv",
        )

        assert result["total_records"] == 4
        assert set(result["vendors"]) == {"Vendor_A", "Vendor_B"}

    @pytest.mark.anyio
    async def test_upload_invalid_content_type(self):
        """Reject invalid content type."""
        loader = DataLoaderService()

        async def read_chunk(size: int) -> bytes:
            return b""

        with pytest.raises(ValueError, match="Invalid file type"):
            await loader.load_data_from_upload(
                read_chunk=read_chunk,
                content_type="application/json",
                filename="test.csv",
            )

    @pytest.mark.anyio
    async def test_upload_invalid_extension(self):
        """Reject invalid file extension."""
        loader = DataLoaderService()

        async def read_chunk(size: int) -> bytes:
            return b""

        with pytest.raises(ValueError, match="Invalid file extension"):
            await loader.load_data_from_upload(
                read_chunk=read_chunk,
                content_type="text/csv",
                filename="test.json",
            )

    @pytest.mark.anyio
    async def test_upload_file_too_large(self):
        """Reject files exceeding size limit."""
        loader = DataLoaderService()
        large_data = b"x" * 1000

        async def read_chunk(size: int) -> bytes:
            return large_data

        with pytest.raises(FileTooLargeError):
            await loader.load_data_from_upload(
                read_chunk=read_chunk,
                content_type="text/csv",
                filename="test.csv",
                max_file_size=100,  # Very small limit
            )
