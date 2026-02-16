#!/usr/bin/env python3
"""
ETL Demo for JAF Framework.

This script demonstrates the JAF framework's capabilities by:
1. Parsing SAP BODS XML metadata
2. Generating realistic test datasets
3. Writing Parquet files for input/expected outputs

Usage:
    # With database persistence (requires DATABASE_URL)
    python -m examples.etl_demo.run_demo

    # Standalone mode (no database required)
    python -m examples.etl_demo.run_demo --standalone

    # Specify record count
    python -m examples.etl_demo.run_demo --count 100
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
import random

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from framework.actor import ActorRegistry
from framework.engine import NativeEngine
from framework.types import Plan, PlanStep

from framework.event_bus import get_event_bus, console_subscriber

# Global verbosity control
VERBOSE_MODE = False
QUIET_MODE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def log_step(
    step_num: int, total_steps: int, message: str, verbose_details: Optional[str] = None
) -> None:
    if QUIET_MODE:
        return
    progress = f"Step {step_num}/{total_steps}"
    logger.info(f"{progress}: {message}")
    if VERBOSE_MODE and verbose_details:
        logger.debug(verbose_details)


def log_summary(
    tables_count: int, records_generated: int, files_written: int, time_elapsed: float
) -> None:
    if QUIET_MODE:
        print("Success")
        return

    logger.info("=" * 60)
    logger.info("Summary")
    logger.info("=" * 60)
    logger.info(f"Tables generated: {tables_count}")
    logger.info(f"Records generated: {records_generated:,}")
    logger.info(f"Files written: {files_written}")
    logger.info(f"Time elapsed: {time_elapsed:.2f}s")
    logger.info("=" * 60)


# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures" / "trafic_ascend"
XML_PATH = DOCS_DIR / "export-ascend.xml"


def register_actors() -> None:
    """Register ETL actors with the registry."""
    try:
        from examples.etl_demo.actors import (
            BODSParserActor,
            DataGeneratorActor,
            ParquetWriterActor,
        )
    except ImportError as e:
        logger.error(
            f"Failed to import ETL demo actors: {e}\n"
            "ETL demo requires additional dependencies. Install with:\n"
            "  pip install -r requirements-demo.txt"
        )
        raise

    ActorRegistry.register("BODSParserActor", BODSParserActor)
    ActorRegistry.register("DataGeneratorActor", DataGeneratorActor)
    ActorRegistry.register("ParquetWriterActor", ParquetWriterActor)

    logger.info("Registered 3 ETL actors")


def build_etl_plan(xml_path: str, record_count: int) -> Plan:
    """
    Build a pre-defined ETL plan for the demo.

    This creates a deterministic plan without LLM involvement.
    """
    schema_output = str(FIXTURES_DIR / "schemas" / "ascend_schema.yaml")

    steps = [
        # Step 1: Parse XML
        PlanStep(
            actor_name="BODSParserActor",
            tool_name="parse_xml",
            parameters={"xml_path": xml_path},
            status="pending",
        ),
        # Step 2: Extract tables from parsed metadata
        PlanStep(
            actor_name="BODSParserActor",
            tool_name="extract_tables",
            parameters={"metadata": "{context.last_result}"},
            status="pending",
        ),
        # Step 3: Generate schema YAML
        PlanStep(
            actor_name="BODSParserActor",
            tool_name="generate_schema_yaml",
            parameters={
                "tables": "{context.last_result}",
                "output_path": schema_output,
            },
            status="pending",
        ),
        # Step 4: Generate all test data
        PlanStep(
            actor_name="DataGeneratorActor",
            tool_name="generate_all_tables",
            parameters={
                "schema": "{context.step_0_result}",
                "count": record_count,
            },
            status="pending",
        ),
        # Step 5: Write all Parquet files
        PlanStep(
            actor_name="ParquetWriterActor",
            tool_name="write_all_parquets",
            parameters={
                "all_data": "{context.last_result}",
                "base_dir": str(FIXTURES_DIR),
            },
            status="pending",
        ),
    ]

    return Plan(steps=steps, status="PLANNING")


async def run_standalone(
    xml_path: str, record_count: int, seed: int = 42
) -> Dict[str, Any]:
    """
    Run the ETL demo in standalone mode (no database).

    This demonstrates the actors and engine without persistence.

    Args:
        xml_path: Path to BODS XML file
        record_count: Number of records to generate per table
        seed: Random seed for reproducible data generation
    """

    # Get actors (pass seed to DataGeneratorActor for isolated random generator)
    start_time = time.time()

    if not QUIET_MODE:
        logger.info("Running in standalone mode (no database persistence)")

    # Set seed for reproducible output
    random.seed(seed)
    # Get actors
    parser_actor = ActorRegistry.get("BODSParserActor")
    generator_actor = ActorRegistry.get("DataGeneratorActor", seed=seed)
    writer_actor = ActorRegistry.get("ParquetWriterActor")

    if VERBOSE_MODE:
        event_bus = get_event_bus()
        event_bus.subscribe(console_subscriber)

    # Create engine with pre-built plan
    plan = build_etl_plan(xml_path, record_count)
    NativeEngine(default_plan=plan)

    # Execute steps manually (without orchestrator)
    context: Dict[str, Any] = {}
    total_steps = 5

    # Step 1: Parse XML
    log_step(1, total_steps, "Parsing XML metadata", f"Reading from: {xml_path}")
    metadata = parser_actor.parse_xml(xml_path)
    context["step_0_result"] = metadata
    context["last_result"] = metadata
    if not QUIET_MODE:
        logger.info(f"  → Found {len(metadata['tables'])} tables")

    # Step 2: Extract tables
    log_step(
        2,
        total_steps,
        "Extracting table definitions",
        f"Processing {len(metadata['tables'])} table definitions",
    )
    tables = parser_actor.extract_tables(metadata)
    context["step_1_result"] = tables
    context["last_result"] = tables
    source_tables = [t for t in tables if t.get("category") == "source"]
    target_tables = [t for t in tables if t.get("category") == "target"]
    if not QUIET_MODE:
        logger.info(
            f"  → Extracted {len(source_tables)} source tables, {len(target_tables)} target tables"
        )

    # Step 3: Generate schema YAML
    log_step(3, total_steps, "Generating schema YAML", "Creating YAML schema file")
    schema_path = FIXTURES_DIR / "schemas" / "ascend_schema.yaml"
    schema_path.parent.mkdir(parents=True, exist_ok=True)
    yaml_path = parser_actor.generate_schema_yaml(tables, str(schema_path))
    context["step_2_result"] = yaml_path
    context["last_result"] = yaml_path
    if VERBOSE_MODE:
        logger.debug(f"  → Schema written to: {yaml_path}")

    # Step 4: Generate test data
    log_step(
        4,
        total_steps,
        f"Generating test data (~{record_count} records per table)",
        f"Generating data for {len(source_tables)} source tables",
    )
    schema_dict = {
        "tables": {
            t["name"].lower(): t for t in tables if t.get("category") == "source"
        }
    }
    all_data = generator_actor.generate_all_tables(schema_dict, record_count)
    context["step_3_result"] = all_data
    context["last_result"] = all_data
    total_records = sum(len(data) for data in all_data.values())
    if not QUIET_MODE:
        logger.info(
            f"  → Generated {total_records:,} total records across {len(all_data)} tables"
        )

    # Step 5: Write Parquet files
    log_step(
        5,
        total_steps,
        "Writing Parquet files",
        f"Writing {len(all_data)} tables to Parquet format",
    )
    outputs = writer_actor.write_all_parquets(all_data, str(FIXTURES_DIR))
    context["step_4_result"] = outputs
    context["last_result"] = outputs
    if VERBOSE_MODE:
        logger.debug(f"  → Wrote {len(outputs)} Parquet files")
        for table_name, file_path in outputs.items():
            logger.debug(f"    - {table_name}: {file_path}")

    # Validation (only in verbose mode)
    if VERBOSE_MODE and outputs:
        sample_file = list(outputs.values())[0]
        validation = writer_actor.validate_output(sample_file)
        logger.debug(f"  → Sample validation: {validation}")

    elapsed_time = time.time() - start_time

    return {
        "status": "completed",
        "metadata": metadata,
        "tables": tables,
        "tables_count": len(tables),
        "source_tables": source_tables,
        "target_tables": target_tables,
        "all_data": all_data,
        "records_generated": total_records,
        "record_count": record_count,
        "files_written": len(outputs),
        "output_files": outputs,
        "xml_path": xml_path,
        "fixtures_dir": str(FIXTURES_DIR),
        "time_elapsed": elapsed_time,
    }


async def run_with_orchestrator(
    xml_path: str, record_count: int, seed: int = 42
) -> Dict[str, Any]:
    """
    Run the ETL demo with full orchestrator (requires database).

    Args:
        xml_path: Path to BODS XML file
        record_count: Number of records to generate per table
        seed: Random seed for reproducible data generation
    """
    from framework.orchestrator import Orchestrator
    from framework.persistence.database import async_session_maker

    start_time = time.time()

    if not QUIET_MODE:
        logger.info("Running with full orchestrator (database persistence enabled)")

    # Subscribe to events (only in verbose mode)
    if VERBOSE_MODE:
        event_bus = get_event_bus()
        event_bus.subscribe(console_subscriber)
    else:
        event_bus = get_event_bus()

    # Create engine with pre-built plan
    plan = build_etl_plan(xml_path, record_count)
    engine = NativeEngine(default_plan=plan)

    # Create orchestrator
    orchestrator = Orchestrator(
        engine=engine,
        session_maker=async_session_maker,
        event_bus=event_bus,
    )

    # Get actors (pass seed to DataGeneratorActor for isolated random generator)
    actors = [
        ActorRegistry.get("BODSParserActor"),
        ActorRegistry.get("DataGeneratorActor", seed=seed),
        ActorRegistry.get("ParquetWriterActor"),
    ]

    # Run orchestration
    goal = (
        f"Parse BODS XML from {xml_path} and generate {record_count} "
        "test records per table as Parquet files"
    )

    if not QUIET_MODE:
        log_step(1, 5, "Starting orchestration", f"Goal: {goal}")

    result = await orchestrator.run(
        goal=goal,
        actors=actors,
        context={"xml_path": xml_path, "record_count": record_count},
    )

    all_data = result.context.get("step_3_result", {})
    outputs = result.context.get("step_4_result", {})
    tables = result.context.get("step_1_result", [])
    _metadata = result.context.get("step_0_result", {})

    source_tables = [
        t for t in tables if isinstance(t, dict) and t.get("category") == "source"
    ]
    target_tables = [
        t for t in tables if isinstance(t, dict) and t.get("category") == "target"
    ]
    total_records = (
        sum(len(data) for data in all_data.values())
        if isinstance(all_data, dict)
        else 0
    )

    elapsed_time = time.time() - start_time

    # Extract summary data from context
    len(result.context.get("step_1_result", [])) if result.context else 0
    result.context.get("records_generated", 0) if result.context else 0
    len(result.context.get("step_4_result", {})) if result.context else 0

    return {
        "status": result.status.value,
        "process_id": str(result.process_id),
        "steps_executed": len(result.step_results),
        "context": result.context,
        "error": result.error,
        "xml_path": xml_path,
        "record_count": record_count,
        "tables": tables,
        "tables_count": len(tables),
        "source_tables": source_tables,
        "target_tables": target_tables,
        "all_data": all_data,
        "records_generated": total_records,
        "files_written": len(outputs) if isinstance(outputs, dict) else 0,
        "output_files": outputs,
        "fixtures_dir": str(FIXTURES_DIR),
        "time_elapsed": elapsed_time,
    }


def _calculate_file_paths(file_path: str, report_path: Path) -> tuple[Path, Path]:
    file_path_obj = Path(file_path)
    if file_path_obj.is_relative_to(PROJECT_ROOT):
        display_path = file_path_obj.relative_to(PROJECT_ROOT)
        report_dir = report_path.parent.relative_to(PROJECT_ROOT)
        file_dir = file_path_obj.relative_to(PROJECT_ROOT)
        href_path = Path("../" * len(report_dir.parts)) / file_dir
    else:
        display_path = file_path_obj
        href_path = file_path_obj
    return display_path, href_path


def generate_html_report(result: Dict[str, Any], args: argparse.Namespace) -> str:
    output_dir = PROJECT_ROOT / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    report_path = output_dir / "demo_report.html"

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    xml_path = result.get("xml_path", "N/A")
    record_count = result.get("record_count", 0)
    tables = result.get("tables", [])
    all_data = result.get("all_data", {})
    output_files = result.get("output_files", {})
    status = result.get("status", "unknown")
    fixtures_dir = result.get("fixtures_dir", str(FIXTURES_DIR))

    table_records = {}
    for table_name, data in all_data.items():
        if isinstance(data, list):
            table_records[table_name] = len(data)
        else:
            table_records[table_name] = 0

    input_files = []
    expected_files = []
    for key, file_path in output_files.items():
        if isinstance(file_path, str):
            if "_input" in key:
                input_files.append((key.replace("_input", ""), file_path))
            elif "_expected" in key:
                expected_files.append((key.replace("_expected", ""), file_path))

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>JAF ETL Demo Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #ffb00f 0%, #ff4c89 100%);
            color: white;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .header h1 {{
            margin: 0 0 10px 0;
            font-size: 2em;
        }}
        .header .timestamp {{
            opacity: 0.9;
            font-size: 0.9em;
        }}
        .section {{
            background: white;
            padding: 25px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .section h2 {{
            margin-top: 0;
            color: #ff4c89;
            border-bottom: 2px solid #ff4c89;
            padding-bottom: 10px;
        }}
        .section h3 {{
            margin-top: 20px;
            margin-bottom: 10px;
            color: #ff4c89;
            font-size: 1.2em;
        }}
        .parameters {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
        }}
        .parameter {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            border-left: 4px solid #ffb00f;
        }}
        .parameter-label {{
            font-weight: bold;
            color: #666;
            font-size: 0.9em;
            margin-bottom: 5px;
        }}
        .parameter-value {{
            color: #333;
            word-break: break-all;
        }}
        .status-badge {{
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 0.9em;
        }}
        .status-completed {{
            background: #d4edda;
            color: #155724;
        }}
        .status-failed {{
            background: #f8d7da;
            color: #721c24;
        }}
        .status-unknown {{
            background: #fff3cd;
            color: #856404;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #ff4c89;
            color: white;
            font-weight: 600;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .file-link {{
            color: #ffb00f;
            text-decoration: none;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }}
        .file-link:hover {{
            color: #ff4c89;
            text-decoration: underline;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}
        .stat-card {{
            background: linear-gradient(135deg, #ffb00f 0%, #ff4c89 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        .stat-card .stat-value {{
            font-size: 2em;
            font-weight: bold;
            margin: 10px 0;
        }}
        .stat-card .stat-label {{
            font-size: 0.9em;
            opacity: 0.9;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 JAF ETL Demo Report</h1>
        <div class="timestamp">Generated: {timestamp}</div>
    </div>

    <div class="section">
        <h2>📊 Execution Summary</h2>
        <div class="stats">
            <div class="stat-card">
                <div class="stat-label">Status</div>
                <div class="stat-value">
                    <span class="status-badge status-{status.lower()}">{status.upper()}</span>
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Tables Generated</div>
                <div class="stat-value">{len(tables)}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Records</div>
                <div class="stat-value">{sum(table_records.values())}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Parquet Files</div>
                <div class="stat-value">{len(output_files)}</div>
            </div>
        </div>
    </div>

    <div class="section">
        <h2>⚙️ Parameters Used</h2>
        <div class="parameters">
            <div class="parameter">
                <div class="parameter-label">XML Source</div>
                <div class="parameter-value">{xml_path}</div>
            </div>
            <div class="parameter">
                <div class="parameter-label">Records per Table</div>
                <div class="parameter-value">{record_count}</div>
            </div>
            <div class="parameter">
                <div class="parameter-label">Output Directory</div>
                <div class="parameter-value">{fixtures_dir}</div>
            </div>
            <div class="parameter">
                <div class="parameter-label">Standalone Mode</div>
                <div class="parameter-value">{"Yes" if args.standalone else "No"}</div>
            </div>
        </div>
    </div>

    <div class="section">
        <h2>📋 Tables Generated</h2>
        <table>
            <thead>
                <tr>
                    <th>Table Name</th>
                    <th>Category</th>
                    <th>Record Count</th>
                </tr>
            </thead>
            <tbody>
"""
    for table in tables:
        if isinstance(table, dict):
            table_name = table.get("name", "Unknown")
            category = table.get("category", "unknown")
            record_count_table = table_records.get(table_name.lower(), 0)
            html_content += f"""
                <tr>
                    <td><strong>{table_name}</strong></td>
                    <td>{category}</td>
                    <td>{record_count_table}</td>
                </tr>
"""

    html_content += """
            </tbody>
        </table>
    </div>

    <div class="section">
        <h2>📁 Generated Parquet Files</h2>
"""
    if input_files:
        html_content += """
        <h3>Input Files</h3>
        <table>
            <thead>
                <tr>
                    <th>Table Name</th>
                    <th>File Path</th>
                </tr>
            </thead>
            <tbody>
"""
        for table_name, file_path in input_files:
            display_path, href_path = _calculate_file_paths(file_path, report_path)
            html_content += f"""
                <tr>
                    <td><strong>{table_name}</strong></td>
                    <td><a href="{href_path}" class="file-link">{display_path}</a></td>
                </tr>
"""
        html_content += """
            </tbody>
        </table>
"""
    if expected_files:
        html_content += """
        <h3>Expected Output Files</h3>
        <table>
            <thead>
                <tr>
                    <th>Table Name</th>
                    <th>File Path</th>
                </tr>
            </thead>
            <tbody>
"""
        for table_name, file_path in expected_files:
            display_path, href_path = _calculate_file_paths(file_path, report_path)
            html_content += f"""
                <tr>
                    <td><strong>{table_name}</strong></td>
                    <td><a href="{href_path}" class="file-link">{display_path}</a></td>
                </tr>
"""
        html_content += """
            </tbody>
        </table>
"""

    html_content += """
    </div>

    <div class="section">
        <h2>📈 Record Counts per Table</h2>
        <table>
            <thead>
                <tr>
                    <th>Table Name</th>
                    <th>Records Generated</th>
                </tr>
            </thead>
            <tbody>
"""

    for table_name, count in sorted(table_records.items()):
        html_content += f"""
                <tr>
                    <td><strong>{table_name}</strong></td>
                    <td>{count}</td>
                </tr>
"""

    html_content += """
            </tbody>
        </table>
    </div>

    <div style="text-align: center; margin-top: 40px; color: #666; font-size: 0.9em;">
        <p>Generated by JAF ETL Demo | Jems AI Framework</p>
    </div>
</body>
</html>
"""

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return str(report_path)


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="JAF ETL Demo - Generate test datasets from BODS XML"
    )
    parser.add_argument(
        "--standalone",
        action="store_true",
        help="Run without database (no persistence)",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=75,
        help="Number of records to generate per table (default: 75)",
    )
    parser.add_argument(
        "--xml",
        type=str,
        default=str(XML_PATH),
        help=f"Path to BODS XML file (default: {XML_PATH})",
    )
    parser.add_argument(
        "--agentic",
        action="store_true",
        help="Use CrewAI adapter for LLM-based planning (requires OPENAI_API_KEY)",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate HTML summary report after execution",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible data generation (default: 42)",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clear output directory before generating new files",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable detailed step-by-step output",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Minimal output (just success/fail)",
    )

    args = parser.parse_args()

    if args.verbose and args.quiet:
        logger.error("Cannot use --verbose and --quiet together")
        sys.exit(1)

    global VERBOSE_MODE, QUIET_MODE
    VERBOSE_MODE = args.verbose
    QUIET_MODE = args.quiet

    if VERBOSE_MODE:
        logging.getLogger().setLevel(logging.DEBUG)
    elif QUIET_MODE:
        logging.getLogger().setLevel(logging.WARNING)

    # Verify XML exists
    if not Path(args.xml).exists():
        logger.error(f"XML file not found: {args.xml}")
        sys.exit(1)

    # Register actors
    register_actors()

    # Set random seed for reproducible output
    import random

    random.seed(args.seed)

    # Clean output directories if requested
    if args.clean:
        import shutil

        for dir_path in [FIXTURES_DIR / "inputs", FIXTURES_DIR / "expected"]:
            if dir_path.exists():
                shutil.rmtree(dir_path)
                logger.info(f"Cleaned directory: {dir_path}")

    # Create output directories
    (FIXTURES_DIR / "schemas").mkdir(parents=True, exist_ok=True)
    (FIXTURES_DIR / "inputs").mkdir(parents=True, exist_ok=True)
    (FIXTURES_DIR / "expected").mkdir(parents=True, exist_ok=True)

    if not QUIET_MODE:
        logger.info("=" * 60)
        logger.info("JAF ETL Demo - TRAFIC NG Test Dataset Generation")
        logger.info("=" * 60)
        if VERBOSE_MODE:
            logger.info(f"XML Source: {args.xml}")
            logger.info(f"Output Directory: {FIXTURES_DIR}")
            logger.info(f"Records per table: {args.count}")
            logger.info(f"Random seed: {args.seed}")
            if args.clean:
                logger.info("Clean mode: output directories cleared")
        logger.info("=" * 60)

    try:
        if args.standalone or not os.getenv("DATABASE_URL"):
            if not args.standalone and not os.getenv("DATABASE_URL"):
                if not QUIET_MODE:
                    logger.warning(
                        "DATABASE_URL not set, falling back to standalone mode"
                    )
            result = await run_standalone(args.xml, args.count, args.seed)
        else:
            result = await run_with_orchestrator(args.xml, args.count, args.seed)

        tables_count = result.get("tables_count", 0)
        records_generated = result.get("records_generated", 0)
        files_written = result.get("files_written", 0)
        time_elapsed = result.get("time_elapsed", 0.0)

        log_summary(tables_count, records_generated, files_written, time_elapsed)

        if result.get("error"):
            if QUIET_MODE:
                print("Failed")
            logger.error(f"Error: {result['error']}")
            sys.exit(1)

        if args.report:
            report_path = generate_html_report(result, args)
            logger.info(f"HTML report generated: {report_path}")

    except Exception as e:
        if QUIET_MODE:
            print("Failed")
        logger.exception(f"Demo failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
