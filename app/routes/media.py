import os
import uuid

from flask import Blueprint, current_app, redirect, request, send_from_directory, url_for
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import Media, MediaLink, Person

bp = Blueprint("media", __name__)

IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp", "bmp"}


def _media_type_for(filename: str, mime_type: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext in IMAGE_EXTENSIONS or (mime_type or "").startswith("image/"):
        return "photo"
    return "document"


@bp.route("/people/<int:person_id>/media", methods=["POST"])
def upload(person_id):
    person = Person.query.get_or_404(person_id)
    file = request.files.get("file")
    if not file or not file.filename:
        return redirect(url_for("people.detail", person_id=person.id))

    original_name = secure_filename(file.filename)
    ext = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""
    stored_name = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex
    dest_path = os.path.join(current_app.config["UPLOAD_FOLDER"], stored_name)
    file.save(dest_path)

    media = Media(
        filename=stored_name,
        original_filename=original_name,
        mime_type=file.mimetype,
        media_type=_media_type_for(original_name, file.mimetype),
        caption=request.form.get("caption", "").strip(),
    )
    db.session.add(media)
    db.session.flush()

    db.session.add(MediaLink(media_id=media.id, person_id=person.id))

    if media.media_type == "photo" and person.profile_media_id is None:
        person.profile_media_id = media.id

    db.session.commit()
    return redirect(url_for("people.detail", person_id=person.id))


@bp.route("/media/<int:media_id>/file")
def file(media_id):
    media = Media.query.get_or_404(media_id)
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], media.filename)


@bp.route("/media/<int:media_id>/set-profile/<int:person_id>", methods=["POST"])
def set_profile(media_id, person_id):
    media = Media.query.get_or_404(media_id)
    person = Person.query.get_or_404(person_id)
    if media.media_type == "photo":
        person.profile_media_id = media.id
        db.session.commit()
    return redirect(url_for("people.detail", person_id=person.id))


@bp.route("/media/<int:media_id>/delete", methods=["POST"])
def delete(media_id):
    media = Media.query.get_or_404(media_id)
    person_id = request.form.get("person_id", type=int)

    for person in Person.query.filter_by(profile_media_id=media.id).all():
        person.profile_media_id = None

    path = os.path.join(current_app.config["UPLOAD_FOLDER"], media.filename)
    if os.path.exists(path):
        os.remove(path)

    db.session.delete(media)
    db.session.commit()
    if person_id:
        return redirect(url_for("people.detail", person_id=person_id))
    return redirect(url_for("people.list_people"))
