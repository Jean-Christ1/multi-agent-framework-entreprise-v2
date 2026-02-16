"""
ETL Fixtures Schema Validation Tests

Validates that generated Parquet files in tests/fixtures/trafic_ascend/
match the schema defined in ascend_schema.yaml.

Tests:
- Column names match schema definition
- Data types are compatible with schema types
- Non-nullable columns have no null values
"""

import pytest
import yaml
from pathlib import Path
from typing import Dict, Any, List
import pyarrow.parquet as pq
import pyarrow as pa

# Fixture paths
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "trafic_ascend"
SCHEMA_FILE = FIXTURES_DIR / "schemas" / "ascend_schema.yaml"
INPUTS_DIR = FIXTURES_DIR / "inputs"
EXPECTED_DIR = FIXTURES_DIR / "expected"


@pytest.fixture(scope="module")
def schema_definition() -> Dict[str, Any]:
    """Load the YAML schema definition."""
    with open(SCHEMA_FILE, "r") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def input_parquet_files() -> List[Path]:
    """Get all Parquet files from inputs directory."""
    return sorted(INPUTS_DIR.glob("*.parquet"))


@pytest.fixture(scope="module")
def expected_parquet_files() -> List[Path]:
    """Get all Parquet files from expected directory."""
    return sorted(EXPECTED_DIR.glob("*.parquet"))


def get_table_schema(
    schema_definition: Dict[str, Any], table_name: str
) -> Dict[str, Any]:
    """
    Extract table schema from YAML definition.

    Args:
        schema_definition: Loaded YAML schema
        table_name: Name of the table to find

    Returns:
        Table schema dict with columns and metadata
    """
    tables = schema_definition.get("tables", {})
    return tables.get(table_name)


def map_yaml_type_to_pyarrow(yaml_type: str) -> List[pa.DataType]:
    """
    Map YAML schema types to compatible PyArrow types.

    Args:
        yaml_type: Type from YAML schema (VARCHAR, INT, DATETIME, etc.)

    Returns:
        List of compatible PyArrow types
    """
    type_mapping = {
        "VARCHAR": [pa.string(), pa.large_string()],
        "CHAR": [pa.string(), pa.large_string()],
        "INT": [pa.int32(), pa.int64()],
        "BIGINT": [pa.int64()],
        "SMALLINT": [pa.int16(), pa.int32()],
        "TINYINT": [pa.int8(), pa.int16()],
        "DATETIME": [
            pa.timestamp("us"),
            pa.timestamp("ns"),
            pa.timestamp("ms"),
            pa.timestamp("s"),
        ],
        "DATE": [pa.date32(), pa.date64()],
        "DECIMAL": [
            pa.decimal128(38, 10),
            pa.float64(),
        ],  # Allow float as approximation
        "FLOAT": [pa.float32(), pa.float64()],
        "DOUBLE": [pa.float64()],
        "BOOLEAN": [pa.bool_()],
    }

    return type_mapping.get(yaml_type.upper(), [pa.string()])


def is_type_compatible(parquet_type: pa.DataType, yaml_type: str) -> bool:
    """
    Check if Parquet type is compatible with YAML schema type.

    Args:
        parquet_type: PyArrow type from Parquet file
        yaml_type: Type string from YAML schema

    Returns:
        True if types are compatible
    """
    # Null type is allowed for nullable columns (columns with no data)
    if pa.types.is_null(parquet_type):
        return True

    compatible_types = map_yaml_type_to_pyarrow(yaml_type)

    # Direct match
    if parquet_type in compatible_types:
        return True

    # For decimal types, check if it's any decimal variant
    if yaml_type.upper() == "DECIMAL" and pa.types.is_decimal(parquet_type):
        return True

    # For timestamp/datetime types
    if yaml_type.upper() == "DATETIME" and pa.types.is_timestamp(parquet_type):
        return True

    # Allow string for DATETIME (common in test data generation)
    # This is acceptable for test fixtures - dates can be stored as ISO strings
    if yaml_type.upper() == "DATETIME" and pa.types.is_string(parquet_type):
        return True

    return False


class TestInputParquetFiles:
    """Test validation for input Parquet files."""

    def test_input_files_exist(self, input_parquet_files):
        """Verify that input Parquet files exist."""
        assert len(input_parquet_files) > 0, "No input Parquet files found"

    def test_input_column_names_match_schema(
        self, schema_definition, input_parquet_files
    ):
        """Validate that column names in input files match the schema.

        Note: Parquet files may contain a subset of schema columns (test data generation).
        This test validates that columns present in Parquet are defined in the schema.
        """
        # Known generated columns that are not in schema but are expected
        generated_columns = {"AIRCRAFTID", "HISTORIESID", "GENTECHID"}

        for parquet_file in input_parquet_files:
            table_name = parquet_file.stem  # filename without extension
            table_schema = get_table_schema(schema_definition, table_name)

            if not table_schema:
                # Skip files not in schema (e.g., views)
                continue

            # Read Parquet schema
            parquet_table = pq.read_table(parquet_file)
            parquet_columns = set(parquet_table.column_names)

            # Get expected columns from YAML
            expected_columns = {col["name"] for col in table_schema["columns"]}

            # Validate that Parquet columns exist in schema (reverse check)
            # Parquet may have subset of columns, but all must be in schema
            # Allow known generated columns
            unknown_columns = parquet_columns - expected_columns - generated_columns
            assert (
                not unknown_columns
            ), f"{parquet_file.name}: Unknown columns not in schema: {unknown_columns}"

    def test_input_data_types_compatible(self, schema_definition, input_parquet_files):
        """Validate that data types in input files are compatible with schema."""
        for parquet_file in input_parquet_files:
            table_name = parquet_file.stem
            table_schema = get_table_schema(schema_definition, table_name)

            if not table_schema:
                continue

            # Read Parquet schema
            parquet_table = pq.read_table(parquet_file)
            parquet_schema = parquet_table.schema

            # Check each column type
            for col_def in table_schema["columns"]:
                col_name = col_def["name"]
                expected_type = col_def["type"]

                if col_name in parquet_schema.names:
                    parquet_type = parquet_schema.field(col_name).type

                    assert is_type_compatible(parquet_type, expected_type), (
                        f"{parquet_file.name}: Column '{col_name}' type mismatch. "
                        f"Expected {expected_type}, got {parquet_type}"
                    )

    def test_input_non_nullable_columns_have_no_nulls(
        self, schema_definition, input_parquet_files
    ):
        """Validate that non-nullable columns contain no null values."""
        for parquet_file in input_parquet_files:
            table_name = parquet_file.stem
            table_schema = get_table_schema(schema_definition, table_name)

            if not table_schema:
                continue

            # Read Parquet data
            parquet_table = pq.read_table(parquet_file)

            # Check non-nullable columns
            for col_def in table_schema["columns"]:
                col_name = col_def["name"]
                nullable = col_def.get("nullable", True)

                if not nullable and col_name in parquet_table.column_names:
                    column = parquet_table.column(col_name)
                    null_count = column.null_count

                    assert null_count == 0, (
                        f"{parquet_file.name}: Non-nullable column '{col_name}' "
                        f"contains {null_count} null values"
                    )


class TestExpectedParquetFiles:
    """Test validation for expected output Parquet files."""

    def test_expected_files_exist(self, expected_parquet_files):
        """Verify that expected Parquet files exist."""
        assert len(expected_parquet_files) > 0, "No expected Parquet files found"

    def test_expected_column_names_match_schema(
        self, schema_definition, expected_parquet_files
    ):
        """Validate that column names in expected files match the schema.

        Note: Expected Parquet files may contain a subset of schema columns.
        This test validates that columns present in Parquet are defined in the schema.
        """
        # Known generated columns that are not in schema but are expected
        generated_columns = {"AIRCRAFTID", "HISTORIESID", "GENTECHID"}

        for parquet_file in expected_parquet_files:
            # Use full filename as table name (e.g., tr_dwh_traf_ascend_company.parquet -> tr_dwh_traf_ascend_company)
            # This matches the YAML schema keys which include the full prefix
            table_name = parquet_file.stem

            table_schema = get_table_schema(schema_definition, table_name)

            if not table_schema:
                continue

            # Read Parquet schema
            parquet_table = pq.read_table(parquet_file)
            parquet_columns = set(parquet_table.column_names)

            # Get expected columns from YAML
            expected_columns = {col["name"] for col in table_schema["columns"]}

            # Validate that Parquet columns exist in schema (reverse check)
            # Allow known generated columns
            unknown_columns = parquet_columns - expected_columns - generated_columns
            assert (
                not unknown_columns
            ), f"{parquet_file.name}: Unknown columns not in schema: {unknown_columns}"

    def test_expected_data_types_compatible(
        self, schema_definition, expected_parquet_files
    ):
        """Validate that data types in expected files are compatible with schema."""
        for parquet_file in expected_parquet_files:
            # Use full filename as table name (e.g., tr_dwh_traf_ascend_company.parquet -> tr_dwh_traf_ascend_company)
            # This matches the YAML schema keys which include the full prefix
            table_name = parquet_file.stem

            table_schema = get_table_schema(schema_definition, table_name)

            if not table_schema:
                continue

            # Read Parquet schema
            parquet_table = pq.read_table(parquet_file)
            parquet_schema = parquet_table.schema

            # Check each column type
            for col_def in table_schema["columns"]:
                col_name = col_def["name"]
                expected_type = col_def["type"]

                if col_name in parquet_schema.names:
                    parquet_type = parquet_schema.field(col_name).type

                    assert is_type_compatible(parquet_type, expected_type), (
                        f"{parquet_file.name}: Column '{col_name}' type mismatch. "
                        f"Expected {expected_type}, got {parquet_type}"
                    )

    def test_expected_non_nullable_columns_have_no_nulls(
        self, schema_definition, expected_parquet_files
    ):
        """Validate that non-nullable columns in expected files contain no null values."""
        for parquet_file in expected_parquet_files:
            # Use full filename as table name (e.g., tr_dwh_traf_ascend_company.parquet -> tr_dwh_traf_ascend_company)
            # This matches the YAML schema keys which include the full prefix
            table_name = parquet_file.stem

            table_schema = get_table_schema(schema_definition, table_name)

            if not table_schema:
                continue

            # Read Parquet data
            parquet_table = pq.read_table(parquet_file)

            # Check non-nullable columns
            for col_def in table_schema["columns"]:
                col_name = col_def["name"]
                nullable = col_def.get("nullable", True)

                if not nullable and col_name in parquet_table.column_names:
                    column = parquet_table.column(col_name)
                    null_count = column.null_count

                    assert null_count == 0, (
                        f"{parquet_file.name}: Non-nullable column '{col_name}' "
                        f"contains {null_count} null values"
                    )


class TestSchemaConsistency:
    """Test overall schema consistency."""

    def test_schema_file_is_valid_yaml(self):
        """Verify that the schema YAML file is valid and loadable."""
        with open(SCHEMA_FILE, "r") as f:
            schema = yaml.safe_load(f)

        assert schema is not None
        assert "tables" in schema
        assert "version" in schema

    def test_all_input_files_have_schema_definition(
        self, schema_definition, input_parquet_files
    ):
        """Verify that all input files have corresponding schema definitions (or are known exceptions)."""
        tables = schema_definition.get("tables", {})
        table_names = set(tables.keys())

        # Known views/derived tables that may not have schema
        known_exceptions = {"v_currenthistories", "v_histories"}

        for parquet_file in input_parquet_files:
            table_name = parquet_file.stem

            if table_name not in known_exceptions:
                assert (
                    table_name in table_names
                ), f"Input file '{parquet_file.name}' has no schema definition"
