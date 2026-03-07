"""Skill dictionary builder (SPEC.md §3.2).

Builds combined skill dictionary from ESCO CSV + UK-specific entries + Phase 1 dict.
Output: dict[str, str] mapping lowercase pattern → canonical name.
"""

from src.skills.dictionary import SKILLS_DICT
from src.skills.esco_loader import load_esco_csv


def build_uk_entries() -> dict[str, str]:
    """Build UK-specific skill entries (~300 additions not in ESCO).

    Returns:
        Dict mapping lowercase pattern → canonical name.
    """
    entries: dict[str, str] = {}

    # Education
    for label, canonical in [
        ("gcse", "GCSE"), ("a-level", "A-Level"), ("a level", "A-Level"),
        ("btec", "BTEC"), ("nvq", "NVQ"), ("nvq level 1", "NVQ Level 1"),
        ("nvq level 2", "NVQ Level 2"), ("nvq level 3", "NVQ Level 3"),
        ("nvq level 4", "NVQ Level 4"), ("nvq level 5", "NVQ Level 5"),
        ("nvq level 6", "NVQ Level 6"), ("nvq level 7", "NVQ Level 7"),
        ("city & guilds", "City & Guilds"), ("city and guilds", "City & Guilds"),
        ("hnc", "HNC"), ("hnd", "HND"), ("qts", "QTS"), ("pgce", "PGCE"),
        ("foundation degree", "Foundation Degree"),
    ]:
        entries[label] = canonical

    # Construction
    for label, canonical in [
        ("cscs", "CSCS Card"), ("cscs card", "CSCS Card"),
        ("smsts", "SMSTS"), ("sssts", "SSSTS"),
        ("cpcs", "CPCS"), ("ipaf", "IPAF"), ("pasma", "PASMA"),
        ("gas safe", "Gas Safe"), ("gas safe registered", "Gas Safe"),
        ("part p", "Part P"), ("jib card", "JIB Card"), ("ecs card", "ECS Card"),
    ]:
        entries[label] = canonical

    # Security
    for label, canonical in [
        ("sia licence", "SIA Licence"), ("sia license", "SIA Licence"),
        ("sia door supervision", "SIA Door Supervision"),
        ("sia cctv", "SIA CCTV"), ("sia close protection", "SIA Close Protection"),
        ("bs 7858", "BS 7858"),
    ]:
        entries[label] = canonical

    # Finance
    for label, canonical in [
        ("acca", "ACCA"), ("cima", "CIMA"), ("aat", "AAT"),
        ("aca", "ACA"), ("icaew", "ICAEW"), ("cfa", "CFA"),
        ("cisi", "CISI"), ("fca regulated", "FCA Regulated"),
        ("pra regulated", "PRA Regulated"),
    ]:
        entries[label] = canonical

    # HR / Management
    for label, canonical in [
        ("cipd", "CIPD"), ("cipd level 3", "CIPD Level 3"),
        ("cipd level 5", "CIPD Level 5"), ("cipd level 7", "CIPD Level 7"),
        ("prince2", "PRINCE2"), ("apm", "APM"), ("cmi", "CMI"),
        ("ilm", "ILM"), ("nebosh", "NEBOSH"), ("iosh", "IOSH"),
    ]:
        entries[label] = canonical

    # Safeguarding
    for label, canonical in [
        ("dbs check", "DBS Check"), ("dbs", "DBS Check"),
        ("enhanced dbs", "Enhanced DBS"),
        ("first aid at work", "First Aid at Work"),
        ("first aid", "First Aid at Work"),
        ("safeguarding certificate", "Safeguarding Certificate"),
        ("safeguarding", "Safeguarding Certificate"),
        ("food hygiene level 2", "Food Hygiene Level 2"),
        ("food hygiene level 3", "Food Hygiene Level 3"),
        ("food hygiene", "Food Hygiene Level 2"),
    ]:
        entries[label] = canonical

    # Health / Social
    for label, canonical in [
        ("nmc registered", "NMC Registered"), ("nmc", "NMC Registered"),
        ("hcpc registered", "HCPC Registered"), ("hcpc", "HCPC Registered"),
        ("gmc registered", "GMC Registered"), ("gmc", "GMC Registered"),
        ("gphc", "GPhC"), ("sssc", "SSSC"),
        ("care certificate", "Care Certificate"),
    ]:
        entries[label] = canonical

    # Driving
    for label, canonical in [
        ("full uk driving licence", "Full UK Driving Licence"),
        ("full driving licence", "Full UK Driving Licence"),
        ("clean driving licence", "Full UK Driving Licence"),
        ("driving licence", "Driving Licence"),
        ("cat c", "Cat C Licence"), ("cat ce", "Cat CE Licence"),
        ("hgv class 1", "HGV Class 1"), ("hgv class 2", "HGV Class 2"),
        ("adr", "ADR"), ("cpc", "CPC"),
        ("forklift licence", "Forklift Licence"),
        ("forklift", "Forklift Licence"),
    ]:
        entries[label] = canonical

    # Legal
    for label, canonical in [
        ("sra regulated", "SRA Regulated"), ("cilex", "CILEx"),
        ("oisc level 1", "OISC Level 1"), ("oisc level 2", "OISC Level 2"),
        ("oisc level 3", "OISC Level 3"),
        ("sqe1", "SQE1"), ("sqe2", "SQE2"), ("lpc", "LPC"), ("bptc", "BPTC"),
    ]:
        entries[label] = canonical

    return entries


def build_dictionary(esco_csv_path: str | None = None) -> dict[str, str]:
    """Build combined skill dictionary from all sources.

    Args:
        esco_csv_path: Path to ESCO skills_en.csv. If None, uses Phase 1 dict + UK entries only.

    Returns:
        Dict mapping lowercase pattern → canonical name.
        Expected: ~450+ patterns without ESCO, ~40K-60K with ESCO.
    """
    combined: dict[str, str] = {}

    # Layer 1: Phase 1 dictionary (~150 skills)
    combined.update(SKILLS_DICT)

    # Layer 2: UK-specific entries (~300 skills)
    combined.update(build_uk_entries())

    # Layer 3: ESCO CSV (if provided, ~13,939 skills + aliases)
    if esco_csv_path is not None:
        esco_skills = load_esco_csv(esco_csv_path)
        for _uri, skill_data in esco_skills.items():
            preferred = str(skill_data["preferred_label"])
            # Add preferred label
            key = preferred.lower()
            if key not in combined:
                combined[key] = preferred

            # Add alt labels as patterns
            alt_labels = skill_data.get("alt_labels", [])
            if isinstance(alt_labels, list):
                for alt in alt_labels:
                    alt_key = str(alt).lower()
                    if alt_key not in combined:
                        combined[alt_key] = preferred

    return combined
