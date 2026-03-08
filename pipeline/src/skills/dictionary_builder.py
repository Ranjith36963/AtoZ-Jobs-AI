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

    # Education (~35 entries)
    for label, canonical in [
        ("gcse", "GCSE"),
        ("gcses", "GCSE"),
        ("a-level", "A-Level"),
        ("a level", "A-Level"),
        ("a levels", "A-Level"),
        ("btec", "BTEC"),
        ("btec national", "BTEC"),
        ("nvq", "NVQ"),
        ("nvq level 1", "NVQ Level 1"),
        ("nvq level 2", "NVQ Level 2"),
        ("nvq level 3", "NVQ Level 3"),
        ("nvq level 4", "NVQ Level 4"),
        ("nvq level 5", "NVQ Level 5"),
        ("nvq level 6", "NVQ Level 6"),
        ("nvq level 7", "NVQ Level 7"),
        ("city & guilds", "City & Guilds"),
        ("city and guilds", "City & Guilds"),
        ("c&g", "City & Guilds"),
        ("hnc", "HNC"),
        ("hnd", "HND"),
        ("qts", "QTS"),
        ("pgce", "PGCE"),
        ("pgde", "PGDE"),
        ("foundation degree", "Foundation Degree"),
        ("access to he", "Access to HE"),
        ("access to higher education", "Access to HE"),
        ("apprenticeship level 2", "Apprenticeship Level 2"),
        ("apprenticeship level 3", "Apprenticeship Level 3"),
        ("apprenticeship level 4", "Apprenticeship Level 4"),
        ("apprenticeship level 6", "Apprenticeship Level 6"),
        ("t-level", "T-Level"),
        ("t level", "T-Level"),
        ("diploma level 3", "Diploma Level 3"),
        ("diploma level 5", "Diploma Level 5"),
        ("degree educated", "Degree Educated"),
        ("masters degree", "Masters Degree"),
    ]:
        entries[label] = canonical

    # Construction (~30 entries)
    for label, canonical in [
        ("cscs", "CSCS Card"),
        ("cscs card", "CSCS Card"),
        ("cscs green card", "CSCS Green Card"),
        ("cscs blue card", "CSCS Blue Card"),
        ("cscs gold card", "CSCS Gold Card"),
        ("smsts", "SMSTS"),
        ("sssts", "SSSTS"),
        ("cpcs", "CPCS"),
        ("cpcs blue card", "CPCS Blue Card"),
        ("cpcs red card", "CPCS Red Card"),
        ("ipaf", "IPAF"),
        ("ipaf operator", "IPAF"),
        ("pasma", "PASMA"),
        ("pasma towers", "PASMA"),
        ("gas safe", "Gas Safe"),
        ("gas safe registered", "Gas Safe"),
        ("gas safe engineer", "Gas Safe"),
        ("part p", "Part P"),
        ("part p qualified", "Part P"),
        ("jib card", "JIB Card"),
        ("ecs card", "ECS Card"),
        ("citb", "CITB"),
        ("citb registered", "CITB"),
        ("nrswa", "NRSWA"),
        ("street works", "NRSWA"),
        ("asbestos awareness", "Asbestos Awareness"),
        ("working at heights", "Working at Heights"),
        ("confined spaces", "Confined Spaces"),
        ("abrasive wheels", "Abrasive Wheels"),
        ("scaffolding ticket", "Scaffolding Ticket"),
    ]:
        entries[label] = canonical

    # Security (~15 entries)
    for label, canonical in [
        ("sia licence", "SIA Licence"),
        ("sia license", "SIA Licence"),
        ("sia badge", "SIA Licence"),
        ("sia door supervision", "SIA Door Supervision"),
        ("sia cctv", "SIA CCTV"),
        ("sia close protection", "SIA Close Protection"),
        ("sia security guard", "SIA Security Guard"),
        ("bs 7858", "BS 7858"),
        ("bs 7858 vetting", "BS 7858"),
        ("act awareness", "ACT Awareness"),
        ("conflict management", "Conflict Management"),
        ("sc clearance", "SC Clearance"),
        ("sc cleared", "SC Clearance"),
        ("dv clearance", "DV Clearance"),
        ("dv cleared", "DV Clearance"),
    ]:
        entries[label] = canonical

    # Finance (~20 entries)
    for label, canonical in [
        ("acca", "ACCA"),
        ("acca qualified", "ACCA"),
        ("cima", "CIMA"),
        ("cima qualified", "CIMA"),
        ("aat", "AAT"),
        ("aat qualified", "AAT"),
        ("aca", "ACA"),
        ("aca qualified", "ACA"),
        ("icaew", "ICAEW"),
        ("cfa", "CFA"),
        ("cfa level 1", "CFA Level 1"),
        ("cfa level 2", "CFA Level 2"),
        ("cfa level 3", "CFA Level 3"),
        ("cisi", "CISI"),
        ("fca regulated", "FCA Regulated"),
        ("fca authorised", "FCA Regulated"),
        ("pra regulated", "PRA Regulated"),
        ("mifid ii", "MiFID II"),
        ("mifid 2", "MiFID II"),
        ("sox compliance", "SOX Compliance"),
        ("ifrs", "IFRS"),
        ("gaap", "GAAP"),
        ("uk gaap", "UK GAAP"),
    ]:
        entries[label] = canonical

    # HR / Management (~25 entries)
    for label, canonical in [
        ("cipd", "CIPD"),
        ("cipd level 3", "CIPD Level 3"),
        ("cipd level 5", "CIPD Level 5"),
        ("cipd level 7", "CIPD Level 7"),
        ("cipd associate", "CIPD Associate"),
        ("cipd chartered", "CIPD Chartered"),
        ("prince2", "PRINCE2"),
        ("prince2 practitioner", "PRINCE2 Practitioner"),
        ("apm", "APM"),
        ("apm pq", "APM PQ"),
        ("cmi", "CMI"),
        ("cmi level 5", "CMI Level 5"),
        ("ilm", "ILM"),
        ("ilm level 3", "ILM Level 3"),
        ("ilm level 5", "ILM Level 5"),
        ("nebosh", "NEBOSH"),
        ("nebosh general", "NEBOSH General Certificate"),
        ("nebosh construction", "NEBOSH Construction"),
        ("nebosh fire", "NEBOSH Fire Certificate"),
        ("nebosh oil and gas", "NEBOSH Oil and Gas"),
        ("iosh", "IOSH"),
        ("iosh managing safely", "IOSH Managing Safely"),
        ("iosh working safely", "IOSH Working Safely"),
        ("itil", "ITIL"),
        ("itil v4", "ITIL"),
        ("six sigma", "Six Sigma"),
        ("lean six sigma", "Lean Six Sigma"),
    ]:
        entries[label] = canonical

    # Safeguarding / Health & Safety (~25 entries)
    for label, canonical in [
        ("dbs check", "DBS Check"),
        ("dbs", "DBS Check"),
        ("enhanced dbs", "Enhanced DBS"),
        ("enhanced dbs check", "Enhanced DBS"),
        ("first aid at work", "First Aid at Work"),
        ("first aid", "First Aid at Work"),
        ("emergency first aid", "Emergency First Aid at Work"),
        ("paediatric first aid", "Paediatric First Aid"),
        ("safeguarding certificate", "Safeguarding Certificate"),
        ("safeguarding", "Safeguarding Certificate"),
        ("safeguarding level 2", "Safeguarding Level 2"),
        ("safeguarding level 3", "Safeguarding Level 3"),
        ("food hygiene level 2", "Food Hygiene Level 2"),
        ("food hygiene level 3", "Food Hygiene Level 3"),
        ("food hygiene", "Food Hygiene Level 2"),
        ("food safety", "Food Safety"),
        ("manual handling", "Manual Handling"),
        ("manual handling trained", "Manual Handling"),
        ("coshh", "COSHH"),
        ("coshh trained", "COSHH"),
        ("fire safety", "Fire Safety"),
        ("fire marshal", "Fire Marshal"),
        ("fire warden", "Fire Warden"),
        ("lone working", "Lone Working"),
        ("infection control", "Infection Control"),
        ("mental health first aid", "Mental Health First Aid"),
        ("riddor", "RIDDOR"),
        ("risk assessment", "Risk Assessment"),
    ]:
        entries[label] = canonical

    # Health / Social Care (~20 entries)
    for label, canonical in [
        ("nmc registered", "NMC Registered"),
        ("nmc", "NMC Registered"),
        ("nmc pin", "NMC PIN"),
        ("hcpc registered", "HCPC Registered"),
        ("hcpc", "HCPC Registered"),
        ("gmc registered", "GMC Registered"),
        ("gmc", "GMC Registered"),
        ("gphc", "GPhC"),
        ("gphc registered", "GPhC"),
        ("sssc", "SSSC"),
        ("sssc registered", "SSSC"),
        ("care certificate", "Care Certificate"),
        ("cqc", "CQC"),
        ("cqc registered", "CQC Registered"),
        ("nice guidelines", "NICE Guidelines"),
        ("bls", "BLS"),
        ("basic life support", "BLS"),
        ("ils", "ILS"),
        ("intermediate life support", "ILS"),
        ("als", "ALS"),
        ("advanced life support", "ALS"),
        ("tissue viability", "Tissue Viability"),
        ("wound care", "Wound Care"),
        ("medication management", "Medication Management"),
        ("medication administration", "Medication Administration"),
    ]:
        entries[label] = canonical

    # Driving (~25 entries)
    for label, canonical in [
        ("full uk driving licence", "Full UK Driving Licence"),
        ("full driving licence", "Full UK Driving Licence"),
        ("clean driving licence", "Full UK Driving Licence"),
        ("driving licence", "Driving Licence"),
        ("uk driving licence", "Full UK Driving Licence"),
        ("cat c", "Cat C Licence"),
        ("cat c licence", "Cat C Licence"),
        ("cat ce", "Cat CE Licence"),
        ("cat ce licence", "Cat CE Licence"),
        ("cat c1", "Cat C1 Licence"),
        ("cat d", "Cat D Licence"),
        ("hgv class 1", "HGV Class 1"),
        ("hgv class 2", "HGV Class 2"),
        ("hgv licence", "HGV Licence"),
        ("lgv licence", "LGV Licence"),
        ("adr", "ADR"),
        ("adr certified", "ADR"),
        ("adr class 1", "ADR Class 1"),
        ("adr class 3", "ADR Class 3"),
        ("cpc", "CPC"),
        ("driver cpc", "Driver CPC"),
        ("transport cpc", "Transport Manager CPC"),
        ("forklift licence", "Forklift Licence"),
        ("forklift", "Forklift Licence"),
        ("counterbalance forklift", "Counterbalance Forklift"),
        ("reach truck", "Reach Truck"),
        ("reach truck licence", "Reach Truck"),
        ("telehandler", "Telehandler"),
        ("cherry picker", "Cherry Picker"),
        ("tachograph", "Digital Tachograph"),
        ("digital tachograph", "Digital Tachograph"),
        ("fors", "FORS"),
    ]:
        entries[label] = canonical

    # Legal (~15 entries)
    for label, canonical in [
        ("sra regulated", "SRA Regulated"),
        ("sra compliant", "SRA Regulated"),
        ("cilex", "CILEx"),
        ("cilex qualified", "CILEx"),
        ("oisc level 1", "OISC Level 1"),
        ("oisc level 2", "OISC Level 2"),
        ("oisc level 3", "OISC Level 3"),
        ("sqe1", "SQE1"),
        ("sqe2", "SQE2"),
        ("sqe", "SQE"),
        ("lpc", "LPC"),
        ("bptc", "BPTC"),
        ("qualified solicitor", "Qualified Solicitor"),
        ("practising certificate", "Practising Certificate"),
        ("legal aid", "Legal Aid"),
    ]:
        entries[label] = canonical

    # IT / Cyber Security (~20 entries) — NEW category
    for label, canonical in [
        ("cyber essentials", "Cyber Essentials"),
        ("cyber essentials plus", "Cyber Essentials Plus"),
        ("iso 27001", "ISO 27001"),
        ("iso27001", "ISO 27001"),
        ("gdpr", "GDPR"),
        ("gdpr compliance", "GDPR"),
        ("pci dss", "PCI DSS"),
        ("pci compliance", "PCI DSS"),
        ("comptia security+", "CompTIA Security+"),
        ("security+", "CompTIA Security+"),
        ("cissp", "CISSP"),
        ("ceh", "CEH"),
        ("soc 2", "SOC 2"),
        ("soc2", "SOC 2"),
        ("penetration testing", "Penetration Testing"),
        ("pen testing", "Penetration Testing"),
        ("iso 9001", "ISO 9001"),
        ("iso 14001", "ISO 14001"),
        ("iso 45001", "ISO 45001"),
        ("crest certified", "CREST Certified"),
    ]:
        entries[label] = canonical

    # Teaching / Education Sector (~15 entries) — NEW category
    for label, canonical in [
        ("eyfs", "EYFS"),
        ("early years foundation stage", "EYFS"),
        ("sen", "SEN"),
        ("send", "SEND"),
        ("special educational needs", "SEN"),
        ("senco", "SENCo"),
        ("sen coordinator", "SENCo"),
        ("ofsted", "Ofsted"),
        ("ofsted outstanding", "Ofsted Outstanding"),
        ("teaching assistant", "Teaching Assistant"),
        ("higher level teaching assistant", "HLTA"),
        ("hlta", "HLTA"),
        ("classroom management", "Classroom Management"),
        ("lesson planning", "Lesson Planning"),
        ("phonics", "Phonics"),
        ("synthetic phonics", "Phonics"),
        ("behaviour management", "Behaviour Management"),
        ("send code of practice", "SEND Code of Practice"),
    ]:
        entries[label] = canonical

    # Trades / Engineering (~20 entries) — NEW category
    for label, canonical in [
        ("18th edition", "18th Edition Wiring Regulations"),
        ("18th edition wiring", "18th Edition Wiring Regulations"),
        ("bs 7671", "18th Edition Wiring Regulations"),
        ("pat testing", "PAT Testing"),
        ("pat tester", "PAT Testing"),
        ("2391", "2391 Inspection and Testing"),
        ("2391 inspection", "2391 Inspection and Testing"),
        ("am2", "AM2"),
        ("am2 assessment", "AM2"),
        ("jib grading", "JIB Grading"),
        ("jib gold card", "JIB Gold Card"),
        ("niceic", "NICEIC"),
        ("niceic approved", "NICEIC"),
        ("napit", "NAPIT"),
        ("plumbing nvq", "Plumbing NVQ"),
        ("electrical installation", "Electrical Installation"),
        ("acs gas", "ACS Gas"),
        ("acs qualified", "ACS Gas"),
        ("oftec", "OFTEC"),
        ("oftec registered", "OFTEC"),
        ("f-gas", "F-Gas"),
        ("f-gas certified", "F-Gas"),
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
