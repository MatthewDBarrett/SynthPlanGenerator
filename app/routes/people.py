from flask import Blueprint, jsonify, redirect, render_template, request, url_for

from app.extensions import db
from app.models import Event, Family, FamilyChild, MediaLink, Person

bp = Blueprint("people", __name__)


def _person_from_form(person: Person, form) -> None:
    person.given_names = form.get("given_names", "").strip()
    person.surname = form.get("surname", "").strip()
    person.sex = form.get("sex", "U") or "U"
    person.birth_date = form.get("birth_date", "").strip()
    person.birth_place = form.get("birth_place", "").strip()
    person.death_date = form.get("death_date", "").strip()
    person.death_place = form.get("death_place", "").strip()
    person.is_living = bool(form.get("is_living"))
    person.notes = form.get("notes", "").strip()


@bp.route("/people")
def list_people():
    q = request.args.get("q", "").strip()
    query = Person.query
    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(Person.given_names.ilike(like), Person.surname.ilike(like))
        )
    people = sorted(query.all(), key=Person.sort_key)
    return render_template("people_list.html", people=people, q=q)


@bp.route("/people/new", methods=["GET", "POST"])
def new_person():
    if request.method == "POST":
        person = Person()
        _person_from_form(person, request.form)
        db.session.add(person)
        db.session.commit()
        return redirect(url_for("people.detail", person_id=person.id))
    return render_template("person_form.html", person=None)


@bp.route("/people/<int:person_id>")
def detail(person_id):
    person = Person.query.get_or_404(person_id)
    events = (
        Event.query.filter_by(person_id=person.id).order_by(Event.date).all()
    )
    return render_template(
        "person_detail.html",
        person=person,
        parents=person.parents(),
        spouses_families=[(f, f.other_spouse(person.id)) for f in person.families_as_spouse()],
        children=sorted(person.children(), key=Person.sort_key),
        siblings=sorted(person.siblings(), key=Person.sort_key),
        events=events,
        photos=person.photos(),
        documents=person.documents(),
    )


@bp.route("/people/<int:person_id>/edit", methods=["GET", "POST"])
def edit_person(person_id):
    person = Person.query.get_or_404(person_id)
    if request.method == "POST":
        _person_from_form(person, request.form)
        db.session.commit()
        return redirect(url_for("people.detail", person_id=person.id))
    return render_template("person_form.html", person=person)


@bp.route("/people/<int:person_id>/delete", methods=["POST"])
def delete_person(person_id):
    person = Person.query.get_or_404(person_id)

    # Detach from any families rather than cascading, so relatives stay intact.
    FamilyChild.query.filter_by(person_id=person.id).delete()
    for fam in Family.query.filter(
        db.or_(Family.spouse1_id == person.id, Family.spouse2_id == person.id)
    ).all():
        if fam.spouse1_id == person.id:
            fam.spouse1_id = None
        if fam.spouse2_id == person.id:
            fam.spouse2_id = None
        if fam.spouse1_id is None and fam.spouse2_id is None and not fam.child_links:
            db.session.delete(fam)

    MediaLink.query.filter_by(person_id=person.id).delete()
    Event.query.filter_by(person_id=person.id).delete()

    db.session.delete(person)
    db.session.commit()
    return redirect(url_for("people.list_people"))


@bp.route("/api/people/search")
def api_search():
    q = request.args.get("q", "").strip()
    exclude = request.args.get("exclude", type=int)
    if not q:
        return jsonify([])
    like = f"%{q}%"
    query = Person.query.filter(
        db.or_(Person.given_names.ilike(like), Person.surname.ilike(like))
    )
    if exclude:
        query = query.filter(Person.id != exclude)
    results = [
        {
            "id": p.id,
            "name": p.display_name(),
            "birth_date": p.birth_date,
            "sex": p.sex,
        }
        for p in query.order_by(Person.surname, Person.given_names).limit(20).all()
    ]
    return jsonify(results)


@bp.route("/people/<int:person_id>/events", methods=["POST"])
def add_event(person_id):
    person = Person.query.get_or_404(person_id)
    event = Event(
        person_id=person.id,
        event_type=request.form.get("event_type", "").strip() or "Event",
        date=request.form.get("date", "").strip(),
        place=request.form.get("place", "").strip(),
        description=request.form.get("description", "").strip(),
    )
    db.session.add(event)
    db.session.commit()
    return redirect(url_for("people.detail", person_id=person.id))


@bp.route("/events/<int:event_id>/delete", methods=["POST"])
def delete_event(event_id):
    event = Event.query.get_or_404(event_id)
    person_id = event.person_id
    db.session.delete(event)
    db.session.commit()
    return redirect(url_for("people.detail", person_id=person_id))
