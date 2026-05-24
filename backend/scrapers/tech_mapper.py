"""Keyword-to-technology/industry mapping engine.

Automatically classifies any text (funding news headline, company description)
into the system's 4 technology domains and 6 industry verticals.
"""

import re
from typing import Optional

# Technology mappings — ordered by specificity (more specific first)
TECH_MAP: list[tuple[list[str], str, str]] = [
    # (keywords, technology_id, technology_name)
    # --- Embodied AI ---
    (["humanoid robot", "humanoid", "embodied intelligence", "embodied ai",
      "具身智能", "人形机器人", "telerobot", "dexterous manipulation",
      "robot hand", "robot arm", "locomotion", "grasping", "manipulation",
      "world model", "robot foundation model", "autonomous driving"],
     "embodied-ai", "具身智能"),
    # --- BCI ---
    (["brain-computer", "brain computer", "neural interface", "neuralink",
      "bci", "neuroprosthetic", "neural implant", "eeg", "neural signal",
      "brain implant", "neural decoding", "脑机接口", "神经接口",
      "brain-machine", "brain machine", "neurotechnology", "neurotech"],
     "bci", "脑机接口"),
    # --- Quantum Computing ---
    (["quantum computing", "quantum computer", "qubit", "quantum processor",
      "quantum algorithm", "quantum error correction", "superconducting qubit",
      "ion trap", "quantum annealing", "quantum cryptography", "quantum network",
      "量子计算", "量子", "qiskit", "cirq", "quantum advantage",
      "quantum supremacy", "topological qubit", "photonics quantum"],
     "quantum", "量子计算"),
    # --- Nuclear Fusion ---
    (["nuclear fusion", "fusion energy", "tokamak", "stellarator",
      "inertial confinement", "deuterium", "tritium", "plasma physics",
      "fusion reactor", "fusion power", "magnetic confinement",
      "deep fission", "nuclear startup", "advanced nuclear",
      "laser fusion", "核聚变", "聚变能源", "托卡马克",
      "iter", "nif", "helion", "commonwealth fusion", "trialpha",
      "general fusion", "zap energy", "fuse energy"],
     "fusion", "核聚变"),
]

# Industry mappings
INDUSTRY_MAP: list[tuple[list[str], str, str]] = [
    # --- Humanoid Robot ---
    (["humanoid robot", "cobot", "robot arm", "industrial robot",
      "servo motor", "harmonic drive", "robot sensor", "robot controller",
      "robot operating system", "ros", "actuator", "robot hand",
      "locomotion", "gripper", "end effector", "robot fleet"],
     "humanoid-robot", "人形机器人"),
    # --- Compute Grid ---
    (["gpu", "h100", "a100", "b100", "b200", "nvidia", "tpu",
      "ai chip", "chipmaker", "brain chip", "大脑芯片",
      "data center", "datacenter", "server farm",
      "cloud computing", "hpc", "supercomputer", "inference chip",
      "training chip", "npu", "ai accelerator", "scheduler",
      "算力", "数据中心", "gpu集群", "gpu cluster",
      "edge computing", "edge ai", "llm inference"],
     "compute-grid", "算力网"),
    # --- Bio Medicine ---
    (["gene therapy", "gene editing", "crispr", "mrna", "cell therapy",
      "immunotherapy", "biotech", "biopharma", "drug discovery",
      "ai drug", "protein folding", "precision medicine",
      "clinical trial", "fda approval", "car-t", "gene sequencing",
      "基因组", "蛋白", "生物医药", "基因治疗", "细胞治疗"],
     "bio-medicine", "生物医药"),
    # --- Neural Prosthetics ---
    (["neural prosthes", "cochlear implant", "retinal implant",
      "deep brain stimulation", "dbs", "brain implant",
      "neural stimul", "vagus nerve", "spinal cord stimul",
      "bionic eye", "bionic limb", "neural decoder",
      "脑起搏", "神经调控", "神经假肢", "人工耳蜗"],
     "neural-prosthetics", "神经假肢/BCI医疗"),
    # --- Quantum Computing Industry ---
    (["quantum chip", "quantum hardware", "quantum sensor",
      "dilution refrigerator", "cryogenic", "quantum cloud",
      "quantum software", "quantum annealing", "quantum advantage",
      "量子芯片", "量子传感器", "量子云平台"],
     "quantum-computing-industry", "量子计算产业链"),
    # --- Fusion Energy ---
    (["fusion energy", "fusion power plant", "tritium breeding",
      "first wall", "divertor", "superconducting magnet",
      "plasma heating", "neutral beam", "inertial fusion",
      "fusion startup", "fusion investment",
      "聚变发电", "聚变装置", "聚变工程"],
     "fusion-energy", "聚变能源产业链"),
]


def map_to_technologies(text: str) -> list[str]:
    """Return list of technology IDs matching the text."""
    text_lower = text.lower()
    matched = set()
    for keywords, tech_id, _ in TECH_MAP:
        for kw in keywords:
            if kw in text_lower:
                matched.add(tech_id)
                break
    return sorted(matched)


def map_to_industries(text: str) -> list[str]:
    """Return list of industry IDs matching the text."""
    text_lower = text.lower()
    matched = set()
    for keywords, ind_id, _ in INDUSTRY_MAP:
        for kw in keywords:
            if kw in text_lower:
                matched.add(ind_id)
                break
    return sorted(matched)


def map_all(text: str) -> tuple[list[str], list[str]]:
    """Map text to both technology and industry IDs."""
    return map_to_technologies(text), map_to_industries(text)


def extract_amount_usd(text: str) -> Optional[float]:
    """Extract USD amount from text like '$50M', '$1.2B', '$500K'."""
    patterns = [
        r'\$(\d+(?:\.\d+)?)\s*(?:million|m\b|M\b)',
        r'\$(\d+(?:\.\d+)?)\s*(?:billion|bn?|B\b)',
        r'\$(\d+(?:\.\d+)?)\s*(?:thousand|k\b|K\b)',
        r'\$(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:million|m\b|M\b)',
        r'\$(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:billion|bn?|B\b)',
    ]
    text_clean = text.replace(",", "")
    for i, pat in enumerate(patterns):
        m = re.search(pat, text)
        if m:
            val = float(m.group(1).replace(",", ""))
            if i in (1, 4):  # billion
                return val * 1_000_000_000
            elif i in (0, 3):  # million
                return val * 1_000_000
            elif i in (2,):  # thousand
                return val * 1_000
            else:
                return val
    # Try bare $ number
    m = re.search(r'\$(\d+(?:,\d{3})*(?:\.\d+)?)\s*(K|M|B|thousand|million|billion)?', text)
    if m:
        val = float(m.group(1).replace(",", ""))
        unit = (m.group(2) or "").lower()
        if unit in ("b", "billion"):
            return val * 1_000_000_000
        elif unit in ("m", "million"):
            return val * 1_000_000
        elif unit in ("k", "thousand"):
            return val * 1_000
        return val
    return None


def extract_round_stage(text: str) -> Optional[str]:
    """Extract funding round stage from text."""
    text_lower = text.lower()
    stages = [
        ("pre-seed", ["pre-seed", "pre seed", "preseed"]),
        ("seed", ["seed round", "seed funding", "seed stage", "raised seed"]),
        ("series-a", ["series a", "series-a", "seriesa", "$a round"]),
        ("series-b", ["series b", "series-b", "seriesb", "$b round"]),
        ("series-c", ["series c", "series-c", "seriesc", "$c round"]),
        ("series-d", ["series d", "series-d", "seriesd"]),
        ("growth", ["growth round", "growth equity"]),
        ("ipo", ["ipo", "initial public offering", "went public", "listing"]),
        ("acquisition", ["acquisition", "acquired", "acq-hire"]),
    ]
    for stage, keywords in stages:
        for kw in keywords:
            if kw in text_lower:
                return stage
    return None
