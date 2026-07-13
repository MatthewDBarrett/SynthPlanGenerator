from flask import Blueprint, redirect, request, url_for

from app.extensions import db
from app.models import Family, FamilyChild, Person

bp = Blueprint("families", __name__)


def _new_person_from_form(form, prefix="") -> Person:
    return Person(
        given_names=form.get(f"{prefix}given_names", "").strip(),
        surname=form.get(f"{prefix}surname", "").strip(),
        sex=form.get(f"{prefix}sex", "U") or "U",
        birth_date=form.get(f"{prefix}birth_date", "").strip(),
        birth_place=form.get(f"{prefix}birth_place", "").strip(),
        death_date=form.get(f"{prefix}death_date", "").strip(),
        death_place=form.get(f"{prefix}death_place", "").strip(),
    )


def _resolve_person(form) -> Person:
    """Either look up an existing person by id, or build a new one from the form."""
    mode = form.get("mode", "new")
    if mode == "existing":
        existing_id = form.get("existing_id", type=int)
        return Person.query.get_or_404(existing_id)
    person = _new_person_from_form(form)
    db.session.add(person)
    return person


@bp.route("/people/<int:person_id>/parents", methods=["POST"])
def add_parent(person_id):
    person = Person.query.get_or_404(person_id)
    relation = request.form.get("relation")  # 'father' or 'mother'

    families_as_child = person.families_as_child()
    family = families_as_child[0] if families_as_child else None
    if family is None:
        family = Family()
        db.session.add(family)
        db.session.flush()
        db.session.add(FamilyChild(family_id=family.id, person_id=person.id))

    parent = _resolve_person(request.form)
    db.session.flush()

    slot_is_father_slot = relation == "father"
    if slot_is_father_slot:
        if family.spouse1_id is None:
            family.spouse1_id = parent.id
        elif family.spouse2_id is None:
            family.spouse2_id = parent.id
        else:
            family.spouse1_id = parent.id
    else:
        if family.spouse2_id is None:
            family.spouse2_id = parent.id
        elif family.spouse1_id is None:
            family.spouse1_id = parent.id
        else:
            family.spouse2_id = parent.id

    if parent.sex == "U":
        parent.sex = "M" if relation == "father" else "F"

    db.session.commit()
    return redirect(url_for("people.detail", person_id=person.id))


@bp.route("/people/<int:person_id>/spouses", methods=["POST"])
def add_spouse(person_id):
    person = Person.query.get_or_404(person_id)
    spouse = _resolve_person(request.form)
    db.session.flush()

    existing = Family.query.filter(
        db.or_(
            db.and_(Family.spouse1_id == person.id, Family.spouse2_id == spouse.id),
            db.and_(Family.spouse1_id == spouse.id, Family.spouse2_id == person.id),
        )
    ).first()

    marriage_date = request.form.get("marriage_date", "").strip()
    marriage_place = request.form.get("marriage_place", "").strip()

    if existing:
        existing.marriage_date = marriage_date or existing.marriage_date
        existing.marriage_place = marriage_place or existing.marriage_place
    else:
        family = Family(
            spouse1_id=person.id,
            spouse2_id=spouse.id,
            marriage_date=marriage_date,
            marriage_place=marriage_place,
        )
        db.session.add(family)

    db.session.commit()
    return redirect(url_for("people.detail", person_id=person.id))


@bp.route("/people/<int:person_id>/children", methods=["POST"])
def add_child(person_id):
    person = Person.query.get_or_404(person_id)

    family_id = request.form.get("family_id", type=int)
    if family_id:
        family = Family.query.get_or_404(family_id)
    else:
        family = Family(spouse1_id=person.id)
        db.session.add(family)
        db.session.flush()

    child = _resolve_person(request.form)
    db.session.flush()

    already_linked = FamilyChild.query.filter_by(family_id=family.id, person_id=child.id).first()
    if not already_linked:
        db.session.add(FamilyChild(family_id=family.id, person_id=child.id))

    db.session.commit()
    return redirect(url_for("people.detail", person_id=person.id))


@bp.route("/families/<int:family_id>/edit", methods=["POST"])
def edit_family(family_id):
    family = Family.query.get_or_404(family_id)
    family.marriage_date = request.form.get("marriage_date", "").strip()
    family.marriage_place = request.form.get("marriage_place", "").strip()
    family.divorced = bool(request.form.get("divorced"))
    db.session.commit()
    return_to = request.form.get("return_to", type=int)
    return redirect(url_for("people.detail", person_id=return_to or family.spouse1_id or family.spouse2_id))


@bp.route("/families/<int:family_id>/remove-child/<int:person_id>", methods=["POST"])
def remove_child(family_id, person_id):
    FamilyChild.query.filter_by(family_id=family_id, person_id=person_id).delete()
    db.session.commit()
    return redirect(url_for("people.detail", person_id=person_id))


@bp.route("/families/<int:family_id>/remove-spouse", methods=["POST"])
def remove_spouse(family_id):
    family = Family.query.get_or_404(family_id)
    return_to = request.form.get("return_to", type=int)
    if family.spouse1_id is None or family.spouse2_id is None:
        db.session.delete(family)
    else:
        if family.spouse1_id == return_to:
            family.spouse1_id = None
        elif family.spouse2_id == return_to:
            family.spouse2_id = None
    db.session.commit()
    return redirect(url_for("people.detail", person_id=return_to))
