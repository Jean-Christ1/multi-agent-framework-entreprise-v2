"""
JAF CEO Demo — Business Data Module

Realistic mock datasets representing enterprise business data.
These demonstrate how JAF agents use data as a first-class citizen:
- Customer records with behavioral history
- Sales metrics with regional breakdowns
- Employee data with department benchmarks

In production, these would come from databases, APIs, and data warehouses.
"""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CUSTOMER INTELLIGENCE DATA
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CUSTOMERS = {
    "C-1042": {
        "name": "Marie Dupont",
        "company": "TechVision SAS",
        "segment": "Enterprise",
        "industry": "Financial Services",
        "since": "2021-03-15",
        "employees": 2500,
        "annual_contract": 169_000,
        "lifetime_value": 847_000,
        "last_purchase_days_ago": 70,
        "purchase_freq_yearly": [12, 10, 8, 4],  # 4 years, declining
        "nps_history": [9, 9, 8, 6],  # declining
        "support_tickets_90d": 4,
        "avg_tickets_90d": 1.2,
        "open_tickets": [
            {"id": "#4891", "subject": "API latency after v3.2 upgrade", "days_open": 12, "priority": "high"},
            {"id": "#5023", "subject": "Billing discrepancy Q4", "days_open": 3, "priority": "medium"},
        ],
        "competitor_eval": True,
        "health_score": 34,
        "contact": "marie.dupont@techvision.fr",
        "account_manager": "Jean-Pierre Martin",
    },
    "C-2187": {
        "name": "Klaus Weber",
        "company": "DataStream GmbH",
        "segment": "Mid-Market",
        "industry": "Manufacturing",
        "since": "2023-06-01",
        "employees": 450,
        "annual_contract": 48_000,
        "lifetime_value": 96_000,
        "last_purchase_days_ago": 22,
        "purchase_freq_yearly": [6, 9],  # growing
        "nps_history": [7, 8],  # improving
        "support_tickets_90d": 1,
        "avg_tickets_90d": 1.5,
        "open_tickets": [],
        "competitor_eval": False,
        "health_score": 82,
        "contact": "k.weber@datastream.de",
        "account_manager": "Sophie Laurent",
    },
    "C-3301": {
        "name": "Sarah Chen",
        "company": "GlobalTrade Ltd",
        "segment": "Enterprise",
        "industry": "Logistics",
        "since": "2020-01-10",
        "employees": 8200,
        "annual_contract": 312_000,
        "lifetime_value": 1_872_000,
        "last_purchase_days_ago": 8,
        "purchase_freq_yearly": [15, 18, 20, 22, 24],  # growing steadily
        "nps_history": [8, 8, 9, 9, 10],  # improving
        "support_tickets_90d": 2,
        "avg_tickets_90d": 2.1,
        "open_tickets": [],
        "competitor_eval": False,
        "health_score": 95,
        "contact": "s.chen@globaltrade.co.uk",
        "account_manager": "Marc Beaumont",
    },
}

# Benchmarks from analyzing all customer journeys
CUSTOMER_BENCHMARKS = {
    "churn_thresholds": {
        "nps_critical": 7,
        "purchase_decline_pct": 40,
        "ticket_spike_multiplier": 2.5,
        "days_inactive": 60,
    },
    "intervention_success_rates": {
        "high_risk_early": 0.73,   # intervene within 2 weeks
        "high_risk_late": 0.31,    # intervene after 30+ days
        "medium_risk": 0.89,
    },
    "journeys_analyzed": 847,
    "avg_enterprise_ltv": 650_000,
    "avg_midmarket_ltv": 120_000,
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SALES & REVENUE DATA
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MONTHLY_REVENUE = [
    {"month": "2025-07", "revenue": 2_340_000, "deals": 23},
    {"month": "2025-08", "revenue": 2_180_000, "deals": 19},
    {"month": "2025-09", "revenue": 2_520_000, "deals": 26},
    {"month": "2025-10", "revenue": 2_410_000, "deals": 24},
    {"month": "2025-11", "revenue": 2_150_000, "deals": 20},
    {"month": "2025-12", "revenue": 1_870_000, "deals": 15},
    {"month": "2026-01", "revenue": 2_690_000, "deals": 28},
]

REVENUE_BY_REGION = {
    "France":  {"revenue": 8_450_000, "growth_pct": 12, "deals": 82, "pipeline": 2_100_000},
    "DACH":    {"revenue": 4_120_000, "growth_pct": -8, "deals": 41, "pipeline": 1_890_000},
    "Benelux": {"revenue": 2_890_000, "growth_pct": 15, "deals": 29, "pipeline": 980_000},
    "UK":      {"revenue": 1_700_000, "growth_pct": 5,  "deals": 18, "pipeline": 620_000},
}

REVENUE_BY_PRODUCT = {
    "Platform License":       {"revenue": 9_200_000, "pct": 54, "trend": "stable"},
    "Professional Services":  {"revenue": 4_100_000, "pct": 24, "trend": "growing"},
    "Support Plans":          {"revenue": 2_500_000, "pct": 15, "trend": "stable"},
    "Training":               {"revenue": 1_360_000, "pct": 8,  "trend": "declining"},
}

SALES_ANOMALIES = [
    {
        "type": "revenue_dip",
        "region": "DACH",
        "period": "Q4 2025",
        "change_pct": -18,
        "cause": "Pricing restructure in October 2025",
        "detail": "3 enterprise deals (€890K total) pushed to Q1 2026",
        "action": "Recovery expected — monitor Q1 pipeline conversion",
    },
    {
        "type": "deal_size_spike",
        "region": "France",
        "period": "Q4 2025",
        "change_pct": 22,
        "cause": "New enterprise tier launched September 2025",
        "detail": "2 new Fortune 500 clients signed (€420K combined)",
        "action": "Replicate enterprise tier positioning in other regions",
    },
]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  EMPLOYEE & DEPARTMENT DATA
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EMPLOYEES = {
    "E-5531": {
        "name": "Thomas Bernard",
        "role": "Senior Developer",
        "department": "Engineering",
        "hire_date": "2026-02-10",
        "location": "Paris",
        "contract_type": "CDI",
        "manager": "Claire Dubois",
    },
    "E-5532": {
        "name": "Anna Kowalski",
        "role": "Data Scientist",
        "department": "AI Research",
        "hire_date": "2026-02-15",
        "location": "Lyon",
        "contract_type": "CDI",
        "manager": "Pierre Moreau",
    },
    "E-5533": {
        "name": "Luca Rossi",
        "role": "Account Executive",
        "department": "Sales",
        "hire_date": "2026-02-20",
        "location": "Paris",
        "contract_type": "CDI",
        "manager": "Nathalie Girard",
    },
}

DEPARTMENT_STATS = {
    "Engineering": {
        "headcount": 128,
        "avg_equipment_cost": 2_200,
        "most_common_setup": "MacBook Pro 16\" + External Monitor 27\"",
        "satisfaction_pct": 91,
        "budget_total": 280_000,
        "budget_remaining": 45_000,
        "top_items": ["MacBook Pro 16\"", "Dell 27\" 4K Monitor", "Ergonomic Chair"],
    },
    "AI Research": {
        "headcount": 24,
        "avg_equipment_cost": 3_100,
        "most_common_setup": "GPU Workstation + Dual 4K Monitors",
        "satisfaction_pct": 87,
        "budget_total": 75_000,
        "budget_remaining": 18_000,
        "top_items": ["GPU Workstation", "32GB+ RAM Upgrade", "Dual 4K Monitors"],
    },
    "Sales": {
        "headcount": 85,
        "avg_equipment_cost": 1_400,
        "most_common_setup": "Lightweight Laptop + Corporate Phone",
        "satisfaction_pct": 94,
        "budget_total": 120_000,
        "budget_remaining": 32_000,
        "top_items": ["MacBook Air 14\"", "iPhone 15 Pro", "Jabra Headset"],
    },
}

EQUIPMENT_CATALOG = {
    "senior_developer": {
        "package_name": "Pro Developer Setup",
        "items": [
            {"name": "MacBook Pro 16\" M3 Pro", "price": 2_899},
            {"name": "Dell 27\" 4K Monitor", "price": 549},
            {"name": "Ergonomic Keyboard + Mouse", "price": 189},
            {"name": "Noise-Canceling Headset", "price": 299},
        ],
        "total": 3_936,
    },
    "data_scientist": {
        "package_name": "AI Research Station",
        "items": [
            {"name": "GPU Workstation (RTX 4090)", "price": 4_299},
            {"name": "Dual 27\" 4K Monitors", "price": 1_098},
            {"name": "Ergonomic Standing Desk", "price": 699},
            {"name": "Noise-Canceling Headset", "price": 299},
        ],
        "total": 6_395,
    },
    "account_executive": {
        "package_name": "Mobile Sales Kit",
        "items": [
            {"name": "MacBook Air 14\" M3", "price": 1_299},
            {"name": "iPhone 15 Pro", "price": 1_199},
            {"name": "Jabra Evolve2 Headset", "price": 249},
            {"name": "Laptop Bag (Premium)", "price": 129},
        ],
        "total": 2_876,
    },
}
