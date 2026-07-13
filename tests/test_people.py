from app.extensions import db
from app.models import Person


def test_welcome_page_when_empty(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Welcome to your family tree" in resp.data


def test_create_person_and_redirect_home(client, app):
    resp = client.post(
        "/people/new",
        data={"given_names": "Ada", "surname": "Lovelace", "sex": "F"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Ada Lovelace" in resp.data

    resp = client.get("/")
    assert resp.status_code == 302
    assert "/tree/" in resp.headers["Location"]


def test_edit_and_delete_person(client, app):
    client.post("/people/new", data={"given_names": "Grace", "surname": "Hopper", "sex": "F"})
    with app.app_context():
        person = Person.query.filter_by(given_names="Grace").one()
        pid = person.id

    resp = client.post(
        f"/people/{pid}/edit",
        data={"given_names": "Grace", "surname": "Hopper-Murray", "sex": "F"},
        follow_redirects=True,
    )
    assert b"Hopper-Murray" in resp.data

    client.post(f"/people/{pid}/delete", follow_redirects=True)
    with app.app_context():
        assert db.session.get(Person, pid) is None


def test_add_parent_spouse_child_relationships(client, app):
    client.post("/people/new", data={"given_names": "Child", "surname": "One", "sex": "M"})
    with app.app_context():
        child = Person.query.filter_by(given_names="Child").one()
        child_id = child.id

    client.post(
        f"/people/{child_id}/parents",
        data={
            "relation": "father",
            "mode": "new",
            "given_names": "Father",
            "surname": "One",
            "sex": "M",
        },
    )
    client.post(
        f"/people/{child_id}/parents",
        data={
            "relation": "mother",
            "mode": "new",
            "given_names": "Mother",
            "surname": "One",
            "sex": "F",
        },
    )

    with app.app_context():
        child = db.session.get(Person, child_id)
        parent_names = sorted(p.display_name() for p in child.parents())
        assert parent_names == ["Father One", "Mother One"]
        father = Person.query.filter_by(given_names="Father").one()

    resp = client.post(
        f"/people/{father.id}/spouses",
        data={"mode": "existing", "existing_id": str(Person.query.filter_by(given_names="Mother").first().id)},
    )
    assert resp.status_code == 302

    with app.app_context():
        father = Person.query.filter_by(given_names="Father").one()
        assert len(father.spouses()) == 1
        assert father.spouses()[0].given_names == "Mother"

    client.post(
        f"/people/{father.id}/children",
        data={"mode": "new", "given_names": "Sibling", "surname": "One", "sex": "F"},
    )
    with app.app_context():
        father = Person.query.filter_by(given_names="Father").one()
        child_names = sorted(c.given_names for c in father.children())
        assert child_names == ["Child", "Sibling"]


def test_person_search_api(client):
    client.post("/people/new", data={"given_names": "Alan", "surname": "Turing", "sex": "M"})
    resp = client.get("/api/people/search?q=Tur")
    assert resp.status_code == 200
    results = resp.get_json()
    assert len(results) == 1
    assert results[0]["name"] == "Alan Turing"
