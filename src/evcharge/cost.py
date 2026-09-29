"""Site build-cost scenarios and indicative site economics. Every constant cites its source.

Sources (see docs/DATA_SOURCES.md):
- NREL: Borlaug et al. (2026), "Economics of electric vehicle corridor fast charging in the
  United States", Advances in Applied Energy 21. Per-port EVSE + installation at 350 kW:
  $141,900 equipment + $90,800 installation = $232,700; distribution transformer $100,000 when
  site peak exceeds 200 kW; feeder upgrade $3,000,000 above 3 MW peak. 2025 capacity factor 4%,
  176 kWh per port per day. Stations with demand charges: $0.43/kWh levelized vs $0.31/kWh without.
- Paren (Oct 31, 2024), analysis of 330 NEVI award applications: median project $802,267,
  top quartile $1,053,624, median $183,116 per port, mean $192,614 per port.
- AFDC station file: IONNA sites average 8.46 DC ports (180 open sites, snapshot 2026-09-22).
"""

from __future__ import annotations

from dataclasses import dataclass

NREL_PORT_350KW = 141_900 + 90_800
NREL_TRANSFORMER = 100_000
PAREN_MEDIAN_PER_PORT = 183_116
PAREN_TOP_QUARTILE_RATIO = 1_053_624 / 802_267  # top-quartile / median project cost = 1.313
NREL_KWH_PER_PORT_DAY_2025 = 176
NREL_DEMAND_CHARGE_ADDER = 0.43 - 0.31  # $/kWh gap between stations with and without demand charges
DEFAULT_PORTS = 8


@dataclass(frozen=True)
class CostScenario:
    name: str
    per_port: float
    site_fixed: float
    note: str


SCENARIOS = {
    "Low": CostScenario("Low", PAREN_MEDIAN_PER_PORT, 0.0,
                        "Median NEVI award cost per port (Paren, 330 awards); all-in project cost."),
    "Base": CostScenario("Base", NREL_PORT_350KW, NREL_TRANSFORMER,
                         "NREL 350 kW per-port equipment + installation, plus one transformer."),
    "High": CostScenario("High", NREL_PORT_350KW * PAREN_TOP_QUARTILE_RATIO,
                         NREL_TRANSFORMER * PAREN_TOP_QUARTILE_RATIO,
                         "Base scaled by NEVI top-quartile / median cost ratio (1.31)."),
}


def site_cost(scenario: str = "Base", ports: int = DEFAULT_PORTS, per_port: float | None = None,
              regional_multiplier: float = 1.0, incentive_share: float = 0.0) -> float:
    """Net capital cost for one site after an optional grant share (0-1)."""
    if ports <= 0:
        raise ValueError("ports must be positive")
    if not 0 <= incentive_share < 1:
        raise ValueError("incentive_share must be in [0, 1)")
    s = SCENARIOS[scenario]
    pp = s.per_port if per_port is None else per_port
    gross = (pp * ports + s.site_fixed) * regional_multiplier
    return gross * (1 - incentive_share)


def annual_economics(ports: int, kwh_per_port_day: float, price_per_kwh: float,
                     elec_c_per_kwh: float, demand_adder: float = NREL_DEMAND_CHARGE_ADDER) -> dict:
    """Indicative annual energy revenue and energy cost for one site (excludes O&M, rent, fees)."""
    kwh = ports * kwh_per_port_day * 365
    revenue = kwh * price_per_kwh
    energy_cost = kwh * (elec_c_per_kwh / 100 + demand_adder)
    return {"kwh": kwh, "revenue": revenue, "energy_cost": energy_cost,
            "gross_margin": revenue - energy_cost}
