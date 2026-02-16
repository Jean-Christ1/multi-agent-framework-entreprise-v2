"""
ETL Demo Actors for JAF Framework.

These actors demonstrate the framework's capabilities by:
1. Parsing SAP BODS XML metadata
2. Generating realistic test data
3. Writing Parquet files for input/expected outputs
"""

from __future__ import annotations

import logging
import random
import string
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from framework.actor import Actor

logger = logging.getLogger(__name__)

# Base path for fixtures
FIXTURES_BASE = (
    Path(__file__).parent.parent.parent / "tests" / "fixtures" / "trafic_ascend"
)


class BODSParserActor(Actor):
    """
    Actor that parses SAP BODS XML export files.

    Extracts table definitions, column metadata, and dataflow information
    from the BODS XML format.
    """

    def configure(self) -> None:
        self.name = "BODSParserActor"
        self.description = (
            "Parses SAP BODS XML export files and extracts schema metadata"
        )
        self.goal = "Extract table definitions and mappings from BODS XML"
        self.tools = [
            self.parse_xml,
            self.extract_tables,
            self.extract_dataflows,
            self.generate_schema_yaml,
        ]
        self.llm_config = None  # Deterministic actor

    def parse_xml(self, xml_path: str) -> Dict[str, Any]:
        """
        Parse BODS XML file and return structured metadata.

        Args:
            xml_path: Path to the BODS XML export file

        Returns:
            Dictionary with parsed metadata including datastores, tables, and dataflows
        """
        logger.info(f"Parsing XML file: {xml_path}")

        tree = ET.parse(xml_path)
        root = tree.getroot()

        metadata = {
            "repository_version": root.get("repositoryVersion"),
            "product_version": root.get("productVersion"),
            "datastores": [],
            "tables": [],
            "dataflows": [],
            "jobs": [],
            "workflows": [],
        }

        # Parse datastores
        for ds in root.findall(".//DIDatabaseDatastore"):
            datastore = {
                "name": ds.get("name"),
                "type_id": ds.get("typeId"),
                "attributes": {},
            }
            for attr in ds.findall(".//DIAttribute"):
                datastore["attributes"][attr.get("name")] = attr.get("value")
            metadata["datastores"].append(datastore)

        # Parse tables
        for table in root.findall(".//DITable"):
            table_info = self._parse_table(table)
            metadata["tables"].append(table_info)

        # Parse dataflows
        for df in root.findall(".//DIDataflow"):
            dataflow = {
                "name": df.get("name"),
                "type_id": df.get("typeId"),
            }
            metadata["dataflows"].append(dataflow)

        # Parse jobs
        for job in root.findall(".//DIJob"):
            job_info = {
                "name": job.get("name"),
                "type_id": job.get("typeId"),
            }
            metadata["jobs"].append(job_info)

        # Parse workflows
        for wf in root.findall(".//DIWorkflow"):
            workflow = {
                "name": wf.get("name"),
                "type_id": wf.get("typeId"),
            }
            metadata["workflows"].append(workflow)

        logger.info(
            f"Parsed: {len(metadata['tables'])} tables, "
            f"{len(metadata['dataflows'])} dataflows, "
            f"{len(metadata['workflows'])} workflows"
        )

        return metadata

    def _parse_table(self, table_elem: ET.Element) -> Dict[str, Any]:
        """Parse a single DITable element."""
        table_info = {
            "name": table_elem.get("name"),
            "owner": table_elem.get("owner"),
            "datastore": table_elem.get("datastore"),
            "database": table_elem.get("database"),
            "description": table_elem.get("description", ""),
            "columns": [],
            "indexes": [],
            "properties": {},
        }

        # Parse properties
        for prop in table_elem.findall(".//DIAttribute"):
            table_info["properties"][prop.get("name")] = prop.get("value")

        # Parse columns
        for col in table_elem.findall("DIColumn"):
            column = {
                "name": col.get("name"),
                "datatype": col.get("datatype"),
                "size": int(col.get("size", 0)) if col.get("size") else None,
                "scale": int(col.get("scale", 0)) if col.get("scale") else None,
                "nullable": col.get("nullable", "true").lower() == "true",
            }
            table_info["columns"].append(column)

        # Parse indexes
        for idx in table_elem.findall("DITableIndex"):
            index = {
                "name": idx.get("name"),
                "unique": idx.get("unique", "false").lower() == "true",
                "columns": [ic.get("name") for ic in idx.findall("DIIndexColumn")],
            }
            table_info["indexes"].append(index)

        return table_info

    def extract_tables(self, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract and categorize tables from parsed metadata.

        Args:
            metadata: Parsed BODS metadata

        Returns:
            List of table definitions categorized by type (source/target)
        """
        source_tables = []
        target_tables = []

        for table in metadata.get("tables", []):
            datastore = table.get("datastore", "")

            if "ASCENDFEED" in datastore:
                # Source table from SQL Server
                table["category"] = "source"
                source_tables.append(table)
            elif "TRAFIC_DATA" in datastore:
                # Target table in Oracle
                table["category"] = "target"
                target_tables.append(table)

        logger.info(
            f"Found {len(source_tables)} source tables, {len(target_tables)} target tables"
        )

        return source_tables + target_tables

    def extract_dataflows(self, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract dataflow definitions from metadata.

        Args:
            metadata: Parsed BODS metadata

        Returns:
            List of dataflow definitions with source/target mappings
        """
        dataflows = []

        for df in metadata.get("dataflows", []):
            name = df.get("name", "")

            # Extract table name from dataflow name convention
            # e.g., DF_TRAFIC2_DWH_AC_CARGO -> AC_CARGO
            if name.startswith("DF_TRAFIC2_DWH_"):
                table_suffix = name.replace("DF_TRAFIC2_DWH_", "")

                dataflow_info = {
                    "name": name,
                    "source_table": table_suffix,
                    "target_table": f"TR_DWH_TRAF_ASCEND_{table_suffix}",
                    "mapping_type": "DIRECT",  # Based on analysis
                }
                dataflows.append(dataflow_info)

        logger.info(f"Extracted {len(dataflows)} dataflow mappings")
        return dataflows

    def generate_schema_yaml(
        self,
        tables: List[Dict[str, Any]],
        output_path: str,
    ) -> str:
        """
        Generate schema YAML file from table definitions.

        Args:
            tables: List of table definitions
            output_path: Path to write the YAML file

        Returns:
            Path to the generated YAML file
        """
        # Ensure directory exists
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)

        # Build schema structure
        schema = {
            "version": "1.0",
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "source_system": "SAP_BODS",
            "tables": {},
        }

        for table in tables:
            table_name = table.get("name", "").lower()
            if not table_name:
                continue

            schema["tables"][table_name] = {
                "category": table.get("category", "unknown"),
                "datastore": table.get("datastore"),
                "database": table.get("database"),
                "owner": table.get("owner"),
                "columns": [
                    {
                        "name": col["name"],
                        "type": col["datatype"],
                        "size": col.get("size"),
                        "nullable": col.get("nullable", True),
                    }
                    for col in table.get("columns", [])
                ],
                "primary_key": self._get_primary_key(table),
            }

        # Write YAML
        try:
            import yaml
        except ImportError:
            raise ImportError(
                "ETL demo requires 'pyyaml'. Install with: pip install -r requirements-demo.txt"
            )

        with open(output_path, "w") as f:
            yaml.dump(schema, f, default_flow_style=False, sort_keys=False)

        logger.info(f"Generated schema YAML: {output_path}")
        return output_path

    def _get_primary_key(self, table: Dict[str, Any]) -> List[str]:
        """Extract primary key columns from table indexes."""
        for idx in table.get("indexes", []):
            if idx.get("name", "").startswith("PK_"):
                return idx.get("columns", [])
        return []


class DataGeneratorActor(Actor):
    """
    Actor that generates realistic aviation test data.

    Uses Faker and domain-specific generators to create
    realistic test data for the Ascend tables.

    Supports seed parameter for reproducible data generation.
    Each actor instance uses its own isolated random generator.
    """

    def __init__(self, seed: Optional[int] = None) -> None:
        """
        Initialize DataGeneratorActor with optional seed.

        Args:
            seed: Random seed for reproducible data generation.
                  If None, uses global random state (not recommended for reproducibility).
        """
        super().__init__()
        self._seed = seed
        # Create isolated random generator if seed is provided
        if seed is not None:
            self._rng = random.Random(seed)
        else:
            # Fallback to global random (for backward compatibility)
            self._rng = random

    def configure(self) -> None:
        self.name = "DataGeneratorActor"
        self.description = "Generates realistic aviation test data"
        self.goal = "Create test datasets with realistic aviation domain data"
        self.tools = [
            self.generate_lookup_data,
            self.generate_complex_data,
            self.generate_all_tables,
        ]
        self.llm_config = None  # Deterministic actor

        # Initialize generators
        self._init_generators()

    def _init_generators(self) -> None:
        """Initialize domain-specific data generators."""
        self.icao_codes = [
            "AFR",
            "BAW",
            "DLH",
            "UAE",
            "SIA",
            "QFA",
            "AAL",
            "UAL",
            "DAL",
            "SWA",
            "KLM",
            "AZA",
            "IBE",
            "TAP",
            "SAS",
            "FIN",
        ]
        self.iata_codes = [
            "AF",
            "BA",
            "LH",
            "EK",
            "SQ",
            "QF",
            "AA",
            "UA",
            "DL",
            "WN",
            "KL",
            "AZ",
            "IB",
            "TP",
            "SK",
            "AY",
        ]
        self.country_codes = [
            "FR",
            "GB",
            "DE",
            "AE",
            "SG",
            "AU",
            "US",
            "NL",
            "IT",
            "ES",
            "PT",
            "SE",
            "FI",
            "JP",
            "CN",
            "BR",
        ]
        self.area_codes = [
            "E",
            "N",
            "A",
            "S",
            "O",
        ]  # Europe, North America, Asia, South, Oceania
        self.aircraft_types = [
            "A320",
            "A321",
            "A330",
            "A350",
            "A380",
            "B737",
            "B738",
            "B77W",
            "B788",
            "B789",
            "E190",
            "E195",
            "CRJ9",
            "AT72",
            "DH8D",
        ]
        self.engine_types = ["CFM", "GE90", "TRENT", "PW4000", "LEAP"]
        self.cargo_types = ["P", "C", "M"]  # Passenger, Cargo, Mixed

    def generate_lookup_data(
        self,
        table_name: str,
        schema: Dict[str, Any],
        count: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Generate data for simple lookup tables.

        Args:
            table_name: Name of the table
            schema: Schema definition for the table
            count: Number of records to generate

        Returns:
            List of generated records
        """
        logger.info(f"Generating {count} records for lookup table: {table_name}")

        generators = {
            "ac_cargo": self._gen_ac_cargo,
            "area": self._gen_area,
            "category": self._gen_category,
            "country": self._gen_country,
            "event": self._gen_event,
            "eventtypes": self._gen_eventtypes,
        }

        generator = generators.get(table_name.lower())
        if generator:
            return generator(count)

        # Fallback: generate based on schema
        return self._gen_from_schema(table_name, schema, count)

    def generate_complex_data(
        self,
        table_name: str,
        schema: Dict[str, Any],
        count: int = 100,
        references: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generate data for complex tables with foreign key references.

        Args:
            table_name: Name of the table
            schema: Schema definition
            count: Number of records
            references: Dict of reference data for FK lookups

        Returns:
            List of generated records
        """
        logger.info(f"Generating {count} records for complex table: {table_name}")
        references = references or {}

        generators = {
            "company": self._gen_company,
            "gentech": self._gen_gentech,
            "spectech": self._gen_spectech,
            "histories": self._gen_histories,
            "lastdelivery": self._gen_lastdelivery,
            "lastorder": self._gen_lastorder,
            "ordersplacedtmp": self._gen_ordersplacedtmp,
            "v_histories": self._gen_v_histories,
            "v_currenthistories": self._gen_v_currenthistories,
        }

        generator = generators.get(table_name.lower())
        if generator:
            return generator(count, references)

        return self._gen_from_schema(table_name, schema, count)

    def generate_all_tables(
        self,
        schema: Dict[str, Any],
        count: int = 75,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Generate data for all tables in the schema.

        Maintains referential integrity across tables.

        Args:
            schema: Full schema definition
            count: Approximate records per table

        Returns:
            Dict mapping table names to generated data
        """
        logger.info(f"Generating data for all tables (~{count} records each)")

        all_data: Dict[str, List[Dict[str, Any]]] = {}

        # Generate lookup tables first (no dependencies)
        # Sort for stable ordering
        lookup_tables = sorted(
            ["ac_cargo", "area", "category", "country", "event", "eventtypes"]
        )
        for table_name in lookup_tables:
            table_schema = schema.get("tables", {}).get(table_name, {})
            # Lookup tables typically have fewer records
            all_data[table_name] = self.generate_lookup_data(
                table_name, table_schema, min(count, 20)
            )

        # Generate complex tables (with dependencies)
        # Sort for stable ordering
        complex_tables = sorted(
            [
                "company",
                "gentech",
                "spectech",
                "histories",
                "lastdelivery",
                "lastorder",
                "ordersplacedtmp",
                "v_histories",
                "v_currenthistories",
            ]
        )
        for table_name in complex_tables:
            table_schema = schema.get("tables", {}).get(table_name, {})
            all_data[table_name] = self.generate_complex_data(
                table_name, table_schema, count, all_data
            )

        logger.info(f"Generated data for {len(all_data)} tables")
        return all_data

    # Lookup table generators
    def _gen_ac_cargo(self, count: int) -> List[Dict[str, Any]]:
        return [
            {"ACCARGO": code, "ACCARGODESC": desc}
            for code, desc in [
                ("P", "Passenger"),
                ("C", "Cargo"),
                ("M", "Mixed/Combi"),
            ]
        ][:count]

    def _gen_area(self, count: int) -> List[Dict[str, Any]]:
        return [
            {"AREA": code, "AREADESC": desc}
            for code, desc in [
                ("E", "Europe"),
                ("N", "North America"),
                ("A", "Asia Pacific"),
                ("S", "South America"),
                ("O", "Oceania"),
                ("M", "Middle East"),
                ("F", "Africa"),
            ]
        ][:count]

    def _gen_category(self, count: int) -> List[Dict[str, Any]]:
        categories = [
            ("MAJR", "Major Carrier"),
            ("RGNL", "Regional Carrier"),
            ("LCC", "Low Cost Carrier"),
            ("CRGO", "Cargo Carrier"),
            ("CHRT", "Charter"),
        ]
        return [{"ACCAT": code, "ACCATDESC": desc} for code, desc in categories][:count]

    def _gen_country(self, count: int) -> List[Dict[str, Any]]:
        countries = [
            ("FR", "France", "E"),
            ("GB", "United Kingdom", "E"),
            ("DE", "Germany", "E"),
            ("US", "United States", "N"),
            ("AE", "United Arab Emirates", "M"),
            ("SG", "Singapore", "A"),
            ("AU", "Australia", "O"),
            ("JP", "Japan", "A"),
            ("CN", "China", "A"),
            ("BR", "Brazil", "S"),
        ]
        return [
            {"CTRY": code, "COUNTRYDESC": name, "AREA": area}
            for code, name, area in countries
        ][:count]

    def _gen_event(self, count: int) -> List[Dict[str, Any]]:
        events = [
            ("DEL", "Delivery"),
            ("RET", "Retirement"),
            ("SOLD", "Sold"),
            ("LEAS", "Leased"),
            ("RTRN", "Returned from Lease"),
            ("STOR", "Stored"),
            ("SCRP", "Scrapped"),
            ("CONV", "Converted"),
        ]
        return [{"EVENT": code, "EVENTDESC": desc} for code, desc in events][:count]

    def _gen_eventtypes(self, count: int) -> List[Dict[str, Any]]:
        types = [
            ("O", "Ownership Change"),
            ("S", "Status Change"),
            ("L", "Lease Transaction"),
            ("T", "Technical Modification"),
        ]
        return [{"EVENTTYPE": code, "EVENTTYPEDESC": desc} for code, desc in types][
            :count
        ]

    # Complex table generators
    def _gen_company(
        self,
        count: int,
        refs: Dict[str, List[Dict[str, Any]]],
    ) -> List[Dict[str, Any]]:
        companies = []
        areas = [r["AREA"] for r in refs.get("area", [])] or self.area_codes
        countries = [r["CTRY"] for r in refs.get("country", [])] or self.country_codes
        categories = [r["ACCAT"] for r in refs.get("category", [])] or ["MAJR", "RGNL"]

        for i in range(count):
            icao = (
                self.icao_codes[i % len(self.icao_codes)]
                if i < len(self.icao_codes)
                else f"X{i:02d}"
            )
            iata = (
                self.iata_codes[i % len(self.iata_codes)]
                if i < len(self.iata_codes)
                else f"X{i}"
            )

            companies.append(
                {
                    "COMPANY": f"{i:04d}",
                    "NAME": f"Airline {icao}",
                    "CAT": self._rng.choice(categories),
                    "AREA": self._rng.choice(areas),
                    "CTRY": self._rng.choice(countries),
                    "SOURCE": "ASCEND",
                    "HISTORIC": self._rng.choice(["Y", "N"]),
                    "ICAO": icao,
                    "IATA": iata,
                    "ALIAS": f"{icao} Airways",
                    "CEASED_OPS": None,
                    "CURRENTAC": self._rng.randint(10, 500),
                }
            )

        return companies

    def _gen_gentech(
        self,
        count: int,
        refs: Dict[str, List[Dict[str, Any]]],
    ) -> List[Dict[str, Any]]:
        records = []

        for i in range(count):
            actype = self.aircraft_types[i % len(self.aircraft_types)]
            acvar = f"V{self._rng.randint(1, 9)}"

            records.append(
                {
                    "ACTYPE": actype,
                    "ACVAR": acvar,
                    "MTOW": self._rng.randint(50000, 560000),  # kg
                    "MLW": self._rng.randint(40000, 400000),
                    "MZFW": self._rng.randint(35000, 350000),
                    "OEW": self._rng.randint(30000, 300000),
                    "FUEL": self._rng.randint(10000, 200000),
                    "EXITLIMIT": self._rng.randint(100, 500),
                    "CARGOVOL": self._rng.randint(100, 500),
                    "GENTECHID": i + 1,
                    "MAXPAYLOAD": self._rng.randint(10000, 100000),
                    "MAXSEATS": self._rng.randint(100, 600),
                    "ACMFRCTRY": self._rng.choice(["FR", "US", "BR", "CA"]),
                    "ACMFR": self._rng.choice(["AIRB", "BOEI", "EMBR", "BOMB"]),
                    "BUILDAREA": self._rng.choice(["E", "N", "S"]),
                    "JETTURBO": self._rng.choice(["JT", "TB", "PP"]),
                    "PAYLOAD": self._rng.choice(["H", "M", "L"]),
                    "RANGE": self._rng.choice(["L", "M", "S"]),
                    "ACVARDESC": f"{actype} Variant {acvar}",
                    "ACMINVAR": f"{actype}-{acvar}",
                    "ENGNO": self._rng.choice([2, 4]),
                    "NOISECERT": self._rng.choice(["C3", "C4", "C5"]),
                    "GRPPAYLOAD": self._rng.choice(["A", "B", "C"]),
                    "CONFIG": self._rng.choice(["1", "2", "3"]),
                    "TYPICALF": self._rng.randint(0, 50),
                    "TYPICALC": self._rng.randint(0, 100),
                    "TYPICALY": self._rng.randint(100, 400),
                    "TYPICALTOT": self._rng.randint(150, 550),
                    "ACCARGO": self._rng.choice(["P", "C", "M"]),
                    "ENGVAR": self._rng.choice(["V1", "V2", "V3"]),
                    "ENGTYPE": self._rng.choice(self.engine_types),
                }
            )

        return records

    def _gen_spectech(
        self,
        count: int,
        refs: Dict[str, List[Dict[str, Any]]],
    ) -> List[Dict[str, Any]]:
        records = []

        for i in range(count):
            actype = self.aircraft_types[i % len(self.aircraft_types)]
            serial = f"MSN{i + 1000:05d}"

            records.append(
                {
                    "ACTYPE": actype,
                    "SERIALNO": serial,
                    "MTOW": self._rng.randint(50000, 560000),
                    "MLW": self._rng.randint(40000, 400000),
                    "MZFW": self._rng.randint(35000, 350000),
                    "OEW": self._rng.randint(30000, 300000),
                    "FUELCAP": self._rng.randint(10000, 200000),
                    "CLASS1": self._rng.randint(0, 50),
                    "CLASS2": self._rng.randint(0, 100),
                    "CLASS3": self._rng.randint(100, 400),
                    "CLASSTYPE": self._rng.choice(["1", "2", "3"]),
                }
            )

        return records

    def _gen_histories(
        self,
        count: int,
        refs: Dict[str, List[Dict[str, Any]]],
    ) -> List[Dict[str, Any]]:
        records = []
        companies = refs.get("company", [])
        company_ids = (
            [c["COMPANY"] for c in companies] if companies else ["0001", "0002"]
        )

        for i in range(count):
            actype = self.aircraft_types[i % len(self.aircraft_types)]
            serial = f"MSN{i + 1000:05d}"
            start_date = datetime(2000, 1, 1) + timedelta(
                days=self._rng.randint(0, 8000)
            )
            end_date = start_date + timedelta(days=self._rng.randint(365, 3650))

            records.append(
                {
                    "ACCLASS": self._rng.choice(["WB", "NB", "RJ"]),
                    "EVENTSEQNO": f"{self._rng.randint(1, 99):02d}",
                    "ACTYPE": actype,
                    "OPR": self._rng.choice(company_ids),
                    "MGR": self._rng.choice(company_ids),
                    "ACVAR": f"V{self._rng.randint(1, 9)}",
                    "STARTEVENT": self._rng.choice(["DEL", "LEAS", "SOLD"]),
                    "ENDEVENT": self._rng.choice(["RET", "SOLD", "RTRN"]),
                    "ACMFR": self._rng.choice(["AIRB", "BOEI"]),
                    "SERIALNO": serial,
                    "REGNO": f"F-G{self._rng.choice(string.ascii_uppercase)}{self._rng.choice(string.ascii_uppercase)}{self._rng.choice(string.ascii_uppercase)}",
                    "ACLINENO": f"LN{i + 100:04d}",
                    "STARTDATE": start_date.isoformat(),
                    "ENDDATE": (
                        end_date.isoformat() if self._rng.random() > 0.3 else None
                    ),
                    "AIRCRAFTID": i + 1,
                    "HISTORIESID": i + 1,
                    "YOB": start_date.year - self._rng.randint(0, 5),
                    "MOB": self._rng.randint(1, 12),
                }
            )

        return records

    def _gen_lastdelivery(
        self,
        count: int,
        refs: Dict[str, List[Dict[str, Any]]],
    ) -> List[Dict[str, Any]]:
        records = []

        for i in range(count):
            actype = self.aircraft_types[i % len(self.aircraft_types)]
            serial = f"MSN{i + 1000:05d}"
            delivery_date = datetime(2010, 1, 1) + timedelta(
                days=self._rng.randint(0, 5000)
            )

            records.append(
                {
                    "ACTYPE": actype,
                    "SERIALNO": serial,
                    "DELIVERYDATE": delivery_date.isoformat(),
                    "OPRDESC": f"Delivered to Operator {i % 20}",  # Note: Known anomaly in source
                }
            )

        return records

    def _gen_lastorder(
        self,
        count: int,
        refs: Dict[str, List[Dict[str, Any]]],
    ) -> List[Dict[str, Any]]:
        records = []

        for i in range(count):
            actype = self.aircraft_types[i % len(self.aircraft_types)]
            serial = f"MSN{i + 1000:05d}"
            order_date = datetime(2005, 1, 1) + timedelta(
                days=self._rng.randint(0, 7000)
            )

            records.append(
                {
                    "ACTYPE": actype,
                    "SERIALNO": serial,
                    "ORDERDATE": order_date.isoformat(),
                }
            )

        return records

    def _gen_ordersplacedtmp(
        self,
        count: int,
        refs: Dict[str, List[Dict[str, Any]]],
    ) -> List[Dict[str, Any]]:
        records = []

        for i in range(count):
            actype = self.aircraft_types[i % len(self.aircraft_types)]
            serial = f"MSN{i + 1000:05d}"
            last_date = datetime(2020, 1, 1) + timedelta(
                days=self._rng.randint(0, 1500)
            )

            records.append(
                {
                    "ACTYPE": actype,
                    "SERIALNO": serial,
                    "LASTDATE": last_date.isoformat(),
                }
            )

        return records

    def _gen_v_histories(
        self,
        count: int,
        refs: Dict[str, List[Dict[str, Any]]],
    ) -> List[Dict[str, Any]]:
        # Similar to histories but represents a view
        return self._gen_histories(count, refs)

    def _gen_v_currenthistories(
        self,
        count: int,
        refs: Dict[str, List[Dict[str, Any]]],
    ) -> List[Dict[str, Any]]:
        # Current active records only
        histories = self._gen_histories(count, refs)
        # Filter to those with no end date (current)
        return [h for h in histories if h.get("ENDDATE") is None][:count]

    def _gen_from_schema(
        self,
        table_name: str,
        schema: Dict[str, Any],
        count: int,
    ) -> List[Dict[str, Any]]:
        """Fallback generator using schema definition."""
        records = []
        columns = schema.get("columns", [])

        for i in range(count):
            record = {}
            for col in columns:
                col_name = col.get("name", "")
                col_type = col.get("type", "VARCHAR")
                col_size = col.get("size", 50)

                if col_type in ("INT", "INTEGER"):
                    record[col_name] = self._rng.randint(1, 10000)
                elif col_type in ("DATETIME", "TIMESTAMP"):
                    record[col_name] = datetime.utcnow().isoformat()
                else:
                    record[col_name] = (
                        f"{col_name}_{i}"[:col_size] if col_size else f"{col_name}_{i}"
                    )

            records.append(record)

        return records


class ParquetWriterActor(Actor):
    """
    Actor that writes data to Parquet format.

    Handles both input (source) and expected (target) data files.
    """

    def configure(self) -> None:
        self.name = "ParquetWriterActor"
        self.description = "Writes data to Parquet format for test fixtures"
        self.goal = "Create Parquet files for input and expected test data"
        self.tools = [
            self.write_input_parquet,
            self.write_expected_parquet,
            self.write_all_parquets,
            self.validate_output,
        ]
        self.llm_config = None  # Deterministic actor

    def write_input_parquet(
        self,
        data: List[Dict[str, Any]],
        table_name: str,
        output_dir: Optional[str] = None,
    ) -> str:
        """
        Write source data to input Parquet file.

        Args:
            data: List of records
            table_name: Name of the table
            output_dir: Output directory (defaults to fixtures/inputs/)

        Returns:
            Path to the written file
        """
        try:
            import pandas as pd
            import pyarrow as pa
            import pyarrow.parquet as pq
        except ImportError:
            raise ImportError(
                "ETL demo requires 'pandas' and 'pyarrow'. Install with: pip install -r requirements-demo.txt"
            )

        output_dir = Path(output_dir) if output_dir else FIXTURES_BASE / "inputs"
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / f"{table_name.lower()}.parquet"

        df = pd.DataFrame(data)
        table = pa.Table.from_pandas(df)
        pq.write_table(table, output_path)

        logger.info(f"Wrote {len(data)} records to {output_path}")
        return str(output_path)

    def write_expected_parquet(
        self,
        data: List[Dict[str, Any]],
        table_name: str,
        output_dir: Optional[str] = None,
        apply_transformations: bool = True,
    ) -> str:
        """
        Write expected output data to Parquet file.

        Applies transformations to match target schema.

        Args:
            data: List of records
            table_name: Source table name
            output_dir: Output directory (defaults to fixtures/expected/)
            apply_transformations: Whether to apply target transformations

        Returns:
            Path to the written file
        """
        try:
            import pandas as pd
            import pyarrow as pa
            import pyarrow.parquet as pq
        except ImportError:
            raise ImportError(
                "ETL demo requires 'pandas' and 'pyarrow'. Install with: pip install -r requirements-demo.txt"
            )

        output_dir = Path(output_dir) if output_dir else FIXTURES_BASE / "expected"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Determine target table name
        target_name = self._get_target_table_name(table_name)
        output_path = output_dir / f"{target_name.lower()}.parquet"

        # Apply transformations if needed
        if apply_transformations:
            data = self._apply_transformations(data, table_name)

        df = pd.DataFrame(data)
        table = pa.Table.from_pandas(df)
        pq.write_table(table, output_path)

        logger.info(f"Wrote {len(data)} expected records to {output_path}")
        return str(output_path)

    def write_all_parquets(
        self,
        all_data: Dict[str, List[Dict[str, Any]]],
        base_dir: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Write all tables to Parquet files.

        Args:
            all_data: Dict mapping table names to data
            base_dir: Base output directory

        Returns:
            Dict mapping table names to output paths
        """
        base_dir = Path(base_dir) if base_dir else FIXTURES_BASE
        outputs = {}

        # Sort table names for stable ordering
        for table_name in sorted(all_data.keys()):
            data = all_data[table_name]
            if not data:
                logger.warning(f"No data for table {table_name}, skipping")
                continue

            # Write input
            input_path = self.write_input_parquet(
                data, table_name, str(base_dir / "inputs")
            )
            outputs[f"{table_name}_input"] = input_path

            # Write expected output
            expected_path = self.write_expected_parquet(
                data, table_name, str(base_dir / "expected")
            )
            outputs[f"{table_name}_expected"] = expected_path

        logger.info(f"Wrote {len(outputs)} Parquet files")
        return outputs

    def validate_output(self, file_path: str) -> Dict[str, Any]:
        """
        Validate a Parquet file.

        Args:
            file_path: Path to the Parquet file

        Returns:
            Validation results
        """
        try:
            import pyarrow.parquet as pq
        except ImportError:
            raise ImportError(
                "ETL demo requires 'pyarrow'. Install with: pip install -r requirements-demo.txt"
            )

        path = Path(file_path)
        if not path.exists():
            return {"valid": False, "error": f"File not found: {file_path}"}

        try:
            table = pq.read_table(file_path)
            return {
                "valid": True,
                "num_rows": table.num_rows,
                "num_columns": table.num_columns,
                "column_names": table.column_names,
                "schema": str(table.schema),
            }
        except Exception as e:
            return {"valid": False, "error": str(e)}

    def _get_target_table_name(self, source_name: str) -> str:
        """Map source table name to target table name."""
        # Views have different target naming
        if source_name.lower().startswith("v_"):
            return f"td_dwh_traf_ascend_{source_name.lower()}"

        return f"tr_dwh_traf_ascend_{source_name.lower()}"

    def _apply_transformations(
        self,
        data: List[Dict[str, Any]],
        table_name: str,
    ) -> List[Dict[str, Any]]:
        """
        Apply target-specific transformations.

        Handles known anomalies like LASTDELIVERY date->string mapping.
        """
        transformed = []

        for record in data:
            new_record = record.copy()

            # Known anomaly: LASTDELIVERY LASTDATE -> OPRDESC
            if table_name.lower() == "lastdelivery":
                # The source LASTDATE is mapped to OPRDESC in target
                # This is a known bug in the legacy system
                if "DELIVERYDATE" in new_record:
                    # Ensure OPRDESC contains the date as string
                    new_record["OPRDESC"] = str(new_record.get("DELIVERYDATE", ""))

            # Strip whitespace from all string fields
            for key, value in new_record.items():
                if isinstance(value, str):
                    new_record[key] = value.strip()

            transformed.append(new_record)

        return transformed
