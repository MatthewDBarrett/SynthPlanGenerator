from datetime import datetime, timezone

from app.extensions import db


def _now():
    return datetime.now(timezone.utc)


class Person(db.Model):
    __tablename__ = "person"

    id = db.Column(db.Integer, primary_key=True)
    given_names = db.Column(db.String(200), nullable=False, default="")
    surname = db.Column(db.String(200), nullable=False, default="")
    sex = db.Column(db.String(1), nullable=False, default="U")  # M, F, U
    birth_date = db.Column(db.String(100))
    birth_place = db.Column(db.String(300))
    death_date = db.Column(db.String(100))
    death_place = db.Column(db.String(300))
    is_living = db.Column(db.Boolean, nullable=False, default=True)
    notes = db.Column(db.Text)
    profile_media_id = db.Column(db.Integer, db.ForeignKey("media.id", use_alter=True), nullable=True)
    created_at = db.Column(db.DateTime, default=_now)
    updated_at = db.Column(db.DateTime, default=_now, onupdate=_now)

    profile_media = db.relationship("Media", foreign_keys=[profile_media_id], post_update=True)

    events = db.relationship(
        "Event", back_populates="person", cascade="all, delete-orphan", foreign_keys="Event.person_id"
    )
    media_links = db.relationship("MediaLink", back_populates="person", cascade="all, delete-orphan")

    def display_name(self) -> str:
        name = f"{self.given_names} {self.surname}".strip()
        return name or "Unknown"

    def sort_key(self):
        return (self.surname or "", self.given_names or "")

    def families_as_spouse(self):
        return Family.query.filter(
            db.or_(Family.spouse1_id == self.id, Family.spouse2_id == self.id)
        ).all()

    def families_as_child(self):
        return (
            Family.query.join(FamilyChild, Family.id == FamilyChild.family_id)
            .filter(FamilyChild.person_id == self.id)
            .all()
        )

    def parents(self):
        parents = []
        for fam in self.families_as_child():
            for sp in (fam.spouse1, fam.spouse2):
                if sp:
                    parents.append(sp)
        return parents

    def spouses(self):
        spouses = []
        for fam in self.families_as_spouse():
            other = fam.other_spouse(self.id)
            if other:
                spouses.append(other)
        return spouses

    def siblings(self):
        sibs = {}
        for fam in self.families_as_child():
            for child in fam.children():
                if child.id != self.id:
                    sibs[child.id] = child
        return list(sibs.values())

    def children(self):
        kids = {}
        for fam in self.families_as_spouse():
            for child in fam.children():
                kids[child.id] = child
        return list(kids.values())

    def photos(self):
        return [ml.media for ml in self.media_links if ml.media and ml.media.media_type == "photo"]

    def documents(self):
        return [ml.media for ml in self.media_links if ml.media and ml.media.media_type == "document"]

    def __repr__(self):
        return f"<Person {self.id} {self.display_name()!r}>"


class Family(db.Model):
    __tablename__ = "family"

    id = db.Column(db.Integer, primary_key=True)
    spouse1_id = db.Column(db.Integer, db.ForeignKey("person.id"), nullable=True)
    spouse2_id = db.Column(db.Integer, db.ForeignKey("person.id"), nullable=True)
    marriage_date = db.Column(db.String(100))
    marriage_place = db.Column(db.String(300))
    divorced = db.Column(db.Boolean, nullable=False, default=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=_now)

    spouse1 = db.relationship("Person", foreign_keys=[spouse1_id])
    spouse2 = db.relationship("Person", foreign_keys=[spouse2_id])
    child_links = db.relationship(
        "FamilyChild", back_populates="family", cascade="all, delete-orphan", order_by="FamilyChild.id"
    )
    events = db.relationship(
        "Event", back_populates="family", cascade="all, delete-orphan", foreign_keys="Event.family_id"
    )
    media_links = db.relationship("MediaLink", back_populates="family", cascade="all, delete-orphan")

    def other_spouse(self, person_id):
        if self.spouse1_id == person_id:
            return self.spouse2
        if self.spouse2_id == person_id:
            return self.spouse1
        return None

    def children(self):
        return [link.person for link in self.child_links if link.person]

    def __repr__(self):
        return f"<Family {self.id}>"


class FamilyChild(db.Model):
    __tablename__ = "family_child"

    id = db.Column(db.Integer, primary_key=True)
    family_id = db.Column(db.Integer, db.ForeignKey("family.id"), nullable=False)
    person_id = db.Column(db.Integer, db.ForeignKey("person.id"), nullable=False)
    relationship_type = db.Column(db.String(20), nullable=False, default="birth")  # birth, adopted, foster, step

    family = db.relationship("Family", back_populates="child_links")
    person = db.relationship("Person")

    __table_args__ = (db.UniqueConstraint("family_id", "person_id", name="uq_family_child"),)


class Event(db.Model):
    __tablename__ = "event"

    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.Integer, db.ForeignKey("person.id"), nullable=True)
    family_id = db.Column(db.Integer, db.ForeignKey("family.id"), nullable=True)
    event_type = db.Column(db.String(50), nullable=False)
    date = db.Column(db.String(100))
    place = db.Column(db.String(300))
    description = db.Column(db.Text)

    person = db.relationship("Person", back_populates="events", foreign_keys=[person_id])
    family = db.relationship("Family", back_populates="events", foreign_keys=[family_id])


class Media(db.Model):
    __tablename__ = "media"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(300), nullable=False)
    original_filename = db.Column(db.String(300))
    mime_type = db.Column(db.String(100))
    media_type = db.Column(db.String(20), nullable=False, default="document")  # photo, document
    caption = db.Column(db.String(500))
    uploaded_at = db.Column(db.DateTime, default=_now)

    links = db.relationship("MediaLink", back_populates="media", cascade="all, delete-orphan")


class MediaLink(db.Model):
    __tablename__ = "media_link"

    id = db.Column(db.Integer, primary_key=True)
    media_id = db.Column(db.Integer, db.ForeignKey("media.id"), nullable=False)
    person_id = db.Column(db.Integer, db.ForeignKey("person.id"), nullable=True)
    family_id = db.Column(db.Integer, db.ForeignKey("family.id"), nullable=True)

    media = db.relationship("Media", back_populates="links")
    person = db.relationship("Person", back_populates="media_links", foreign_keys=[person_id])
    family = db.relationship("Family", back_populates="media_links", foreign_keys=[family_id])
