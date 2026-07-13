from flask import Blueprint, Response, current_app, flash, redirect, render_template, request, url_for

from app.extensions import db
from app.gedcom_export import export_gedcom
from app.gedcom_import import import_gedcom
from app.models import Event, Family, FamilyChild, Media, MediaLink, Person

bp = Blueprint("gedcom", __name__)


def _decode_gedcom(raw: bytes) -> str:
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16", errors="replace")
    if raw.startswith(b"\xff\xfe\x00\x00") or raw.startswith(b"\x00\x00\xfe\xff"):
        return raw.decode("utf-32", errors="replace")
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        # Older exports (GEDCOM 5.5 ANSEL/ANSI) aren't valid UTF-8. cp1252
        # accepts any byte value, so this never raises.
        return raw.decode("cp1252", errors="replace")


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
        flash("Choose a .ged file to import.", "error")
        return redirect(url_for("gedcom.index"))

    try:
        raw = file.read()
        text = _decode_gedcom(raw)

        if request.form.get("replace"):
            MediaLink.query.delete()
            Media.query.delete()
            Event.query.delete()
            FamilyChild.query.delete()
            Family.query.delete()
            Person.query.delete()
            db.session.commit()

        result = import_gedcom(text)
    except Exception:
        db.session.rollback()
        current_app.logger.exception("GEDCOM import failed")
        flash(
            "That GEDCOM file couldn't be imported -- it may be malformed or use an "
            "unsupported format. Check the server logs for details.",
            "error",
        )
        return redirect(url_for("gedcom.index"))

    flash(
        f"Imported {result['people']} people, {result['families']} families, "
        f"{result['child_links']} parent-child links.",
        "success",
    )

    first_person = Person.query.order_by(Person.id.asc()).first()
    if first_person:
        return redirect(url_for("tree.view", person_id=first_person.id))
    return redirect(url_for("gedcom.index"))
