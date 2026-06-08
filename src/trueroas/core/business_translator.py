#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.
#  Proprietary and confidential.

#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.
#  Proprietary and confidential.

from typing import Dict, Any


def translate_to_business_action(
    posterior_roas: float,
    p10_roas: float,
    break_even_roas: float,
    attribution_variance: float,
    meta_roas: float,
    daily_spend: float,
) -> Dict[str, Any]:
    """
    Translates complex Bayesian metrics into actionable CFO-level business logic.
    """
    # 1. Determine Health Status
    if posterior_roas < break_even_roas * 0.9:
        status = "BLEEDING"
    elif attribution_variance > 0.35 or p10_roas < break_even_roas:
        status = "WARNING"
    else:
        status = "HEALTHY"

    # 2. Capital Health Narrative
    health_map = {
        "HEALTHY": "Your ad spend is generating positive ROI",
        "WARNING": "Attribution lag detected, true ROAS is eroding",
        "BLEEDING": "Platform is overstating ROAS, you are losing money on every order",
    }
    capital_health = health_map.get(status)

    # 3. Action Logic
    if status == "BLEEDING":
        action = "PAUSE_CAMPAIGN"
    elif status == "WARNING":
        action = "REDUCE_SPEND"
    elif posterior_roas > break_even_roas * 1.4:
        action = "STRONG_SCALE"
    else:
        action = "HOLD"

    # 4. Capital Bleed Calculation (Daily exposure)
    capital_bleed_usd = daily_spend * max(
        0, (meta_roas - posterior_roas) / max(meta_roas, 0.1)
    )

    # 5. CFO Brief Construction
    cfo_brief = (
        f"Marketing Audit: Your platform is reporting a {meta_roas:.1f}x return, but bank-truth reconciliation "
        f"confirms only {posterior_roas:.1f}x. {'URGENT: Scale back spend to protect your P&L.' if status == 'BLEEDING' else 'System confirms your spend is efficient.'}"
    )

    return {
        "status": status,
        "capital_health": capital_health,
        "capital_bleed_usd": float(round(capital_bleed_usd, 2)),
        "action_required": action,
        "cfo_brief": cfo_brief,
    }
