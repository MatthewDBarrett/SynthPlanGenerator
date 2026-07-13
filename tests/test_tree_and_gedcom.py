import io

from app.gedcom_import import import_gedcom
from app.models import Family, FamilyChild, Person


def _make_family(app, client):
    client.post("/people/new", data={"given_names": "Kid", "surname": "Smith", "sex": "M", "birth_date": "1990"})
    with app.app_context():
        kid = Person.query.filter_by(given_names="Kid").one()
        kid_id = kid.id

    client.post(
        f"/people/{kid_id}/parents",
        data={"relation": "father", "mode": "new", "given_names": "Dad", "surname": "Smith", "sex": "M", "birth_date": "1960"},
    )
    client.post(
        f"/people/{kid_id}/parents",
        data={"relation": "mother", "mode": "new", "given_names": "Mom", "surname": "Jones", "sex": "F", "birth_date": "1962"},
    )
    with app.app_context():
        dad = Person.query.filter_by(given_names="Dad").one()
        dad_id = dad.id
    client.post(
        f"/people/{dad_id}/children",
        data={"mode": "new", "given_names": "Sis", "surname": "Smith", "sex": "F", "birth_date": "1993"},
    )
    return kid_id


def test_tree_view_and_data_endpoint(client, app):
    kid_id = _make_family(app, client)

    resp = client.get(f"/tree/{kid_id}")
    assert resp.status_code == 200
    assert b"tree-container" in resp.data

    resp = client.get(f"/tree/{kid_id}/data")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["name"] == "Kid Smith"
    assert data["father"]["name"] == "Dad Smith"
    assert data["mother"]["name"] == "Mom Jones"


def test_gedcom_export_then_import_roundtrip(client, app):
    _make_family(app, client)

    resp = client.get("/gedcom/export")
    assert resp.status_code == 200
    ged_text = resp.data.decode("utf-8")
    assert "0 HEAD" in ged_text
    assert "INDI" in ged_text
    assert "0 TRLR" in ged_text

    with app.app_context():
        original_count = Person.query.count()
        assert original_count == 4  # Kid, Dad, Mom, Sis

    import io

    resp = client.post(
        "/gedcom/import",
        data={
            "file": (io.BytesIO(ged_text.encode("utf-8")), "export.ged"),
            "replace": "on",
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert resp.status_code == 200

    with app.app_context():
        assert Person.query.count() == original_count
        kid = Person.query.filter_by(given_names="Kid").one()
        assert kid.parents()
        assert {p.given_names for p in kid.parents()} == {"Dad", "Mom"}


def test_import_survives_malformed_lines(app):
    text = (
        "0 HEAD\n"
        "1 CHAR UTF-8\n"
        "0 @I1@ INDI\n"
        "1 NAME John /Doe/\n"
        "1 SEX M\n"
        "this line has no level number and should be skipped\n"
        "1 BIRT\n"
        "2 DATE 1 JAN 1900\n"
        "0 TRLR\n"
    )
    with app.app_context():
        result = import_gedcom(text)
        assert result["people"] == 1
        person = Person.query.filter_by(given_names="John").one()
        assert person.birth_date == "1 JAN 1900"


def test_import_joins_conc_cont_note_lines(app):
    text = (
        "0 HEAD\n"
        "1 CHAR UTF-8\n"
        "0 @I1@ INDI\n"
        "1 NAME Jane /Doe/\n"
        "1 NOTE This is a long note that got split\n"
        "2 CONC  across multiple lines\n"
        "2 CONT and continues on a new line too.\n"
        "0 TRLR\n"
    )
    with app.app_context():
        import_gedcom(text)
        person = Person.query.filter_by(given_names="Jane").one()
        assert "split across multiple lines" in person.notes
        assert "continues on a new line too" in person.notes


def test_import_utf16_encoded_file_via_route(client, app):
    ged_text = (
        "0 HEAD\n1 CHAR UTF-8\n"
        "0 @I1@ INDI\n1 NAME Ute /Sixteen/\n1 SEX F\n"
        "0 TRLR\n"
    )
    utf16_bytes = ged_text.encode("utf-16")  # includes BOM

    resp = client.post(
        "/gedcom/import",
        data={"file": (io.BytesIO(utf16_bytes), "export.ged")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with app.app_context():
        assert Person.query.filter_by(given_names="Ute").count() == 1


def test_import_dedupes_duplicate_child_pointers(app):
    text = (
        "0 HEAD\n"
        "1 CHAR UTF-8\n"
        "0 @I1@ INDI\n1 NAME Parent /One/\n1 FAMS @F1@\n"
        "0 @I2@ INDI\n1 NAME Kid /One/\n1 FAMC @F1@\n"
        "0 @F1@ FAM\n1 HUSB @I1@\n1 CHIL @I2@\n1 CHIL @I2@\n"
        "0 TRLR\n"
    )
    with app.app_context():
        result = import_gedcom(text)
        assert result["child_links"] == 1
        family = Family.query.one()
        assert FamilyChild.query.filter_by(family_id=family.id).count() == 1


def test_import_bad_file_shows_friendly_error_not_500(client, monkeypatch):
    import app.routes.gedcom as gedcom_route

    def boom(text):
        raise RuntimeError("simulated parser crash")

    monkeypatch.setattr(gedcom_route, "import_gedcom", boom)

    resp = client.post(
        "/gedcom/import",
        data={"file": (io.BytesIO(b"0 HEAD\n0 TRLR\n"), "export.ged")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"couldn&#39;t be imported" in resp.data or b"couldn't be imported" in resp.data
