"""
Curated investment theme models.
"""

from typing import Dict, List

from app.services.research_models import EvidenceCard, ThemeExposure


class AIInfrastructureThemeModel:
    """AI infrastructure and inference theme exposure model."""

    theme_slug = "ai-infrastructure"
    name = "AI Infrastructure and Inference"

    bottlenecks = [
        "HBM memory supply",
        "advanced packaging capacity",
        "datacenter power availability",
        "liquid cooling and thermal constraints",
        "export controls and geopolitical concentration",
    ]

    risks = [
        "valuation compression if AI capex expectations cool",
        "hyperscaler capex digestion cycles",
        "customer concentration",
        "export controls and tariff changes",
        "supply-chain bottlenecks delaying revenue conversion",
    ]

    layers = {
        "gpu-accelerator": {
            "description": "Accelerators used for AI training and inference.",
            "symbols": ["NVDA", "AMD", "AVGO", "MRVL"],
            "drivers": ["AI training demand", "inference acceleration", "accelerator attach rates"],
        },
        "foundry-manufacturing": {
            "description": "Semiconductor manufacturing capacity and process leadership.",
            "symbols": ["TSM", "INTC", "GFS"],
            "drivers": ["advanced-node demand", "chip supply resilience", "regional subsidies"],
        },
        "equipment-process-control": {
            "description": "Tools required to manufacture advanced semiconductors.",
            "symbols": ["ASML", "AMAT", "LRCX", "KLAC"],
            "drivers": ["EUV demand", "capacity expansion", "process control complexity"],
        },
        "eda-ip": {
            "description": "Design automation and semiconductor IP used before manufacturing.",
            "symbols": ["SNPS", "CDNS", "ARM"],
            "drivers": ["chip design starts", "custom silicon", "IP licensing"],
        },
        "memory-storage": {
            "description": "HBM, DRAM, storage, and memory subsystems for AI workloads.",
            "symbols": ["MU", "WDC", "STX"],
            "drivers": ["HBM demand", "AI server memory intensity", "storage growth"],
        },
        "networking": {
            "description": "High-speed networking for AI clusters and datacenters.",
            "symbols": ["ANET", "AVGO", "MRVL", "CSCO"],
            "drivers": ["cluster scale-out", "ethernet AI fabrics", "optical networking"],
        },
        "servers-integration": {
            "description": "AI server assembly, integration, and enterprise infrastructure.",
            "symbols": ["SMCI", "DELL", "HPE"],
            "drivers": ["AI server demand", "rack-scale deployments", "enterprise refresh"],
        },
        "datacenter-power-cooling": {
            "description": "Electrical, power, thermal, and construction support for AI datacenters.",
            "symbols": ["VRT", "ETN", "PWR", "GNRC"],
            "drivers": ["power density", "liquid cooling", "grid interconnect demand"],
        },
        "datacenter-real-estate": {
            "description": "Datacenter facilities and colocation infrastructure.",
            "symbols": ["EQIX", "DLR"],
            "drivers": ["datacenter capacity", "cloud colocation", "interconnect demand"],
        },
        "cloud-ai-platforms": {
            "description": "Cloud platforms funding and monetizing training and inference workloads.",
            "symbols": ["MSFT", "AMZN", "GOOGL", "ORCL", "META"],
            "drivers": ["hyperscaler capex", "AI platform services", "inference consumption"],
        },
        "agentic-inference-software": {
            "description": "Software and data platforms that can monetize model inference and agentic workflows.",
            "symbols": ["NOW", "CRM", "PLTR", "SNOW", "DDOG", "NET", "MDB"],
            "drivers": ["enterprise AI adoption", "agent workflows", "observability and data infrastructure"],
        },
    }

    company_names = {
        "NVDA": "NVIDIA Corporation",
        "AMD": "Advanced Micro Devices, Inc.",
        "AVGO": "Broadcom Inc.",
        "MRVL": "Marvell Technology, Inc.",
        "TSM": "Taiwan Semiconductor Manufacturing Company Limited",
        "INTC": "Intel Corporation",
        "GFS": "GlobalFoundries Inc.",
        "ASML": "ASML Holding N.V.",
        "AMAT": "Applied Materials, Inc.",
        "LRCX": "Lam Research Corporation",
        "KLAC": "KLA Corporation",
        "SNPS": "Synopsys, Inc.",
        "CDNS": "Cadence Design Systems, Inc.",
        "ARM": "Arm Holdings plc",
        "MU": "Micron Technology, Inc.",
        "WDC": "Western Digital Corporation",
        "STX": "Seagate Technology Holdings plc",
        "ANET": "Arista Networks, Inc.",
        "CSCO": "Cisco Systems, Inc.",
        "SMCI": "Super Micro Computer, Inc.",
        "DELL": "Dell Technologies Inc.",
        "HPE": "Hewlett Packard Enterprise Company",
        "VRT": "Vertiv Holdings Co",
        "ETN": "Eaton Corporation plc",
        "PWR": "Quanta Services, Inc.",
        "GNRC": "Generac Holdings Inc.",
        "EQIX": "Equinix, Inc.",
        "DLR": "Digital Realty Trust, Inc.",
        "MSFT": "Microsoft Corporation",
        "AMZN": "Amazon.com, Inc.",
        "GOOGL": "Alphabet Inc.",
        "ORCL": "Oracle Corporation",
        "META": "Meta Platforms, Inc.",
        "NOW": "ServiceNow, Inc.",
        "CRM": "Salesforce, Inc.",
        "PLTR": "Palantir Technologies Inc.",
        "SNOW": "Snowflake Inc.",
        "DDOG": "Datadog, Inc.",
        "NET": "Cloudflare, Inc.",
        "MDB": "MongoDB, Inc.",
    }

    def get_exposures(self, symbol: str) -> List[ThemeExposure]:
        symbol = symbol.upper()
        exposures: List[ThemeExposure] = []
        for layer, data in self.layers.items():
            if symbol not in data["symbols"]:
                continue
            exposures.append(
                ThemeExposure(
                    theme_slug=self.theme_slug,
                    symbol=symbol,
                    company_name=self.company_names.get(symbol, f"{symbol} Corporation"),
                    layer=layer,
                    score=self._score(symbol, layer),
                    drivers=data["drivers"],
                    bottlenecks=self._bottlenecks_for_layer(layer),
                )
            )
        return exposures

    def get_theme_map(self) -> dict:
        exposures = []
        for layer, data in self.layers.items():
            for symbol in data["symbols"]:
                exposures.extend(self.get_exposures(symbol))

        return {
            "themeSlug": self.theme_slug,
            "name": self.name,
            "layers": [
                {
                    "layer": layer,
                    "description": data["description"],
                    "symbols": data["symbols"],
                    "drivers": data["drivers"],
                }
                for layer, data in self.layers.items()
            ],
            "exposures": [item.to_api() for item in exposures],
            "bottlenecks": self.bottlenecks,
            "risks": self.risks,
            "sourceNotes": [
                "Curated MVP theme model for local research.",
                "Future versions should derive exposure from filings, earnings calls, news, and supply-chain datasets.",
            ],
        }

    def evidence_for(self, exposure: ThemeExposure) -> EvidenceCard:
        return EvidenceCard(
            title=f"AI infrastructure exposure: {exposure.layer}",
            summary=(
                f"{exposure.symbol} is mapped to {exposure.layer} with drivers: "
                + ", ".join(exposure.drivers[:3])
            ),
            source="curated-theme-model",
            source_id="curated-ai-infrastructure-theme",
            source_type="curated",
            symbols=[exposure.symbol],
            themes=[self.theme_slug],
            sentiment="positive" if exposure.score >= 0.6 else "neutral",
            confidence=max(0.5, min(0.95, exposure.score)),
        )

    def _score(self, symbol: str, layer: str) -> float:
        primary_scores: Dict[str, float] = {
            "NVDA": 1.0,
            "TSM": 0.95,
            "ASML": 0.9,
            "AVGO": 0.86,
            "ANET": 0.84,
            "VRT": 0.82,
            "MSFT": 0.78,
            "AMZN": 0.75,
            "GOOGL": 0.74,
            "META": 0.72,
        }
        if symbol in primary_scores:
            return primary_scores[symbol]
        if layer in {"gpu-accelerator", "datacenter-power-cooling", "networking"}:
            return 0.74
        if layer in {"agentic-inference-software", "servers-integration"}:
            return 0.66
        return 0.62

    def _bottlenecks_for_layer(self, layer: str) -> List[str]:
        mapping = {
            "gpu-accelerator": ["HBM supply", "advanced packaging capacity", "export controls"],
            "foundry-manufacturing": ["Taiwan concentration", "advanced-node capacity", "geopolitical risk"],
            "equipment-process-control": ["fab capex cyclicality", "export controls", "long lead times"],
            "memory-storage": ["HBM yield", "memory cycle volatility", "customer concentration"],
            "networking": ["cluster architecture shifts", "optical component supply", "hyperscaler capex timing"],
            "datacenter-power-cooling": ["grid interconnect delays", "power equipment lead times", "cooling density"],
            "agentic-inference-software": ["AI monetization proof", "valuation risk", "platform competition"],
        }
        return mapping.get(layer, self.bottlenecks[:3])
