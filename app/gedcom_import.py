"""Minimal GEDCOM 5.5.1 parser covering the fields this app tracks.

Not a full spec implementation -- handles the common INDI/FAM structure
produced by Ancestry.com, FamilySearch, Gramps, and similar tools:
NAME, SEX, BIRT/DEAT (DATE/PLAC), FAMC/FAMS, NOTE, HUSB/WIFE/CHIL, MARR.
"""

from app.extensions import db
from app.models import Family, FamilyChild, Person


def _parse_name(value: str):
    if "/" in value:
        given, _, rest = value.partition("/")
        surname, _, _ = rest.partition("/")
        return given.strip(), surname.strip()
    return value.strip(), ""


def _split_line(raw_line: str):
    parts = raw_line.strip().split(" ", 2)
    level = int(parts[0])
    if len(parts) >= 3 and parts[1].startswith("@"):
        return level, parts[1], parts[2], None  # xref line: level, xref, tag, (no value slot used)
    tag = parts[1] if len(parts) > 1 else ""
    value = parts[2] if len(parts) > 2 else ""
    return level, None, tag, value


def _parse_records(text: str) -> dict:
    records = {}
    current_xref = None
    for raw_line in text.splitlines():
        if not raw_line.strip():
            continue
        parts = raw_line.strip().split(" ", 2)
        level = int(parts[0])
        if level == 0:
            if len(parts) >= 3 and parts[1].startswith("@") and parts[2] in ("INDI", "FAM"):
                current_xref = parts[1]
                records[current_xref] = {"type": parts[2], "lines": []}
            else:
                current_xref = None
            continue
        if current_xref is None:
            continue
        tag = parts[1] if len(parts) > 1 else ""
        value = parts[2] if len(parts) > 2 else ""
        records[current_xref]["lines"].append((level, tag, value))
    return records


def _parse_individual(lines):
    data = {
        "given_names": "",
        "surname": "",
        "sex": "U",
        "birth_date": "",
        "birth_place": "",
        "death_date": "",
        "death_place": "",
        "famc": [],
        "fams": [],
        "notes": [],
    }
    context = None
    for level, tag, value in lines:
        if level == 1:
            context = None
            if tag == "NAME":
                data["given_names"], data["surname"] = _parse_name(value)
            elif tag == "SEX":
                data["sex"] = (value.strip()[:1] or "U").upper()
            elif tag == "BIRT":
                context = "BIRT"
            elif tag == "DEAT":
                context = "DEAT"
            elif tag == "FAMC":
                data["famc"].append(value.strip())
            elif tag == "FAMS":
                data["fams"].append(value.strip())
            elif tag == "NOTE":
                data["notes"].append(value)
        elif level == 2 and context in ("BIRT", "DEAT"):
            prefix = "birth" if context == "BIRT" else "death"
            if tag == "DATE":
                data[f"{prefix}_date"] = value
            elif tag == "PLAC":
                data[f"{prefix}_place"] = value
    return data


def _parse_family(lines):
    data = {"husb": None, "wife": None, "chil": [], "marriage_date": "", "marriage_place": ""}
    context = None
    for level, tag, value in lines:
        if level == 1:
            if tag == "HUSB":
                data["husb"] = value.strip()
                context = None
            elif tag == "WIFE":
                data["wife"] = value.strip()
                context = None
            elif tag == "CHIL":
                data["chil"].append(value.strip())
                context = None
            elif tag == "MARR":
                context = "MARR"
            else:
                context = None
        elif level == 2 and context == "MARR":
            if tag == "DATE":
                data["marriage_date"] = value
            elif tag == "PLAC":
                data["marriage_place"] = value
    return data


def import_gedcom(text: str) -> dict:
    records = _parse_records(text)

    person_map = {}  # gedcom xref -> Person
    family_map = {}  # gedcom xref -> Family

    for xref, record in records.items():
        if record["type"] == "INDI":
            info = _parse_individual(record["lines"])
            person = Person(
                given_names=info["given_names"],
                surname=info["surname"],
                sex=info["sex"] if info["sex"] in ("M", "F") else "U",
                birth_date=info["birth_date"],
                birth_place=info["birth_place"],
                death_date=info["death_date"],
                death_place=info["death_place"],
                is_living=not bool(info["death_date"] or info["death_place"]),
                notes="\n".join(info["notes"]) if info["notes"] else None,
            )
            db.session.add(person)
            person_map[xref] = (person, info)

    db.session.flush()

    for xref, record in records.items():
        if record["type"] == "FAM":
            info = _parse_family(record["lines"])
            husb_person = person_map.get(info["husb"], (None,))[0] if info["husb"] else None
            wife_person = person_map.get(info["wife"], (None,))[0] if info["wife"] else None
            family = Family(
                spouse1_id=husb_person.id if husb_person else None,
                spouse2_id=wife_person.id if wife_person else None,
                marriage_date=info["marriage_date"],
                marriage_place=info["marriage_place"],
            )
            db.session.add(family)
            family_map[xref] = (family, info)

    db.session.flush()

    child_links = 0
    for family, info in family_map.values():
        for child_xref in info["chil"]:
            child_person = person_map.get(child_xref, (None,))[0]
            if child_person:
                db.session.add(FamilyChild(family_id=family.id, person_id=child_person.id))
                child_links += 1

    db.session.commit()

    return {
        "people": len(person_map),
        "families": len(family_map),
        "child_links": child_links,
    }
