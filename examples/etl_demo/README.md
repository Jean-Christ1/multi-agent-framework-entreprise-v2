# JAF ETL Demo - TRAFIC NG Test Dataset Generation

This demo showcases the JAF (Jems Agentic Framework) capabilities by parsing SAP BODS metadata and generating realistic test datasets for the TRAFIC NG project (Aéroports de Paris).

## Overview

The demo demonstrates:

1. **Framework Components**: Orchestrator, NativeEngine, Actor pattern
2. **XML Parsing**: Extracting table schemas from SAP BODS exports
3. **Data Generation**: Creating realistic aviation domain test data
4. **Parquet Output**: Writing input/expected datasets for ETL testing

## Prerequisites

### Python Environment

```bash
# Ensure Python 3.10+ is installed
python3 --version

# Install dependencies (using uv - recommended)
uv pip install pydantic pydantic-settings sqlalchemy asyncpg python-dotenv pyarrow pandas faker pyyaml lxml

# Or using pip
pip install -r requirements.txt
```

### Required Files

The demo expects the BODS XML file at:

```
docs/export-ascend.xml
```

This file should already be present in the repository.

## Running the Demo

### Standalone Mode (Recommended for First Run)

No database required - runs the ETL actors directly:

```bash
# From project root
python -m examples.etl_demo.run_demo --standalone

# With custom record count (default: 75)
python -m examples.etl_demo.run_demo --standalone --count 100

# Generate HTML report after execution
python -m examples.etl_demo.run_demo --standalone --count 100 --report
# With custom seed for reproducible output (default: 42)
python -m examples.etl_demo.run_demo --standalone --seed 123

# Clean output directories before generating
python -m examples.etl_demo.run_demo --standalone --clean
# Verbose mode for detailed output
python -m examples.etl_demo.run_demo --standalone --verbose

# Quiet mode for minimal output
python -m examples.etl_demo.run_demo --standalone --quiet

# Specify custom XML path
python -m examples.etl_demo.run_demo --standalone --xml /path/to/export.xml
```

### With Orchestrator (Full Framework Demo)

Requires PostgreSQL database:

```bash
# Set database connection
export DATABASE_URL="postgresql+asyncpg://user:password@localhost/jaf_dev"

# Run with full orchestrator
python -m examples.etl_demo.run_demo --count 75
```

### Command Line Options

| Option         | Description                                  | Default                  |
| -------------- | -------------------------------------------- | ------------------------ |
| `--standalone` | Run without database persistence             | False                    |
| `--count N`    | Records to generate per table                | 75                       |
| `--xml PATH`   | Path to BODS XML file                        | `docs/export-ascend.xml` |
| `--agentic`    | Use CrewAI for LLM-based planning            | False                    |
| `--report`     | Generate HTML summary report after execution | False                    |
| `--seed N`     | Random seed for reproducible data generation | 42                       |
| `--clean`      | Clear output directories before generating   | False                    |
| `--xml PATH`   | Path to BODS XML file                        | `docs/export-ascend.xml` |
| `--agentic`    | Use CrewAI for LLM-based planning            | False                    |
| `--verbose`    | Enable detailed step-by-step output          | False                    |
| `--quiet`      | Minimal output (just success/fail)           | False                    |

## Output

### HTML Report

When using the `--report` flag, a comprehensive HTML report is generated in `output/demo_report.html`:

```bash
# Generate report
python -m examples.etl_demo.run_demo --standalone --count 100 --report

# Open report in browser
open output/demo_report.html
```

The report includes:

- **Execution Summary**: Status, tables generated, total records, parquet files
- **Parameters Used**: XML source, record count, output directory, execution mode
- **Tables Generated**: Complete list with categories and record counts
- **Generated Parquet Files**: Links to all input and expected output files
- **Record Counts**: Detailed breakdown per table

### Directory Structure

After running, you'll find:

```
tests/fixtures/trafic_ascend/
├── schemas/
│   └── ascend_schema.yaml        # Extracted table definitions
├── inputs/                       # Source data (SQL Server format)
│   ├── ac_cargo.parquet
│   ├── area.parquet
│   ├── category.parquet
│   ├── company.parquet
│   ├── country.parquet
│   ├── event.parquet
│   ├── eventtypes.parquet
│   ├── gentech.parquet
│   ├── histories.parquet
│   ├── lastdelivery.parquet
│   ├── lastorder.parquet
│   ├── ordersplacedtmp.parquet
│   ├── spectech.parquet
│   ├── v_currenthistories.parquet
│   └── v_histories.parquet
└── expected/                     # Target data (Oracle format)
    ├── tr_dwh_traf_ascend_ac_cargo.parquet
    ├── tr_dwh_traf_ascend_area.parquet
    ├── ... (13 more files)
    └── td_dwh_traf_ascend_v_histories.parquet
```

### Schema YAML

The generated `ascend_schema.yaml` contains:

```yaml
version: "1.0"
source_system: SAP_BODS
tables:
  ac_cargo:
    category: source
    datastore: DS_TRAFIC_ASCENDFEED
    columns:
      - name: ACCARGO
        type: VARCHAR
        size: 1
        nullable: false
      - name: ACCARGODESC
        type: VARCHAR
        size: 50
        nullable: true
    primary_key:
      - ACCARGO
  # ... more tables
```

### Reproducible Output (Seed Support)

The demo supports deterministic data generation using random seeds:

- **Same seed = identical output**: Running with the same seed produces identical data
- **Stable ordering**: Tables and records are generated in a consistent order
- **Default seed**: 42 (can be changed with `--seed N`)

**Example:**

```bash
# Generate data with seed 42
python -m examples.etl_demo.run_demo --standalone --seed 42

# Generate again with same seed - produces identical files
python -m examples.etl_demo.run_demo --standalone --seed 42 --clean

# Different seed produces different data
python -m examples.etl_demo.run_demo --standalone --seed 123
```

**Note:** The `--clean` option clears output directories before generating, ensuring a clean state for reproducible runs.

#### Technical Details

**How Seed Works:**

1. **Actor-Level Isolation**: `DataGeneratorActor` uses an isolated `random.Random(seed)` instance instead of the global `random` module. This ensures:
   - Each actor instance has its own random state
   - Reproducibility is guaranteed even if other code uses `random`
   - Multiple actor instances with the same seed produce identical output

2. **Seed Propagation**: The seed is passed to the actor during initialization:
   ```python
   generator_actor = ActorRegistry.get("DataGeneratorActor", seed=42)
   ```

3. **Guarantees**:
   - **Deterministic**: Same seed → identical output (byte-for-byte identical Parquet files)
   - **Isolated**: Actor's random state is independent of global `random` state
   - **Stable Ordering**: Tables and records are generated in sorted order for consistency

4. **Behavior with Multiple Instances**:
   - Each `DataGeneratorActor` instance with the same seed will produce identical data
   - Instances with different seeds produce different data
   - If seed is `None`, the actor falls back to global `random` (not recommended for reproducibility)

### Reading Parquet Files

```python
import pandas as pd

# Read input data
df_input = pd.read_parquet("tests/fixtures/trafic_ascend/inputs/company.parquet")
print(df_input.head())

# Read expected output
df_expected = pd.read_parquet("tests/fixtures/trafic_ascend/expected/tr_dwh_traf_ascend_company.parquet")
print(df_expected.head())
```

## Demo Actors

### BODSParserActor

Parses SAP BODS XML exports:

- `parse_xml(xml_path)` - Parse XML and extract metadata
- `extract_tables(metadata)` - Categorize source/target tables
- `generate_schema_yaml(tables, output_path)` - Generate schema file

### DataGeneratorActor

Generates realistic aviation test data:

- `generate_lookup_data(table_name, schema, count)` - Simple reference tables
- `generate_complex_data(table_name, schema, count, refs)` - Complex tables with FK
- `generate_all_tables(schema, count)` - All tables with referential integrity

### ParquetWriterActor

Writes Parquet files:

- `write_input_parquet(data, table_name)` - Source format
- `write_expected_parquet(data, table_name)` - Target format with transformations
- `write_all_parquets(all_data, base_dir)` - Batch write all tables

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    run_demo.py                          │
│                   (Entry Point)                         │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│                   Orchestrator                          │
│            (Coordinates Execution)                      │
└─────────────────────┬───────────────────────────────────┘
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ NativeEngine│ │  EventBus   │ │ Persistence │
│  (Execute)  │ │  (Events)   │ │   (State)   │
└──────┬──────┘ └─────────────┘ └─────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────┐
│                    ETL Actors                           │
├─────────────┬─────────────────┬─────────────────────────┤
│ BODSParser  │ DataGenerator   │ ParquetWriter           │
│ Actor       │ Actor           │ Actor                   │
└─────────────┴─────────────────┴─────────────────────────┘
```

## Troubleshooting

### ModuleNotFoundError

```bash
# Ensure you're in the project root
cd /path/to/jaf-framework

# Install dependencies
uv pip install pyarrow pandas faker pyyaml lxml pydantic sqlalchemy
```

### XML File Not Found

```bash
# Verify the file exists
ls -la docs/export-ascend.xml

# Or specify a different path
python -m examples.etl_demo.run_demo --standalone --xml /your/path/export.xml
```

### Database Connection Error

```bash
# For standalone mode (no database needed)
python -m examples.etl_demo.run_demo --standalone

# Or set DATABASE_URL correctly
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/jaf_dev"
```

## Sample Output

```
============================================================
JAF ETL Demo - TRAFIC NG Test Dataset Generation
============================================================
XML Source: /path/to/jaf-framework/docs/export-ascend.xml
Output Directory: /path/to/jaf-framework/tests/fixtures/trafic_ascend
Records per table: 75
============================================================
Running in standalone mode (no database persistence)
============================================================
STEP 1: Parsing XML metadata
============================================================
Parsed: 30 tables, 15 dataflows, 13 workflows
Found 30 tables
============================================================
STEP 2: Extracting table definitions
============================================================
Extracted 15 source tables, 15 target tables
============================================================
STEP 3: Generating schema YAML
============================================================
Schema written to: .../schemas/ascend_schema.yaml
============================================================
STEP 4: Generating test data (~75 records per table)
============================================================
Generated 600+ total records across 15 tables
============================================================
STEP 5: Writing Parquet files
============================================================
Wrote 30 Parquet files
============================================================
Demo Complete!
============================================================
Status: completed
Files generated in: tests/fixtures/trafic_ascend
```

## Next Steps

1. **Use datasets for ETL testing**: Load input parquets, run your Python ETL, compare against expected parquets
2. **Extend with more tables**: Add generators for additional BODS exports
3. **Integrate with CI/CD**: Run demo as part of test setup to regenerate fixtures
