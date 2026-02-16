"""
ETL Demo for JAF Framework.

Demonstrates the framework's capabilities by parsing SAP BODS metadata
and generating test datasets for the TRAFIC NG project.

Note: This module requires additional dependencies. Install with:
    pip install -r requirements-demo.txt
"""

try:
    from examples.etl_demo.actors import (
        BODSParserActor,
        DataGeneratorActor,
        ParquetWriterActor,
    )

    __all__ = [
        "BODSParserActor",
        "DataGeneratorActor",
        "ParquetWriterActor",
    ]
except ImportError as e:
    raise ImportError(
        f"ETL demo requires additional dependencies: {e}\n"
        "Install with: pip install -r requirements-demo.txt"
    ) from e
