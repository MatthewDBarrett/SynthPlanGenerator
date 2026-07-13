from flask import Blueprint, Response, redirect, render_template, request, url_for

from app.extensions import db
from app.gedcom_export import export_gedcom
from app.gedcom_import import import_gedcom
from app.models import Event, Family, FamilyChild, Media, MediaLink, Person

bp = Blueprint("gedcom", __name__)


@bp.route("/gedcom")
def index():
    return render_template("gedcom.html")


@bp.route("/gedcom/export")
def export():
    content = export_gedcom()
    return Response(
        content,
        mimetype="text/plain; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=family_tree.ged"},
    )


@bp.route("/gedcom/import", methods=["POST"])
def import_file():
    file = request.files.get("file")
    if not file or not file.filename:
        return redirect(url_for("gedcom.index"))

    if request.form.get("replace"):
        MediaLink.query.delete()
        Media.query.delete()
        Event.query.delete()
        FamilyChild.query.delete()
        Family.query.delete()
        Person.query.delete()
        db.session.commit()

    text = file.read().decode("utf-8-sig", errors="replace")
    result = import_gedcom(text)

    first_person = Person.query.order_by(Person.id.asc()).first()
    if first_person:
        return redirect(url_for("tree.view", person_id=first_person.id))
    return redirect(url_for("gedcom.index"))
