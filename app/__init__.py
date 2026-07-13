import os

from flask import Flask

from app.extensions import db


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)

    os.makedirs(app.instance_path, exist_ok=True)
    upload_folder = os.path.join(app.instance_path, "uploads")
    os.makedirs(upload_folder, exist_ok=True)

    app.config.from_mapping(
        SECRET_KEY="dev",
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{os.path.join(app.instance_path, 'family_tree.sqlite3')}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        UPLOAD_FOLDER=upload_folder,
        MAX_CONTENT_LENGTH=25 * 1024 * 1024,  # 25MB upload cap
    )

    if config:
        app.config.update(config)

    db.init_app(app)

    from app import models  # noqa: F401  (register models with SQLAlchemy)

    with app.app_context():
        db.create_all()

    from app.routes.main import bp as main_bp
    from app.routes.people import bp as people_bp
    from app.routes.families import bp as families_bp
    from app.routes.tree import bp as tree_bp
    from app.routes.media import bp as media_bp
    from app.routes.gedcom import bp as gedcom_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(people_bp)
    app.register_blueprint(families_bp)
    app.register_blueprint(tree_bp)
    app.register_blueprint(media_bp)
    app.register_blueprint(gedcom_bp)

    @app.template_filter("display_name")
    def display_name_filter(person):
        return person.display_name() if person else "Unknown"

    return app
