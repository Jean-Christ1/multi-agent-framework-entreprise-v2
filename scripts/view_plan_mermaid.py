#!/usr/bin/env python3
"""
Open Plan Mermaid diagram(s) in the default browser.

Usage (from repo root):
  python scripts/view_plan_mermaid.py

Supports one or more flows: define EXAMPLE_FLOWS as a list of (title, plan).
Generates one HTML with a diagram per flow and opens it in the browser.
"""

import sys
import tempfile
import webbrowser
from pathlib import Path
from typing import List, Tuple

# Add repo root so "framework" is importable (must run before framework imports)
_repo_root = Path(__file__).resolve().parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from framework.types import Plan, PlanStep  # noqa: E402


def _example_plan() -> Plan:
    """Same plan as in docs/COOKBOOK.md."""
    return Plan(
        steps=[
            PlanStep(
                actor_name="ProvisioningActor",
                tool_name="validate_request",
                parameters={},
                status="completed",
                parallel_group=None,
            ),
            PlanStep(
                actor_name="InventoryActor",
                tool_name="check_stock",
                parameters={"sku": "MBP-001"},
                status="completed",
                parallel_group="fetch",
            ),
            PlanStep(
                actor_name="VendorActor",
                tool_name="get_quote",
                parameters={"sku": "MBP-001"},
                status="completed",
                parallel_group="fetch",
            ),
            PlanStep(
                actor_name="ProvisioningActor",
                tool_name="create_order",
                parameters={},
                status="pending",
                parallel_group=None,
            ),
        ],
        status="EXECUTING",
    )


def _reporting_plan() -> Plan:
    """Simple sequential reporting flow."""
    return Plan(
        steps=[
            PlanStep(
                actor_name="ReportActor",
                tool_name="fetch_data",
                parameters={},
                status="completed",
            ),
            PlanStep(
                actor_name="ReportActor",
                tool_name="aggregate",
                parameters={},
                status="completed",
            ),
            PlanStep(
                actor_name="ReportActor",
                tool_name="export_pdf",
                parameters={},
                status="pending",
            ),
        ],
        status="EXECUTING",
    )


def _etl_plan() -> Plan:
    """ETL: extract → transform (parallel) → load."""
    return Plan(
        steps=[
            PlanStep(
                actor_name="ExtractActor",
                tool_name="read_source",
                parameters={},
                status="completed",
            ),
            PlanStep(
                actor_name="TransformActor",
                tool_name="normalize",
                parameters={},
                status="completed",
                parallel_group="transform",
            ),
            PlanStep(
                actor_name="TransformActor",
                tool_name="enrich",
                parameters={},
                status="completed",
                parallel_group="transform",
            ),
            PlanStep(
                actor_name="LoadActor",
                tool_name="write_target",
                parameters={},
                status="pending",
            ),
        ],
        status="EXECUTING",
    )


def _onboarding_plan() -> Plan:
    """Onboarding with mixed statuses: completed, executing, failed, pending (shows all colors)."""
    return Plan(
        steps=[
            PlanStep(
                actor_name="HRActor",
                tool_name="create_account",
                parameters={},
                status="completed",
            ),
            PlanStep(
                actor_name="ITActor",
                tool_name="provision_laptop",
                parameters={},
                status="executing",
            ),
            PlanStep(
                actor_name="ITActor",
                tool_name="assign_license",
                parameters={},
                status="failed",
            ),
            PlanStep(
                actor_name="HRActor",
                tool_name="send_welcome",
                parameters={},
                status="pending",
            ),
        ],
        status="EXECUTING",
    )


def _minimal_plan() -> Plan:
    """Minimal 2-step flow."""
    return Plan(
        steps=[
            PlanStep(
                actor_name="ActorA",
                tool_name="step_one",
                parameters={},
                status="completed",
            ),
            PlanStep(
                actor_name="ActorB",
                tool_name="step_two",
                parameters={},
                status="pending",
            ),
        ],
        status="EXECUTING",
    )


# Define one or more flows: (title, plan). All are rendered on the same page.
EXAMPLE_FLOWS: List[Tuple[str, Plan]] = [
    ("1. Provisioning (parallel + sequential)", _example_plan()),
    ("2. Reporting (sequential)", _reporting_plan()),
    ("3. ETL (extract → parallel transform → load)", _etl_plan()),
    ("4. Onboarding (all status colors: green/blue/red/gray)", _onboarding_plan()),
    ("5. Minimal (2 steps)", _minimal_plan()),
]


def main() -> None:
    diagrams_html: List[str] = []
    for title, plan in EXAMPLE_FLOWS:
        mermaid_str = plan.to_mermaid()
        diagrams_html.append(
            f'  <h2>{title}</h2>\n  <pre class="mermaid">{mermaid_str}</pre>'
        )
    body_section = "\n".join(diagrams_html)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>JAF Plans – Mermaid</title>
  <style>
    body {{ font-family: sans-serif; margin: 1rem; }}
    .mermaid {{ margin: 1rem 0; }}
    h2 {{ margin-top: 2rem; color: #333; }}
  </style>
</head>
<body>
  <h1>Plan diagrams</h1>
{body_section}
  <script type="module">
    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
    mermaid.initialize({{ startOnLoad: true }});
  </script>
</body>
</html>
"""
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".html",
        delete=False,
        encoding="utf-8",
    ) as f:
        f.write(html_content)
        path = f.name
    url = Path(path).as_uri()
    webbrowser.open(url)
    print(f"Opened in browser: {path}")
    print(f"Flows: {[t for t, _ in EXAMPLE_FLOWS]}")
    print("(Edit EXAMPLE_FLOWS in scripts/view_plan_mermaid.py to add/change plans.)")


if __name__ == "__main__":
    main()
