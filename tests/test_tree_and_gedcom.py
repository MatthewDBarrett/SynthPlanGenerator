from app.models import Person


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
