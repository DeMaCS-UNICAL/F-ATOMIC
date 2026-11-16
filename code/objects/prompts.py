"""
    messages = build_messages("crowbar", sense="...", events=["PersonX ...", ...])
    ctxs = parse_output(raw_text)          # list of validated ObjectContext
    problems = check_contexts(ctxs)        # content checks (empty list = ok)
"""
import json
import re
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

EXAMPLE_ENTITY = "crowbar"
EXCLUDED_ENTITIES = {EXAMPLE_ENTITY}

TAXONOMY: Dict[str, List[str]] = {
    "Violent Crimes": ["Assault", "Homicide", "Kidnapping", "Robbery", "Sexual Offense"],
    "Property Crimes": ["Theft", "Burglary", "Arson", "Vandalism", "Trespassing"],
    "Financial Crimes": ["Fraud", "Money Laundering", "Embezzlement", "Bribery", "Tax Evasion"],
    "Cyber Crimes": ["Hacking", "Phishing", "Identity Theft", "Online Harassment"],
    "Organized Crimes": ["Drug Trafficking", "Human Trafficking", "Racketeering", "Weapon Smuggling"],
    "Public Order/Justice": ["Perjury", "Obstruction of Justice", "Disorderly Conduct"],
}

RELATION_FIELDS = ["IsA", "UsedFor", "AtLocation", "MadeOf", "PartOf", "HasProperty", "HasA"]
GENERIC_TERMS = ["crime scene", "physical evidence", "evidence room", "evidence bag", "police station"]


class ObjectContext(BaseModel):
    crime_category: str
    crime_subcategory: str
    brief_context: str
    IsA: str
    UsedFor: List[str] = Field(default_factory=list)
    AtLocation: List[str] = Field(default_factory=list)
    MadeOf: List[str] = Field(default_factory=list)
    PartOf: List[str] = Field(default_factory=list)
    HasProperty: List[str] = Field(default_factory=list)
    HasA: List[str] = Field(default_factory=list)


def parse_output(raw: str) -> List[ObjectContext]:
    text = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M).strip()
    data = json.loads(text)
    return [ObjectContext.model_validate(o) for o in data]


def check_contexts(ctxs: List[ObjectContext], entity: Optional[str] = None) -> List[str]:
    """Content checks (structure is validated by Pydantic)."""
    problems = []
    if len(ctxs) > 2:
        problems.append("more than 2 contexts")
    pairs = set()
    for i, c in enumerate(ctxs):
        if c.crime_category not in TAXONOMY:
            problems.append(f"[{i}] category outside the taxonomy: {c.crime_category!r}")
        elif c.crime_subcategory not in TAXONOMY[c.crime_category]:
            problems.append(f"[{i}] invalid subcategory for {c.crime_category}: {c.crime_subcategory!r}")
        pairs.add((c.crime_category, c.crime_subcategory))
        if not any(getattr(c, f) for f in RELATION_FIELDS):
            problems.append(f"[{i}] all relation lists are empty")
        for f in RELATION_FIELDS:
            vals = getattr(c, f)
            if len(vals) > (2 if f == "IsA" else 4):
                problems.append(f"[{i}] {f}: more than {2 if f == 'IsA' else 4} items")
            if len({v.lower() for v in vals}) != len(vals):
                problems.append(f"[{i}] {f}: duplicates")
            for v in vals:
                if len(v.split()) > (2 if f == "IsA" else 4):
                    problems.append(f"[{i}] {f}: item too long: {v!r}")
                if v.lower() in GENERIC_TERMS:
                    problems.append(f"[{i}] {f}: generic term {v!r}")
                if entity and entity.replace("_", " ").lower() in v.lower():
                    problems.append(f"[{i}] {f}: repeats the entity name: {v!r}")
    if len(ctxs) == 2 and len(pairs) < 2:
        problems.append("the two contexts have the same category and subcategory")
    return problems


def _taxonomy_text() -> str:
    return "\n".join(f"- **{c}:** ({', '.join(s)})" for c, s in TAXONOMY.items())


EXAMPLE_INPUT = """Entity: crowbar"""

EXAMPLE_OUTPUT = """[
  {
    "crime_category": "Property Crimes",
    "crime_subcategory": "Burglary",
    "brief_context": "PersonX uses a crowbar to force open a rear door and enter a house to steal.",
    "IsA": "instrument",
    "UsedFor": ["force entry", "pry open doors"],
    "AtLocation": ["tool bag", "garage"],
    "MadeOf": ["steel"],
    "PartOf": ["intruder's tool bag"],
    "HasProperty": ["easy to conceal"],
    "HasA": ["flat prying end", "curved claw"]
  },
  {
    "crime_category": "Violent Crimes",
    "crime_subcategory": "Assault",
    "brief_context": "PersonX swings a crowbar at another person during a fight to hurt them.",
    "IsA": "weapon",
    "UsedFor": ["strike a person", "threaten people"],
    "AtLocation": ["car trunk"],
    "MadeOf": ["steel"],
    "PartOf": [],
    "HasProperty": ["heavy"],
    "HasA": ["curved claw"]
  }
]"""

SYSTEM_PROMPT = f"""You are an expert Forensic Criminologist building a commonsense knowledge resource.
Your task is to take ONE entity (a physical object) and state what is commonly known about it in the criminal contexts where it plausibly appears.

### CORE DIRECTIVE: "DIVERSE CONTEXTUAL BRANCHING"
The role of an object changes with the context. Generate a **JSON LIST of 1 or 2 objects**, one per context:
- Generate 2 contexts only when the entity plausibly appears in two DIFFERENT crime categories or subcategories. If only one context is realistic, generate one. Never invent a second context to reach two.
- If the entity has no plausible criminal context at all, return an empty list: []

### FORENSIC TAXONOMY
{_taxonomy_text()}

### TAXONOMY RULES
- "crime_category" MUST be EXACTLY ONE top-level category above. NEVER combine categories with '/', 'and', ',' or any separator.
- "crime_subcategory" MUST be EXACTLY ONE subcategory listed in parentheses under the chosen category. NEVER combine or invent subcategories.
- "Non-Criminal", "Deceptive Prank", "Daily Routine" and any label outside the taxonomy are NOT valid.
- If two contexts are generated, they MUST differ in category or subcategory.

### COMMONSENSE STYLE
Each item must be a short phrase stating something generally true of this kind of object in this context.
- Write what is TYPICALLY true, not what happened in one story. Do not describe the traces, injuries, victims or events of a single case.
- Write items as short phrases of 1-4 words, lowercase: a noun or noun phrase, or for UsedFor a verb phrase without "to".

### FIELDS
- brief_context: ONE sentence starting with PersonX, describing the scenario that fixes the crime category for this context.
- IsA: the general class the object belongs to, as a broad category noun of 1-2 words. 
- UsedFor: what the object is used for in this context. Verb phrases without "to".
- AtLocation: where the object is typically found, kept or used in this context.
- MadeOf: materials or substances the object is typically made of.
- PartOf: a larger kit, set or apparatus the object typically belongs to in this context.
- HasProperty: typical properties of the object that matter in this context.
- HasA: typical parts, components, modifications or contents of the object.

### GENERATION RULES
1. **Omission:** a relation field may be an empty list [] when you cannot give a plausible item that is specific to this entity.
2. **Specificity:** each item must be specific to this entity in this context. Never output items that would fit any object, such as: {', '.join(GENERIC_TERMS)}.
3. **No echo:** items must not repeat the entity's name.
4. **Variety:** when two contexts are generated, their context-dependent lists (IsA, UsedFor, AtLocation, PartOf, HasProperty) must differ in content, exploring a different angle of the object. 
5. **Format:** every relation field has 0-4 items, with no duplicates inside a list.

### OUTPUT SCHEMA (strict JSON list, no text before or after, no markdown fences)
[
  {{
    "crime_category": "String, EXACTLY ONE category from the taxonomy",
    "crime_subcategory": "String, EXACTLY ONE subcategory under that category",
    "brief_context": "String",
    "IsA": ["String", ...],
    "UsedFor": ["String", ...],
    "AtLocation": ["String", ...],
    "MadeOf": ["String", ...],
    "PartOf": ["String", ...],
    "HasProperty": ["String", ...],
    "HasA": ["String", ...]
  }}
]
All keys must always be present. Use [] for an empty relation.

### EXAMPLE (illustration of format only)
Input:
{EXAMPLE_INPUT}

Output:
{EXAMPLE_OUTPUT}"""

def build_messages(entity: str) -> List[dict]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Entity: {entity.replace('_', ' ')}"},
    ]