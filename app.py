import hmac
import os
import re
from datetime import datetime
from functools import wraps
from pathlib import Path

import bleach
import markdown

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from werkzeug.security import (
    check_password_hash,
    generate_password_hash,
)

from extensions import db
from models import Project


app = Flask(
    __name__,
    instance_relative_config=True,
)

app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    "temporary-development-secret-key",
)


# ----------------------------------------------------------------------
# Database configuration
# ----------------------------------------------------------------------

database_path = (
    Path(app.instance_path)
    / "portfolio.db"
)

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"sqlite:///{database_path.as_posix()}"
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


# ----------------------------------------------------------------------
# Administrator credentials
# ----------------------------------------------------------------------
#
# These should be set as environment variables before starting Flask.
#
# Development defaults:
#
# Username: admin
# Password: change-this-password
#
# Do not use the default credentials if the site is exposed publicly.
# ----------------------------------------------------------------------

app.config["ADMIN_USERNAME"] = os.environ.get(
    "ADMIN_USERNAME",
    "admin",
)

app.config["ADMIN_PASSWORD_HASH"] = generate_password_hash(
    os.environ.get(
        "ADMIN_PASSWORD",
        "change-this-password",
    )
)


# ----------------------------------------------------------------------
# Application directories and database initialization
# ----------------------------------------------------------------------

# Create the instance folder before SQLite attempts to create its file.
Path(app.instance_path).mkdir(
    parents=True,
    exist_ok=True,
)

db.init_app(app)


# Markdown files for the project pages are stored in:
#
# content/projects/<project-slug>.md

PROJECT_CONTENT_DIRECTORY = (
    Path(app.root_path)
    / "content"
    / "projects"
)

PROJECT_CONTENT_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True,
)


# Automatically create portfolio.db and any missing database tables
# whenever the Flask application starts.
with app.app_context():
    db.create_all()


# ----------------------------------------------------------------------
# Authentication helpers
# ----------------------------------------------------------------------

def login_required(view_function):
    """
    Require an authenticated administrator session before opening a
    route.
    """

    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if not session.get("admin_logged_in"):
            flash(
                "Log in to manage projects.",
                "error",
            )

            return redirect(
                url_for(
                    "login",
                    next=request.path,
                )
            )

        return view_function(
            *args,
            **kwargs,
        )

    return wrapped_view


def is_safe_redirect_target(
    target: str | None,
) -> bool:
    """
    Only permit redirects to local application paths.
    """

    return bool(
        target
        and target.startswith("/")
        and not target.startswith("//")
    )


# ----------------------------------------------------------------------
# Project helper functions
# ----------------------------------------------------------------------

def slugify(value: str) -> str:
    """
    Convert a project title or manually entered slug into a URL-safe
    string.

    Example:
        LED Baton Project -> led-baton-project
    """

    value = value.strip().lower()

    value = re.sub(
        r"[^a-z0-9]+",
        "-",
        value,
    )

    return value.strip("-")


def get_project_or_404(
    project_id: int,
) -> Project:
    """
    Retrieve a project from the database or return a 404 page.
    """

    project = db.session.get(
        Project,
        project_id,
    )

    if project is None:
        abort(404)

    return project


def read_project_markdown(
    project: Project,
) -> str:
    """
    Read the Markdown content belonging to a project.
    """

    markdown_path = (
        PROJECT_CONTENT_DIRECTORY
        / project.markdown_filename
    )

    if not markdown_path.is_file():
        return ""

    return markdown_path.read_text(
        encoding="utf-8",
    )


def write_project_markdown(
    filename: str,
    content: str,
) -> None:
    """
    Create or overwrite a project's Markdown file.
    """

    markdown_path = (
        PROJECT_CONTENT_DIRECTORY
        / filename
    )

    markdown_path.write_text(
        content,
        encoding="utf-8",
    )


def delete_project_markdown(
    filename: str,
) -> None:
    """
    Delete a project's Markdown file if it exists.
    """

    markdown_path = (
        PROJECT_CONTENT_DIRECTORY
        / filename
    )

    if markdown_path.is_file():
        markdown_path.unlink()


def project_form_data() -> dict:
    """
    Read and normalize data submitted from the project form.
    """

    title = request.form.get(
        "title",
        "",
    ).strip()

    requested_slug = request.form.get(
        "slug",
        "",
    ).strip()

    slug = slugify(
        requested_slug or title
    )

    return {
        "title": title,
        "slug": slug,
        "summary": request.form.get(
            "summary",
            "",
        ).strip(),
        "category": request.form.get(
            "category",
            "",
        ).strip() or None,
        "thumbnail": request.form.get(
            "thumbnail",
            "",
        ).strip() or None,
        "content": request.form.get(
            "content",
            "",
        ).strip(),
        "published": (
            request.form.get("published")
            == "on"
        ),
        "featured": (
            request.form.get("featured")
            == "on"
        ),
        "display_order": request.form.get(
            "display_order",
            "0",
        ).strip(),
    }


def validate_project_form(
    data: dict,
    project_id: int | None = None,
) -> list[str]:
    """
    Validate submitted project information.

    project_id is supplied while editing so that the existing project's
    slug does not conflict with itself.
    """

    errors = []

    if not data["title"]:
        errors.append(
            "Title is required."
        )

    if not data["slug"]:
        errors.append(
            "Slug is required."
        )

    if not data["summary"]:
        errors.append(
            "Summary is required."
        )

    if not data["content"]:
        errors.append(
            "Project content is required."
        )

    try:
        data["display_order"] = int(
            data["display_order"] or 0
        )

    except ValueError:
        errors.append(
            "Display order must be a whole number."
        )

        data["display_order"] = 0

    if data["slug"]:
        statement = (
            db.select(Project)
            .where(
                Project.slug
                == data["slug"]
            )
        )

        if project_id is not None:
            statement = statement.where(
                Project.id != project_id
            )

        existing_project = (
            db.session.execute(statement)
            .scalar_one_or_none()
        )

        if existing_project is not None:
            errors.append(
                "Another project already uses that slug."
            )

    return errors


# ----------------------------------------------------------------------
# Shared template values
# ----------------------------------------------------------------------

@app.context_processor
def inject_current_year():
    return {
        "current_year": datetime.now().year
    }


# ----------------------------------------------------------------------
# Public routes
# ----------------------------------------------------------------------

@app.route("/")
def home():
    statement = (
        db.select(Project)
        .where(
            Project.published.is_(True),
            Project.featured.is_(True),
        )
        .order_by(
            Project.display_order.asc(),
            Project.created_at.desc(),
        )
        .limit(3)
    )

    featured_projects = (
        db.session.execute(statement)
        .scalars()
        .all()
    )

    return render_template(
        "index.html",
        projects=featured_projects,
    )


@app.route("/projects")
def projects():
    statement = (
        db.select(Project)
        .where(
            Project.published.is_(True)
        )
        .order_by(
            Project.display_order.asc(),
            Project.created_at.desc(),
        )
    )

    project_list = (
        db.session.execute(statement)
        .scalars()
        .all()
    )

    return render_template(
        "projects.html",
        projects=project_list,
    )


@app.route("/projects/<string:slug>")
def project_detail(
    slug: str,
):
    statement = (
        db.select(Project)
        .where(
            Project.slug == slug,
            Project.published.is_(True),
        )
    )

    project = (
        db.session.execute(statement)
        .scalar_one_or_none()
    )

    if project is None:
        abort(404)

    markdown_source = read_project_markdown(
        project
    )

    if not markdown_source:
        abort(404)

    rendered_html = markdown.markdown(
        markdown_source,
        extensions=[
            "fenced_code",
            "tables",
            "toc",
        ],
    )

    allowed_tags = set(
        bleach.sanitizer.ALLOWED_TAGS
    ).union(
        {
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "p",
            "pre",
            "code",
            "blockquote",
            "ul",
            "ol",
            "li",
            "table",
            "thead",
            "tbody",
            "tr",
            "th",
            "td",
            "img",
            "hr",
            "br",
        }
    )

    project_content = bleach.clean(
        rendered_html,
        tags=allowed_tags,
        attributes={
            "a": [
                "href",
                "title",
            ],
            "img": [
                "src",
                "alt",
                "title",
            ],
            "code": [
                "class",
            ],
        },
        protocols=[
            "http",
            "https",
            "mailto",
        ],
        strip=True,
    )

    return render_template(
        "project_detail.html",
        project=project,
        project_content=project_content,
    )


@app.route("/about")
def about():
    return render_template(
        "about.html"
    )


@app.route(
    "/contact",
    methods=[
        "GET",
        "POST",
    ],
)
def contact():
    if request.method == "POST":
        name = request.form.get(
            "name",
            "",
        ).strip()

        email = request.form.get(
            "email",
            "",
        ).strip()

        subject = request.form.get(
            "subject",
            "",
        ).strip()

        message = request.form.get(
            "message",
            "",
        ).strip()

        if not all(
            [
                name,
                email,
                subject,
                message,
            ]
        ):
            flash(
                "Please complete all fields.",
                "error",
            )

            return render_template(
                "contact.html"
            )

        # Email sending can be added here later.

        flash(
            "Your message has been received.",
            "success",
        )

        return redirect(
            url_for("contact")
        )

    return render_template(
        "contact.html"
    )


# ----------------------------------------------------------------------
# Authentication routes
# ----------------------------------------------------------------------

@app.route(
    "/login",
    methods=[
        "GET",
        "POST",
    ],
)
def login():
    """
    Display the login form and create an authenticated administrator
    session.
    """

    if session.get("admin_logged_in"):
        return redirect(
            url_for("admin_projects")
        )

    next_page = (
        request.args.get("next")
        or request.form.get("next")
    )

    if request.method == "POST":
        username = request.form.get(
            "username",
            "",
        ).strip()

        password = request.form.get(
            "password",
            "",
        )

        username_matches = hmac.compare_digest(
            username,
            app.config["ADMIN_USERNAME"],
        )

        password_matches = check_password_hash(
            app.config[
                "ADMIN_PASSWORD_HASH"
            ],
            password,
        )

        if (
            username_matches
            and password_matches
        ):
            session.clear()

            session["admin_logged_in"] = True
            session["admin_username"] = username

            flash(
                "You are now logged in.",
                "success",
            )

            if is_safe_redirect_target(
                next_page
            ):
                return redirect(next_page)

            return redirect(
                url_for("admin_projects")
            )

        flash(
            "Incorrect username or password.",
            "error",
        )

    return render_template(
        "auth/login.html",
        next_page=next_page or "",
    )


@app.route(
    "/logout",
    methods=[
        "POST",
    ],
)
def logout():
    """
    Clear the administrator session.
    """

    session.clear()

    flash(
        "You have been logged out.",
        "success",
    )

    return redirect(
        url_for("home")
    )


# ----------------------------------------------------------------------
# Project administration routes
# ----------------------------------------------------------------------

@app.route("/admin/projects")
@login_required
def admin_projects():
    """
    Display all projects, including unpublished drafts.
    """

    statement = (
        db.select(Project)
        .order_by(
            Project.display_order.asc(),
            Project.created_at.desc(),
        )
    )

    project_list = (
        db.session.execute(statement)
        .scalars()
        .all()
    )

    return render_template(
        "admin/projects.html",
        projects=project_list,
    )


@app.route(
    "/admin/projects/add",
    methods=[
        "GET",
        "POST",
    ],
)
@login_required
def add_project():
    """
    Add a project through the browser.
    """

    if request.method == "POST":
        form_data = project_form_data()

        errors = validate_project_form(
            form_data
        )

        if not errors:
            markdown_filename = (
                f"{form_data['slug']}.md"
            )

            project = Project(
                title=form_data["title"],
                slug=form_data["slug"],
                summary=form_data["summary"],
                category=form_data["category"],
                thumbnail=form_data["thumbnail"],
                markdown_filename=markdown_filename,
                published=form_data["published"],
                featured=form_data["featured"],
                display_order=form_data[
                    "display_order"
                ],
            )

            try:
                write_project_markdown(
                    markdown_filename,
                    form_data["content"],
                )

                db.session.add(project)
                db.session.commit()

            except OSError:
                db.session.rollback()

                delete_project_markdown(
                    markdown_filename
                )

                flash(
                    "The project content file could not be written.",
                    "error",
                )

            else:
                flash(
                    "Project added successfully.",
                    "success",
                )

                return redirect(
                    url_for("admin_projects")
                )

        for error in errors:
            flash(
                error,
                "error",
            )

        return render_template(
            "admin/project_form.html",
            page_title="Add project",
            submit_label="Add project",
            project=None,
            form_data=form_data,
        )

    return render_template(
        "admin/project_form.html",
        page_title="Add project",
        submit_label="Add project",
        project=None,
        form_data=None,
    )


@app.route(
    "/admin/projects/<int:project_id>/edit",
    methods=[
        "GET",
        "POST",
    ],
)
@login_required
def edit_project(
    project_id: int,
):
    """
    Edit an existing project through the browser.
    """

    project = get_project_or_404(
        project_id
    )

    if request.method == "POST":
        form_data = project_form_data()

        errors = validate_project_form(
            form_data,
            project_id=project.id,
        )

        if not errors:
            old_markdown_filename = (
                project.markdown_filename
            )

            new_markdown_filename = (
                f"{form_data['slug']}.md"
            )

            project.title = form_data[
                "title"
            ]

            project.slug = form_data[
                "slug"
            ]

            project.summary = form_data[
                "summary"
            ]

            project.category = form_data[
                "category"
            ]

            project.thumbnail = form_data[
                "thumbnail"
            ]

            project.markdown_filename = (
                new_markdown_filename
            )

            project.published = form_data[
                "published"
            ]

            project.featured = form_data[
                "featured"
            ]

            project.display_order = form_data[
                "display_order"
            ]

            try:
                write_project_markdown(
                    new_markdown_filename,
                    form_data["content"],
                )

                db.session.commit()

            except OSError:
                db.session.rollback()

                flash(
                    "The project content file could not be written.",
                    "error",
                )

            else:
                if (
                    old_markdown_filename
                    != new_markdown_filename
                ):
                    delete_project_markdown(
                        old_markdown_filename
                    )

                flash(
                    "Project updated successfully.",
                    "success",
                )

                return redirect(
                    url_for("admin_projects")
                )

        for error in errors:
            flash(
                error,
                "error",
            )

        return render_template(
            "admin/project_form.html",
            page_title="Edit project",
            submit_label="Save changes",
            project=project,
            form_data=form_data,
        )

    form_data = {
        "title": project.title,
        "slug": project.slug,
        "summary": project.summary,
        "category": (
            project.category or ""
        ),
        "thumbnail": (
            project.thumbnail or ""
        ),
        "content": read_project_markdown(
            project
        ),
        "published": project.published,
        "featured": project.featured,
        "display_order": (
            project.display_order
        ),
    }

    return render_template(
        "admin/project_form.html",
        page_title="Edit project",
        submit_label="Save changes",
        project=project,
        form_data=form_data,
    )


@app.route(
    "/admin/projects/<int:project_id>/delete",
    methods=[
        "POST",
    ],
)
@login_required
def delete_project(
    project_id: int,
):
    """
    Delete a project and its Markdown file.
    """

    project = get_project_or_404(
        project_id
    )

    markdown_filename = (
        project.markdown_filename
    )

    db.session.delete(project)
    db.session.commit()

    delete_project_markdown(
        markdown_filename
    )

    flash(
        "Project deleted successfully.",
        "success",
    )

    return redirect(
        url_for("admin_projects")
    )


# ----------------------------------------------------------------------
# Development server
# ----------------------------------------------------------------------

if __name__ == "__main__":
    app.run(
        debug=True
    )