"""
JAF Demo Actors — Data-Driven Business Intelligence
====================================================

Three actors that demonstrate real AI reasoning with business data.
Each actor has @Tool-decorated methods that provide data access.
The NativeAdapter (OpenAI function calling) decides which tools to call.

Usage:
    from jaf.demos.actors import create_customer_agent, create_sales_agent, create_provisioning_agent
    agents = [create_customer_agent(), create_sales_agent(), create_provisioning_agent()]
"""

from jaf.core.actor import Actor, Tool, actor
from jaf.core.models import LLMConfig

from jaf.demos.data import (
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


# ── Customer Intelligence Agent ─────────────────────────────

@actor(
    name="CustomerIntelligenceAgent",
    description="Analyzes customer data to detect churn risk and recommend retention actions",
    goal="Identify at-risk customers and provide actionable retention strategies",
    llm_config=LLMConfig(model="gpt-5-nano", temperature=0.8),
)
class CustomerIntelligenceAgent(Actor):

    @Tool(description="Look up a customer by ID. Returns full customer profile including contract, NPS history, support tickets, and health score.")
    def lookup_customer(self, customer_id: str) -> dict:
        customer = CUSTOMERS.get(customer_id)
        if not customer:
            available = list(CUSTOMERS.keys())
            return {"error": f"Customer {customer_id} not found. Available: {available}"}
        return {"customer_id": customer_id, **customer}

    @Tool(description="Analyze customer health using benchmark data. Returns churn risk assessment based on NPS trends, purchase frequency, ticket volume, and competitor evaluation signals.")
    def analyze_health(self, customer_id: str) -> dict:
        customer = CUSTOMERS.get(customer_id)
        if not customer:
            return {"error": f"Customer {customer_id} not found"}

        thresholds = CUSTOMER_BENCHMARKS["churn_thresholds"]
        risks = []

        # NPS decline check
        nps = customer.get("nps_history", [])
        if nps and nps[-1] < thresholds["nps_critical"]:
            risks.append(f"NPS dropped to {nps[-1]} (critical threshold: {thresholds['nps_critical']})")

        # Purchase frequency decline
        freq = customer.get("purchase_freq_yearly", [])
        if len(freq) >= 2:
            decline = ((freq[-2] - freq[-1]) / freq[-2]) * 100 if freq[-2] > 0 else 0
            if decline > thresholds["purchase_decline_pct"]:
                risks.append(f"Purchase frequency declined {decline:.0f}% YoY (threshold: {thresholds['purchase_decline_pct']}%)")

        # Support ticket spike
        tickets = customer.get("support_tickets_90d", 0)
        avg = customer.get("avg_tickets_90d", 1)
        if avg > 0 and tickets / avg > thresholds["ticket_spike_multiplier"]:
            risks.append(f"Support tickets {tickets}x above average ({tickets} vs avg {avg})")

        # Inactivity
        days_inactive = customer.get("last_purchase_days_ago", 0)
        if days_inactive > thresholds["days_inactive"]:
            risks.append(f"Inactive for {days_inactive} days (threshold: {thresholds['days_inactive']})")

        # Competitor evaluation
        if customer.get("competitor_eval"):
            risks.append("Currently evaluating competitor solutions")

        risk_level = "critical" if len(risks) >= 3 else "high" if len(risks) >= 2 else "medium" if risks else "low"

        return {
            "customer_id": customer_id,
            "health_score": customer.get("health_score", 0),
            "risk_level": risk_level,
            "risk_factors": risks,
            "benchmarks_used": CUSTOMER_BENCHMARKS,
            "intervention_success_rate": CUSTOMER_BENCHMARKS["intervention_success_rates"].get(
                f"{risk_level}_early", 0.5
            ),
        }

    @Tool(description="Get recommended retention actions for a customer based on their risk profile and contract value.")
    def recommend_actions(self, customer_id: str, risk_level: str) -> dict:
        customer = CUSTOMERS.get(customer_id)
        if not customer:
            return {"error": f"Customer {customer_id} not found"}

        actions = []
        contract_value = customer.get("annual_contract", 0)

        if risk_level in ("critical", "high"):
            actions.extend([
                {"action": "Schedule executive sponsor call within 48 hours", "priority": "urgent", "owner": "VP Sales"},
                {"action": f"Resolve open tickets: {[t['id'] for t in customer.get('open_tickets', [])]}", "priority": "urgent", "owner": "Support Lead"},
                {"action": f"Prepare retention offer (up to {int(contract_value * 0.15):,} EUR discount)", "priority": "high", "owner": "Account Manager"},
            ])
        if customer.get("competitor_eval"):
            actions.append({"action": "Competitive displacement analysis + feature comparison deck", "priority": "high", "owner": "Product Marketing"})
        if risk_level == "medium":
            actions.extend([
                {"action": "Quarterly business review meeting", "priority": "medium", "owner": "Account Manager"},
                {"action": "Share product roadmap preview", "priority": "medium", "owner": "Product Manager"},
            ])

        return {
            "customer_id": customer_id,
            "customer_name": customer.get("name"),
            "contract_at_risk": f"{contract_value:,} EUR",
            "lifetime_value": f"{customer.get('lifetime_value', 0):,} EUR",
            "recommended_actions": actions,
            "account_manager": customer.get("account_manager"),
        }


# ── Sales Analytics Agent ────────────────────────────────────

@actor(
    name="SalesAnalyticsAgent",
    description="Analyzes sales and revenue data to detect trends, anomalies, and growth opportunities",
    goal="Provide data-driven sales insights with regional and product breakdowns",
    llm_config=LLMConfig(model="gpt-5-nano", temperature=0.8),
)
class SalesAnalyticsAgent(Actor):

    @Tool(description="Get revenue summary with monthly trends, totals, and growth rate. Returns last 7 months of revenue data.")
    def revenue_summary(self) -> dict:
        total = sum(m["revenue"] for m in MONTHLY_REVENUE)
        total_deals = sum(m["deals"] for m in MONTHLY_REVENUE)
        avg_deal = total / total_deals if total_deals else 0

        # Growth calculation
        if len(MONTHLY_REVENUE) >= 2:
            recent = MONTHLY_REVENUE[-1]["revenue"]
            previous = MONTHLY_REVENUE[-2]["revenue"]
            mom_growth = ((recent - previous) / previous) * 100 if previous else 0
        else:
            mom_growth = 0

        return {
            "monthly_data": MONTHLY_REVENUE,
            "total_revenue": total,
            "total_deals": total_deals,
            "avg_deal_size": round(avg_deal),
            "mom_growth_pct": round(mom_growth, 1),
            "period": f"{MONTHLY_REVENUE[0]['month']} to {MONTHLY_REVENUE[-1]['month']}",
        }

    @Tool(description="Detect anomalies in sales data. Returns identified anomalies with causes, impact, and recommended actions.")
    def detect_anomalies(self) -> dict:
        return {
            "anomalies_found": len(SALES_ANOMALIES),
            "anomalies": SALES_ANOMALIES,
            "regional_breakdown": REVENUE_BY_REGION,
        }

    @Tool(description="Analyze a specific region's performance. Provide the region name (France, DACH, Benelux, UK).")
    def analyze_region(self, region: str) -> dict:
        data = REVENUE_BY_REGION.get(region)
        if not data:
            return {"error": f"Region '{region}' not found. Available: {list(REVENUE_BY_REGION.keys())}"}

        # Find anomalies for this region
        region_anomalies = [a for a in SALES_ANOMALIES if a.get("region") == region]

        return {
            "region": region,
            "revenue": data["revenue"],
            "growth_pct": data["growth_pct"],
            "deals": data["deals"],
            "pipeline": data["pipeline"],
            "anomalies": region_anomalies,
            "product_breakdown": REVENUE_BY_PRODUCT,
        }


# ── Smart Provisioning Agent ────────────────────────────────

@actor(
    name="SmartProvisioningAgent",
    description="Provisions equipment for new employees based on role, department, and budget data",
    goal="Recommend optimal equipment packages for new hires within department budget",
    llm_config=LLMConfig(model="gpt-5-nano", temperature=0.8),
)
class SmartProvisioningAgent(Actor):

    @Tool(description="Get full context for an employee including their role, department stats, and budget availability.")
    def get_employee_context(self, employee_id: str) -> dict:
        employee = EMPLOYEES.get(employee_id)
        if not employee:
            return {"error": f"Employee {employee_id} not found. Available: {list(EMPLOYEES.keys())}"}

        dept = employee.get("department", "")
        dept_stats = DEPARTMENT_STATS.get(dept, {})

        return {
            "employee": {"id": employee_id, **employee},
            "department_stats": dept_stats,
            "budget_available": dept_stats.get("budget_remaining", 0),
            "avg_cost": dept_stats.get("avg_equipment_cost", 0),
            "common_setup": dept_stats.get("most_common_setup", "N/A"),
        }

    @Tool(description="Get recommended equipment package for an employee based on their role. Maps role to catalog package.")
    def recommend_equipment(self, employee_id: str) -> dict:
        employee = EMPLOYEES.get(employee_id)
        if not employee:
            return {"error": f"Employee {employee_id} not found"}

        role = employee.get("role", "").lower().replace(" ", "_")
        dept = employee.get("department", "")
        dept_stats = DEPARTMENT_STATS.get(dept, {})

        # Map role to equipment catalog
        package = EQUIPMENT_CATALOG.get(role)
        if not package:
            # Fallback: find closest match
            for key, pkg in EQUIPMENT_CATALOG.items():
                if any(word in role for word in key.split("_")):
                    package = pkg
                    break

        if not package:
            return {"error": f"No equipment package found for role: {employee.get('role')}"}

        budget_remaining = dept_stats.get("budget_remaining", 0)
        within_budget = package["total"] <= budget_remaining

        return {
            "employee_id": employee_id,
            "employee_name": employee.get("name"),
            "role": employee.get("role"),
            "department": dept,
            "package": package,
            "total_cost": package["total"],
            "budget_remaining": budget_remaining,
            "within_budget": within_budget,
            "budget_after_purchase": budget_remaining - package["total"] if within_budget else None,
        }


# ── Factory functions ────────────────────────────────────────

def create_customer_agent() -> CustomerIntelligenceAgent:
    """Create a fresh CustomerIntelligenceAgent instance."""
    return CustomerIntelligenceAgent()


def create_sales_agent() -> SalesAnalyticsAgent:
    """Create a fresh SalesAnalyticsAgent instance."""
    return SalesAnalyticsAgent()


def create_provisioning_agent() -> SmartProvisioningAgent:
    """Create a fresh SmartProvisioningAgent instance."""
    return SmartProvisioningAgent()
