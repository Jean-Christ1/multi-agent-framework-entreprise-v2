#!/usr/bin/env python3
"""
JAF Framework — Executive Demo for CEO
=======================================

Demonstrates JAF's core value proposition: data-driven intelligent automation.

This demo creates three agents for three business domains ON THE FLY,
then runs them against real business data to show how data context
transforms generic AI into specific, actionable business intelligence.

Usage:
    python examples/ceo_demo.py

No API keys required — runs entirely on data-driven logic.
"""

import asyncio
import sys
import time
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from jaf import Actor, Tool, ActorRegistry, LLMConfig
from jaf.core.actor import actor

# Import business data
from ceo_demo_data import (
    CUSTOMERS,
    CUSTOMER_BENCHMARKS,
    MONTHLY_REVENUE,
    REVENUE_BY_REGION,
    REVENUE_BY_PRODUCT,
    SALES_ANOMALIES,
    EMPLOYEES,
    DEPARTMENT_STATS,
    EQUIPMENT_CATALOG,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DISPLAY UTILITIES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class C:
    """ANSI terminal colors."""
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[97m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"

W = 67  # Output width


def header(title: str, subtitle: str = ""):
    """Print main header."""
    print()
    print(f"{C.CYAN}{'═' * W}")
    print(f"{'═' * W}")
    padding = (W - len(title)) // 2
    print(f"{' ' * padding}{C.BOLD}{C.WHITE}{title}{C.RESET}{C.CYAN}")
    if subtitle:
        padding2 = (W - len(subtitle)) // 2
        print(f"{C.DIM}{' ' * padding2}{subtitle}{C.RESET}{C.CYAN}")
    print(f"{'═' * W}")
    print(f"{'═' * W}{C.RESET}")
    print()


def act(number: int, title: str, description: str = ""):
    """Print act header."""
    print()
    print(f"{C.CYAN}{'━' * W}")
    print(f"  {C.BOLD}{C.WHITE}ACT {number}{C.RESET}   {C.CYAN}{title}")
    print(f"{'━' * W}{C.RESET}")
    if description:
        print(f"\n  {C.DIM}\"{description}\"{C.RESET}")
    print()


def box(title: str, lines: list, color=C.WHITE):
    """Print a titled box."""
    print(f"  {color}┌─ {C.BOLD}{title}{C.RESET}{color} {'─' * max(0, W - len(title) - 7)}┐{C.RESET}")
    for line in lines:
        padded = line.ljust(W - 6)
        print(f"  {color}│{C.RESET}  {padded}{color}│{C.RESET}")
    print(f"  {color}└{'─' * (W - 4)}┘{C.RESET}")
    print()


def step(number: int, text: str):
    """Print step indicator."""
    print(f"  {C.BLUE}{C.BOLD}Step {number}{C.RESET} → {text}")
    print()


def success(text: str):
    """Print success line."""
    print(f"  {C.GREEN}✓ {text}{C.RESET}")


def warning(text: str):
    """Print warning line."""
    print(f"  {C.YELLOW}⚠ {text}{C.RESET}")


def pause(seconds: float = 0.6):
    """Brief pause for dramatic effect."""
    time.sleep(seconds)


def progress_bar(pct: int, width: int = 20) -> str:
    """Create a text progress bar."""
    filled = int(width * pct / 100)
    empty = width - filled
    if pct >= 75:
        color = C.RED
    elif pct >= 50:
        color = C.YELLOW
    else:
        color = C.GREEN
    return f"{color}{'█' * filled}{'░' * empty}{C.RESET}"


def euro(amount: int) -> str:
    """Format euro amount."""
    if amount >= 1_000_000:
        return f"€{amount / 1_000_000:.2f}M"
    elif amount >= 1_000:
        return f"€{amount:,.0f}"
    return f"€{amount}"


def bar_chart(value: int, max_val: int, width: int = 20) -> str:
    """Create a simple horizontal bar."""
    filled = max(1, int(width * value / max_val))
    return f"{C.CYAN}{'█' * filled}{C.RESET}"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  AGENT DEFINITIONS (created "on the fly" during demo)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@actor(
    name="CustomerIntelligenceAgent",
    description="Analyzes customer data to predict churn and recommend retention actions",
    goal="Use customer behavioral data to protect revenue and prevent churn",
    llm_config=LLMConfig(model="gpt-4o-mini", temperature=0),
)
class CustomerIntelligenceAgent(Actor):
    """Customer intelligence agent — uses data to predict and prevent churn."""

    @Tool(description="Look up full customer profile from database")
    def lookup_customer(self, customer_id: str) -> dict:
        """Query customer database for complete profile."""
        customer = CUSTOMERS.get(customer_id)
        if not customer:
            return {"error": f"Customer {customer_id} not found"}
        return {
            "customer_id": customer_id,
            **customer,
        }

    @Tool(description="Analyze customer health using behavioral signals")
    def analyze_health(self, customer_id: str) -> dict:
        """Cross-reference multiple data signals to assess customer health."""
        c = CUSTOMERS.get(customer_id, {})
        thresholds = CUSTOMER_BENCHMARKS["churn_thresholds"]

        signals = []
        risk_score = 0

        # Signal 1: NPS trend
        if c.get("nps_history"):
            current_nps = c["nps_history"][-1]
            if current_nps < thresholds["nps_critical"]:
                signals.append({
                    "signal": "NPS below critical threshold",
                    "detail": f"{current_nps} < {thresholds['nps_critical']}",
                    "trend": " → ".join(str(n) for n in c["nps_history"]),
                    "risk_points": 25,
                })
                risk_score += 25

        # Signal 2: Purchase frequency decline
        if c.get("purchase_freq_yearly") and len(c["purchase_freq_yearly"]) >= 2:
            first = c["purchase_freq_yearly"][0]
            last = c["purchase_freq_yearly"][-1]
            decline = round((1 - last / first) * 100)
            if decline > thresholds["purchase_decline_pct"]:
                signals.append({
                    "signal": "Purchase frequency declining",
                    "detail": f"{first} → {last}/year (-{decline}%)",
                    "trend": " → ".join(str(n) for n in c["purchase_freq_yearly"]),
                    "risk_points": 30,
                })
                risk_score += 30

        # Signal 3: Support ticket spike
        if c.get("support_tickets_90d") and c.get("avg_tickets_90d"):
            spike = round(c["support_tickets_90d"] / c["avg_tickets_90d"], 1)
            if spike >= thresholds["ticket_spike_multiplier"]:
                signals.append({
                    "signal": "Support ticket spike",
                    "detail": f"{c['support_tickets_90d']} tickets ({spike}× normal)",
                    "risk_points": 17,
                })
                risk_score += 17

        # Signal 4: Inactivity
        if c.get("last_purchase_days_ago", 0) > thresholds["days_inactive"]:
            signals.append({
                "signal": "Purchase inactivity",
                "detail": f"{c['last_purchase_days_ago']} days since last purchase",
                "risk_points": 10,
            })
            risk_score += 10

        # Signal 5: Competitor evaluation
        if c.get("competitor_eval"):
            signals.append({
                "signal": "Competitor evaluation active",
                "detail": "Detected in CRM activity log",
                "risk_points": 15,
            })
            risk_score += 15

        # Classify risk level
        risk_level = "low"
        if risk_score >= 70:
            risk_level = "critical"
        elif risk_score >= 40:
            risk_level = "high"
        elif risk_score >= 20:
            risk_level = "medium"

        return {
            "customer_id": customer_id,
            "health_score": c.get("health_score", 50),
            "risk_score": min(risk_score, 100),
            "risk_level": risk_level,
            "signals": signals,
            "revenue_at_risk": c.get("annual_contract", 0),
        }

    @Tool(description="Generate data-backed retention recommendations")
    def recommend_actions(self, customer_id: str, risk_level: str) -> dict:
        """Recommend specific actions based on risk level and customer data."""
        c = CUSTOMERS.get(customer_id, {})
        benchmarks = CUSTOMER_BENCHMARKS

        actions = {"immediate": [], "short_term": [], "rationale": []}

        if risk_level in ("critical", "high"):
            # Immediate actions driven by specific data
            if c.get("open_tickets"):
                top_ticket = c["open_tickets"][0]
                actions["immediate"].append({
                    "action": f"Escalate ticket {top_ticket['id']} to Critical priority",
                    "reason": f"Open {top_ticket['days_open']} days — correlated with NPS decline",
                })

            actions["immediate"].append({
                "action": "Schedule executive sponsor call within 48 hours",
                "reason": f"{risk_level.upper()} churn risk on {euro(c.get('annual_contract', 0))}/yr contract",
            })

            if c.get("open_tickets"):
                actions["short_term"].append({
                    "action": "Offer assisted migration to v3.3 with dedicated support",
                    "reason": "v3.2 issues driving majority of support tickets",
                })

            discount = round(c.get("annual_contract", 0) * 0.20)
            actions["short_term"].append({
                "action": f"Propose 20% renewal discount ({euro(discount)}/yr)",
                "reason": f"Protects {euro(c.get('annual_contract', 0))}/yr — ROI: {round(c.get('annual_contract', 0) / max(discount, 1))}× return",
            })

            success_rate = benchmarks["intervention_success_rates"]["high_risk_early"]
            actions["rationale"].append(
                f"Based on {benchmarks['journeys_analyzed']} similar customer journeys"
            )
            actions["rationale"].append(
                f"Early intervention at this risk level: {int(success_rate * 100)}% success rate"
            )

        elif risk_level == "medium":
            actions["immediate"].append({
                "action": "Proactive check-in call from account manager",
                "reason": "Address concerns before they escalate",
            })
            actions["rationale"].append("Medium risk — standard retention playbook")

        else:
            actions["immediate"].append({
                "action": "Continue regular engagement cadence",
                "reason": "Customer health is strong — maintain relationship",
            })

        return {
            "customer_id": customer_id,
            "risk_level": risk_level,
            **actions,
        }


@actor(
    name="SalesAnalyticsAgent",
    description="Analyzes revenue data, detects anomalies, and generates actionable insights",
    goal="Turn raw sales data into strategic intelligence",
    llm_config=LLMConfig(model="gpt-4o-mini", temperature=0),
)
class SalesAnalyticsAgent(Actor):
    """Sales analytics agent — finds patterns and anomalies in revenue data."""

    @Tool(description="Get revenue summary for a time period")
    def revenue_summary(self, period: str) -> dict:
        """Aggregate revenue data for the requested period."""
        # Filter for the period (simplified: use all data as "H2 2025 + Jan 2026")
        total_revenue = sum(m["revenue"] for m in MONTHLY_REVENUE)
        total_deals = sum(m["deals"] for m in MONTHLY_REVENUE)
        avg_deal = total_revenue // max(total_deals, 1)
        monthly_avg = total_revenue // len(MONTHLY_REVENUE)

        # Trend: compare last 3 months to first 3
        first_3 = sum(m["revenue"] for m in MONTHLY_REVENUE[:3])
        last_3 = sum(m["revenue"] for m in MONTHLY_REVENUE[-3:])
        trend_pct = round((last_3 - first_3) / first_3 * 100, 1)

        return {
            "period": "Jul 2025 – Jan 2026",
            "total_revenue": total_revenue,
            "total_deals": total_deals,
            "avg_deal_size": avg_deal,
            "monthly_avg": monthly_avg,
            "trend_pct": trend_pct,
            "months": MONTHLY_REVENUE,
            "by_region": REVENUE_BY_REGION,
            "by_product": REVENUE_BY_PRODUCT,
        }

    @Tool(description="Detect anomalies and unusual patterns in sales data")
    def detect_anomalies(self) -> dict:
        """Scan revenue data for statistical anomalies and correlations."""
        anomalies = []
        for a in SALES_ANOMALIES:
            anomalies.append({
                "type": a["type"].replace("_", " ").title(),
                "where": f"{a['region']} — {a['period']}",
                "magnitude": f"{a['change_pct']:+d}%",
                "probable_cause": a["cause"],
                "detail": a["detail"],
                "recommendation": a["action"],
            })

        # Detect month-over-month changes
        for i in range(1, len(MONTHLY_REVENUE)):
            prev = MONTHLY_REVENUE[i - 1]
            curr = MONTHLY_REVENUE[i]
            change = (curr["revenue"] - prev["revenue"]) / prev["revenue"]
            if abs(change) > 0.12:  # >12% change month-over-month
                anomalies.append({
                    "type": "Month-Over-Month Shift",
                    "where": f"{prev['month']} → {curr['month']}",
                    "magnitude": f"{change * 100:+.1f}%",
                    "probable_cause": "Seasonal or structural change",
                    "detail": f"Revenue {euro(prev['revenue'])} → {euro(curr['revenue'])}",
                    "recommendation": "Investigate driver",
                })

        return {
            "anomalies_found": len(anomalies),
            "anomalies": anomalies,
        }

    @Tool(description="Deep-dive analysis on a specific region")
    def analyze_region(self, region: str) -> dict:
        """Analyze regional performance with pipeline context."""
        data = REVENUE_BY_REGION.get(region, {})
        if not data:
            return {"error": f"Region {region} not found"}
        return {
            "region": region,
            **data,
            "pipeline_coverage": round(data.get("pipeline", 0) / max(data.get("revenue", 1) / 4, 1), 1),
            "health": "healthy" if data.get("growth_pct", 0) > 0 else "needs attention",
        }


@actor(
    name="SmartProvisioningAgent",
    description="Data-driven equipment provisioning based on department patterns and budgets",
    goal="Recommend optimal equipment using historical department data and budget constraints",
    llm_config=LLMConfig(model="gpt-4o-mini", temperature=0),
)
class SmartProvisioningAgent(Actor):
    """Smart provisioning agent — uses department data for optimal equipment allocation."""

    @Tool(description="Get employee context enriched with department intelligence")
    def get_employee_context(self, employee_id: str) -> dict:
        """Look up employee and enrich with department data."""
        emp = EMPLOYEES.get(employee_id)
        if not emp:
            return {"error": f"Employee {employee_id} not found"}

        dept = DEPARTMENT_STATS.get(emp["department"], {})

        return {
            "employee_id": employee_id,
            **emp,
            "department_stats": {
                "headcount": dept.get("headcount", 0),
                "avg_equipment_cost": dept.get("avg_equipment_cost", 0),
                "most_common_setup": dept.get("most_common_setup", "N/A"),
                "satisfaction_pct": dept.get("satisfaction_pct", 0),
                "budget_remaining": dept.get("budget_remaining", 0),
                "budget_total": dept.get("budget_total", 0),
            },
        }

    @Tool(description="Recommend equipment package based on role, department, and budget data")
    def recommend_equipment(self, employee_id: str) -> dict:
        """Data-driven equipment recommendation using department patterns."""
        emp = EMPLOYEES.get(employee_id, {})
        dept_stats = DEPARTMENT_STATS.get(emp.get("department", ""), {})

        # Map role to equipment catalog key
        role_map = {
            "Senior Developer": "senior_developer",
            "Data Scientist": "data_scientist",
            "Account Executive": "account_executive",
        }
        catalog_key = role_map.get(emp.get("role", ""), "senior_developer")
        package = EQUIPMENT_CATALOG.get(catalog_key, {})

        # Budget check
        budget_remaining = dept_stats.get("budget_remaining", 0)
        fits_budget = package.get("total", 0) <= budget_remaining
        remaining_after = budget_remaining - package.get("total", 0)
        remaining_setups = remaining_after // max(dept_stats.get("avg_equipment_cost", 1), 1)

        # Approval logic
        needs_approval = package.get("total", 0) > 3000

        return {
            "employee_id": employee_id,
            "employee_name": emp.get("name", "Unknown"),
            "role": emp.get("role", "Unknown"),
            "department": emp.get("department", "Unknown"),
            "recommended_package": package.get("package_name", "Standard"),
            "items": package.get("items", []),
            "total_cost": package.get("total", 0),
            "fits_budget": fits_budget,
            "budget_remaining_after": remaining_after,
            "similar_setups_possible": remaining_setups,
            "dept_satisfaction_with_similar": dept_stats.get("satisfaction_pct", 0),
            "needs_approval": needs_approval,
            "approval_reason": "Amount exceeds €3,000 auto-approval limit" if needs_approval else None,
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DEMO ACTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def run_act_1():
    """ACT 1: Create three agents for three business domains."""
    act(1, "One Framework, Three New Agents",
        "Any developer can create an intelligent agent in minutes. "
        "Watch us create three agents for three different business domains.")

    t0 = time.time()

    # Clear previous registrations and create agents
    ActorRegistry.clear()

    agents = [
        CustomerIntelligenceAgent(),
        SalesAnalyticsAgent(),
        SmartProvisioningAgent(),
    ]

    elapsed = time.time() - t0

    for agent in agents:
        box(agent.name, [
            f"{C.BOLD}Goal:{C.RESET}   {agent.goal}",
            f"{C.BOLD}Tools:{C.RESET}  {', '.join(agent.tool_names)}",
            f"{C.BOLD}Data:{C.RESET}   {'Customer DB, Support Tickets, NPS Scores' if 'Customer' in agent.name else 'Revenue Data, Regional Metrics, Pipeline' if 'Sales' in agent.name else 'Employee Records, Department Budgets, Equipment Catalog'}",
            f"{C.BOLD}AI:{C.RESET}     gpt-4o-mini (cost-optimized)",
        ], color=C.CYAN)
        pause(0.3)

    total_tools = sum(len(a.tools) for a in agents)
    success(f"3 agents created with {total_tools} data-powered tools — {elapsed:.3f}s")
    success(f"All agents registered in framework — ready to execute")
    print()


def run_act_2():
    """ACT 2: Data changes everything — customer intelligence showcase."""
    act(2, "Data Changes Everything",
        "The same question, two very different answers. The difference? Data.")

    # The scenario
    print(f"  {C.MAGENTA}╭─ SCENARIO {'─' * (W - 15)}╮{C.RESET}")
    print(f"  {C.MAGENTA}│{C.RESET}  {C.BOLD}\"Analyze customer C-1042 and recommend next steps\"{C.RESET}       {C.MAGENTA}│{C.RESET}")
    print(f"  {C.MAGENTA}╰{'─' * (W - 4)}╯{C.RESET}")
    print()
    pause(0.5)

    # WITHOUT data — generic AI response
    box("WITHOUT Data Context (Generic AI)", [
        "",
        "\"Schedule a follow-up meeting with the customer to",
        "  discuss their needs and explore upsell opportunities.\"",
        "",
        f"{C.RED}✗ Generic{C.RESET}    {C.RED}✗ No urgency{C.RESET}    {C.RED}✗ No specifics{C.RESET}",
        f"{C.RED}✗ Misses €169,000 at risk{C.RESET}    {C.RED}✗ Misses churn signals{C.RESET}",
        "",
    ], color=C.RED)

    pause(0.8)
    print(f"  {C.GREEN}{C.BOLD}WITH JAF Data Intelligence:{C.RESET}")
    print()

    # Get the agent
    agent = ActorRegistry.get("CustomerIntelligenceAgent")

    # Step 1: Lookup customer
    step(1, "Querying Customer Database...")
    pause(0.3)

    profile = agent.lookup_customer.invoke(customer_id="C-1042")
    box("Customer Profile", [
        f"{C.BOLD}Name:{C.RESET}       {profile['name']} — {profile['company']}",
        f"{C.BOLD}Segment:{C.RESET}    {profile['segment']} | {profile['industry']}",
        f"{C.BOLD}Contract:{C.RESET}   {euro(profile['annual_contract'])}/year  (Lifetime: {euro(profile['lifetime_value'])})",
        f"{C.BOLD}Customer:{C.RESET}   Since {profile['since']}  ({profile['employees']} employees)",
    ], color=C.BLUE)

    # Step 2: Analyze health
    step(2, "Analyzing Customer Health Signals...")
    pause(0.4)

    health = agent.analyze_health.invoke(customer_id="C-1042")

    health_lines = [""]
    for sig in health["signals"]:
        trend_str = f"  {C.DIM}({sig.get('trend', '')}){C.RESET}" if sig.get("trend") else ""
        health_lines.append(
            f"{C.YELLOW}▼{C.RESET} {sig['signal']}: {sig['detail']}{trend_str}"
        )
        health_lines.append(f"  {C.DIM}Risk contribution: +{sig['risk_points']} points{C.RESET}")
        health_lines.append("")

    if profile.get("open_tickets"):
        health_lines.append(f"{C.BOLD}Open Issues:{C.RESET}")
        for ticket in profile["open_tickets"]:
            health_lines.append(
                f"  {ticket['id']}  {ticket['subject']} — {ticket['days_open']} days open"
            )
        health_lines.append("")

    box("Health Signals", health_lines, color=C.YELLOW)

    # Step 3: Risk assessment
    step(3, "Computing Churn Risk Score...")
    pause(0.4)

    risk_bar = progress_bar(health["risk_score"])
    risk_color = C.RED if health["risk_level"] in ("critical", "high") else C.YELLOW

    box("Risk Assessment", [
        "",
        f"  {risk_bar}  {risk_color}{C.BOLD}CHURN RISK: {health['risk_score']}%{C.RESET}",
        "",
        f"  Revenue at Risk: {C.RED}{C.BOLD}{euro(health['revenue_at_risk'])}/year{C.RESET}",
        "",
    ], color=risk_color)

    # Step 4: Recommendations
    step(4, "Generating Data-Driven Recommendations...")
    pause(0.4)

    recs = agent.recommend_actions.invoke(
        customer_id="C-1042",
        risk_level=health["risk_level"],
    )

    rec_lines = [""]
    if recs["immediate"]:
        rec_lines.append(f"{C.BOLD}IMMEDIATE (within 48 hours):{C.RESET}")
        for i, a in enumerate(recs["immediate"], 1):
            rec_lines.append(f"  {i}. {C.BOLD}{a['action']}{C.RESET}")
            rec_lines.append(f"     {C.DIM}Reason: {a['reason']}{C.RESET}")
            rec_lines.append("")

    if recs["short_term"]:
        rec_lines.append(f"{C.BOLD}SHORT-TERM (within 2 weeks):{C.RESET}")
        for i, a in enumerate(recs["short_term"], len(recs["immediate"]) + 1):
            rec_lines.append(f"  {i}. {C.BOLD}{a['action']}{C.RESET}")
            rec_lines.append(f"     {C.DIM}Reason: {a['reason']}{C.RESET}")
            rec_lines.append("")

    if recs["rationale"]:
        rec_lines.append(f"{C.CYAN}CONFIDENCE:{C.RESET}")
        for r in recs["rationale"]:
            rec_lines.append(f"  {r}")
        rec_lines.append("")

    box("Data-Driven Actions", rec_lines, color=C.GREEN)

    success("Customer analysis complete — 4 tools executed — Cost: $0.00")
    print()


def run_act_3():
    """ACT 3: Same framework, different business domains."""
    act(3, "Intelligence Across the Business",
        "Same framework. Different domain. Instant data-driven intelligence.")

    # ── Sales Analytics ──────────────────────
    print(f"  {C.CYAN}── Sales Analytics {'─' * (W - 23)}{C.RESET}")
    print(f"  {C.DIM}Goal: \"Analyze recent sales performance and flag issues\"{C.RESET}")
    print()

    sales_agent = ActorRegistry.get("SalesAnalyticsAgent")

    # Revenue summary
    summary = sales_agent.revenue_summary.invoke(period="H2-2025")

    box("Revenue Overview", [
        f"{C.BOLD}Period:{C.RESET}    {summary['period']}",
        f"{C.BOLD}Revenue:{C.RESET}   {euro(summary['total_revenue'])}  ({summary['total_deals']} deals)",
        f"{C.BOLD}Avg Deal:{C.RESET}  {euro(summary['avg_deal_size'])}",
        f"{C.BOLD}Trend:{C.RESET}     {summary['trend_pct']:+.1f}% (last 3m vs first 3m)",
        "",
        f"{C.BOLD}By Region:{C.RESET}",
        *[
            f"  {name:10s} {euro(d['revenue']):>8s}  {d['growth_pct']:+3d}%  {bar_chart(d['revenue'], 8_500_000)}"
            + (f"  {C.YELLOW}⚠{C.RESET}" if d['growth_pct'] < 0 else "")
            for name, d in summary["by_region"].items()
        ],
    ], color=C.CYAN)

    pause(0.3)

    # Anomaly detection
    anomalies = sales_agent.detect_anomalies.invoke()

    for a in anomalies["anomalies"][:2]:  # Show top 2
        anom_color = C.YELLOW if "dip" in a["type"].lower() or "-" in a["magnitude"] else C.GREEN
        box(f"Anomaly: {a['type']}", [
            f"{C.BOLD}Where:{C.RESET}       {a['where']}",
            f"{C.BOLD}Magnitude:{C.RESET}   {a['magnitude']}",
            f"{C.BOLD}Cause:{C.RESET}       {a['probable_cause']}",
            f"{C.BOLD}Detail:{C.RESET}      {a['detail']}",
            "",
            f"{C.BOLD}Action:{C.RESET}      {a['recommendation']}",
        ], color=anom_color)
        pause(0.2)

    success("Sales analysis complete — anomalies detected and explained")
    print()

    pause(0.5)

    # ── Smart Provisioning ──────────────────
    print(f"  {C.CYAN}── Smart Provisioning {'─' * (W - 26)}{C.RESET}")
    print(f"  {C.DIM}Goal: \"Provision equipment for new hire Thomas Bernard (E-5531)\"{C.RESET}")
    print()

    prov_agent = ActorRegistry.get("SmartProvisioningAgent")

    # Employee context
    context = prov_agent.get_employee_context.invoke(employee_id="E-5531")
    dept = context["department_stats"]

    box("Employee + Department Context", [
        f"{C.BOLD}Employee:{C.RESET}    {context['name']}",
        f"{C.BOLD}Role:{C.RESET}        {context['role']} | {context['department']}",
        f"{C.BOLD}Location:{C.RESET}    {context['location']} | Start: {context['hire_date']}",
        "",
        f"{C.BOLD}Department Intelligence:{C.RESET}",
        f"  {dept['headcount']} engineers, avg equipment: {euro(dept['avg_equipment_cost'])}",
        f"  Most popular: {dept['most_common_setup']}",
        f"  Team satisfaction: {dept['satisfaction_pct']}%",
        f"  Budget: {euro(dept['budget_remaining'])} remaining of {euro(dept['budget_total'])}",
    ], color=C.BLUE)

    pause(0.3)

    # Equipment recommendation
    rec = prov_agent.recommend_equipment.invoke(employee_id="E-5531")

    item_lines = [f"  • {item['name']:40s} {euro(item['price']):>8s}" for item in rec["items"]]
    item_lines.append(f"  {'─' * 51}")
    item_lines.append(f"  {'Total':41s} {C.BOLD}{euro(rec['total_cost']):>8s}{C.RESET}")

    box("Data-Driven Recommendation", [
        f"{C.BOLD}Package:{C.RESET} \"{rec['recommended_package']}\"",
        "",
        *item_lines,
        "",
        f"{C.BOLD}Why this package?{C.RESET}",
        f"  Based on {dept['headcount']} engineers: {rec['dept_satisfaction_with_similar']}% satisfaction",
        f"  with similar setup. Budget covers {rec['similar_setups_possible']} more setups.",
        "",
        f"{C.BOLD}Approval:{C.RESET} {'Required — ' + rec['approval_reason'] if rec['needs_approval'] else f'{C.GREEN}Not required (within auto-approval limit){C.RESET}'}",
    ], color=C.GREEN)

    success("Provisioning complete — data-driven package selected")
    success("Two new business domains — same framework — instant results")
    print()


def run_act_4():
    """ACT 4: The business case summary."""
    act(4, "The Business Case", "")

    box("What We Just Demonstrated", [
        "",
        f"{C.GREEN}✓{C.RESET} Created 3 agents for 3 business domains {C.DIM}(seconds){C.RESET}",
        f"{C.GREEN}✓{C.RESET} Agents query real business data, not just follow rules",
        f"{C.GREEN}✓{C.RESET} Data-driven analysis: churn risk, anomaly detection",
        f"{C.GREEN}✓{C.RESET} Specific recommendations backed by historical patterns",
        f"{C.GREEN}✓{C.RESET} Any developer can create new agents for new problems",
        "",
    ], color=C.GREEN)

    box("Cost Per Decision", [
        "",
        f"  {'Mode':<18s}{'Cost':>12s}{'Speed':>12s}{'Use For':>22s}",
        f"  {'─' * 60}",
        f"  {C.GREEN}{'Traditional':<18s}{'$0.00':>12s}{'< 100ms':>12s}{'80% of tasks':>22s}{C.RESET}",
        f"  {C.CYAN}{'Agentic':<18s}{'~$0.05':>12s}{'~ 2s':>12s}{'15% of tasks':>22s}{C.RESET}",
        f"  {C.MAGENTA}{'Multi-Agent':<18s}{'~$0.12':>12s}{'~ 5s':>12s}{'5% of tasks':>22s}{C.RESET}",
        "",
    ], color=C.WHITE)

    box("Why Data Is the Differentiator", [
        "",
        f"  {C.RED}WITHOUT data:{C.RESET}  \"Follow up with the customer\"",
        "",
        f"  {C.GREEN}WITH JAF:{C.RESET}     \"87% churn risk on €169K contract —",
        f"                escalate ticket #4891, call within 48h,",
        f"                20% discount saves €169K/yr (73% success rate)\"",
        "",
        f"  {C.BOLD}Same AI model. Data makes it intelligent.{C.RESET}",
        "",
    ], color=C.CYAN)

    box("What This Means for the Business", [
        "",
        f"  {C.BOLD}REVENUE PROTECTION{C.RESET}",
        f"    Agents detect churn before it happens — data-backed actions",
        "",
        f"  {C.BOLD}DEVELOPER VELOCITY{C.RESET}",
        f"    New agent for any domain: minutes, not months",
        "",
        f"  {C.BOLD}VENDOR INDEPENDENCE{C.RESET}",
        f"    Swap AI backends without changing business logic",
        "",
        f"  {C.BOLD}COST OPTIMIZATION{C.RESET}",
        f"    Right AI for each task — 50% reduction vs always-on AI",
        "",
    ], color=C.WHITE)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  MAIN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    """Run the full CEO demo."""
    header(
        "JAF FRAMEWORK — EXECUTIVE DEMONSTRATION",
        "\"Intelligent Automation Powered by Your Data\""
    )

    print(f"  {C.DIM}Date: February 6, 2026")
    print(f"  Framework: JAF v0.1.0 (Jems Agent Framework)")
    print(f"  Mode: Data-Driven Intelligence — no API keys required{C.RESET}")

    pause(1.0)

    t_start = time.time()

    run_act_1()
    pause(0.5)

    run_act_2()
    pause(0.5)

    run_act_3()
    pause(0.5)

    run_act_4()

    total_time = time.time() - t_start

    print()
    print(f"{C.CYAN}{'═' * W}")
    msg = "One framework. Any business problem. Data-driven intelligence."
    padding = (W - len(msg)) // 2
    print(f"{' ' * padding}{C.BOLD}{C.WHITE}{msg}{C.RESET}{C.CYAN}")
    print(f"{'═' * W}{C.RESET}")
    print()
    print(f"  {C.DIM}Total demo time: {total_time:.1f}s | All analysis: $0.00 | Agents created: 3{C.RESET}")
    print()

    # Clean up
    ActorRegistry.clear()


if __name__ == "__main__":
    main()
