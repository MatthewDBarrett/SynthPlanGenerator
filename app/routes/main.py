from flask import Blueprint, redirect, render_template, url_for

from app.models import Person

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    first_person = Person.query.order_by(Person.id.asc()).first()
    if first_person is None:
        return render_template("welcome.html")
    return redirect(url_for("tree.view", person_id=first_person.id))
