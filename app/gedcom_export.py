"""Minimal GEDCOM 5.5.1 writer covering the fields this app tracks."""

from datetime import datetime, timezone

from app.models import Family, Person


def _esc(value: str) -> str:
    return (value or "").replace("\r", "").replace("\n", " ")


def export_gedcom() -> str:
    lines = [
        "0 HEAD",
        "1 SOUR FamilyTree",
        "1 GEDC",
        "2 VERS 5.5.1",
        "2 FORM LINEAGE-LINKED",
        "1 CHAR UTF-8",
        f"1 DATE {datetime.now(timezone.utc).strftime('%d %b %Y').upper()}",
    ]

    people = Person.query.order_by(Person.id).all()
    families = Family.query.order_by(Family.id).all()

    for person in people:
        pid = f"@I{person.id}@"
        lines.append(f"0 {pid} INDI")
        lines.append(f"1 NAME {_esc(person.given_names)} /{_esc(person.surname)}/")
        lines.append(f"1 SEX {person.sex or 'U'}")
        if person.birth_date or person.birth_place:
            lines.append("1 BIRT")
            if person.birth_date:
                lines.append(f"2 DATE {_esc(person.birth_date)}")
            if person.birth_place:
                lines.append(f"2 PLAC {_esc(person.birth_place)}")
        if person.death_date or person.death_place:
            lines.append("1 DEAT")
            if person.death_date:
                lines.append(f"2 DATE {_esc(person.death_date)}")
            if person.death_place:
                lines.append(f"2 PLAC {_esc(person.death_place)}")
        for fam in families:
            if person.id in (fam.spouse1_id, fam.spouse2_id):
                lines.append(f"1 FAMS @F{fam.id}@")
        for fam in person.families_as_child():
            lines.append(f"1 FAMC @F{fam.id}@")
        if person.notes:
            for note_line in _esc(person.notes).splitlines() or [""]:
                lines.append(f"1 NOTE {note_line}")

    for fam in families:
        fid = f"@F{fam.id}@"
        lines.append(f"0 {fid} FAM")
        husb = wife = None
        if fam.spouse1 and fam.spouse1.sex == "M":
            husb, wife = fam.spouse1, fam.spouse2
        elif fam.spouse2 and fam.spouse2.sex == "M":
            husb, wife = fam.spouse2, fam.spouse1
        else:
            husb, wife = fam.spouse1, fam.spouse2
        if husb:
            lines.append(f"1 HUSB @I{husb.id}@")
        if wife:
            lines.append(f"1 WIFE @I{wife.id}@")
        for child in fam.children():
            lines.append(f"1 CHIL @I{child.id}@")
        if fam.marriage_date or fam.marriage_place:
            lines.append("1 MARR")
            if fam.marriage_date:
                lines.append(f"2 DATE {_esc(fam.marriage_date)}")
            if fam.marriage_place:
                lines.append(f"2 PLAC {_esc(fam.marriage_place)}")

    lines.append("0 TRLR")
    return "\n".join(lines) + "\n"
