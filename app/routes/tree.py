from flask import Blueprint, abort, jsonify, render_template, request

from app.models import Person

bp = Blueprint("tree", __name__)

MAX_ANCESTOR_DEPTH = 5
MAX_DESCENDANT_DEPTH = 4


def _person_summary(person: Person) -> dict:
    return {
        "id": person.id,
        "name": person.display_name(),
        "sex": person.sex,
        "birth_date": person.birth_date,
        "death_date": person.death_date,
        "is_living": person.is_living,
        "photo_url": f"/media/{person.profile_media_id}/file" if person.profile_media_id else None,
    }


def _build_ancestors(person: Person, depth: int) -> dict:
    node = _person_summary(person)
    if depth <= 0:
        return node
    parents = person.parents()
    father = next((p for p in parents if p.sex == "M"), None) or (parents[0] if parents else None)
    mother = next((p for p in parents if p.sex == "F" and p is not father), None) or (
        parents[1] if len(parents) > 1 else None
    )
    node["father"] = _build_ancestors(father, depth - 1) if father else None
    node["mother"] = _build_ancestors(mother, depth - 1) if mother else None
    return node


def _build_descendants(person: Person, depth: int, seen=None) -> dict:
    if seen is None:
        seen = set()
    node = _person_summary(person)
    node["spouses"] = [_person_summary(s) for s in person.spouses()]
    if depth <= 0 or person.id in seen:
        node["children"] = []
        return node
    seen = seen | {person.id}
    node["children"] = [
        _build_descendants(child, depth - 1, seen)
        for child in sorted(person.children(), key=Person.sort_key)
    ]
    return node


@bp.route("/tree/<int:person_id>")
def view(person_id):
    person = Person.query.get_or_404(person_id)
    return render_template("tree.html", person=person)


@bp.route("/tree/<int:person_id>/data")
def data(person_id):
    person = Person.query.get_or_404(person_id)
    if person is None:
        abort(404)

    ancestor_depth = request.args.get("ancestors", default=4, type=int)
    descendant_depth = request.args.get("descendants", default=3, type=int)
    ancestor_depth = max(0, min(ancestor_depth, MAX_ANCESTOR_DEPTH))
    descendant_depth = max(0, min(descendant_depth, MAX_DESCENDANT_DEPTH))

    root = _person_summary(person)
    root["spouses"] = [_person_summary(s) for s in person.spouses()]
    root["father"] = None
    root["mother"] = None
    parents = person.parents()
    father = next((p for p in parents if p.sex == "M"), None) or (parents[0] if parents else None)
    mother = next((p for p in parents if p.sex == "F" and p is not father), None) or (
        parents[1] if len(parents) > 1 else None
    )
    if father:
        root["father"] = _build_ancestors(father, ancestor_depth - 1)
    if mother:
        root["mother"] = _build_ancestors(mother, ancestor_depth - 1)

    root["children"] = [
        _build_descendants(child, descendant_depth - 1)
        for child in sorted(person.children(), key=Person.sort_key)
    ]

    return jsonify(root)
