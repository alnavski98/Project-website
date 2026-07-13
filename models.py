from datetime import datetime, timezone

from extensions import db


class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    title = db.Column(
        db.String(150),
        nullable=False,
    )

    slug = db.Column(
        db.String(150),
        unique=True,
        nullable=False,
        index=True,
    )

    summary = db.Column(
        db.Text,
        nullable=False,
    )

    category = db.Column(
        db.String(80),
        nullable=True,
    )

    thumbnail = db.Column(
        db.String(255),
        nullable=True,
    )

    markdown_filename = db.Column(
        db.String(255),
        nullable=False,
    )

    published = db.Column(
        db.Boolean,
        default=False,
        nullable=False,
    )

    featured = db.Column(
        db.Boolean,
        default=False,
        nullable=False,
    )

    display_order = db.Column(
        db.Integer,
        default=0,
        nullable=False,
    )

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Project {self.title}>"