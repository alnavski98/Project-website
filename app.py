from datetime import datetime
from flask import Flask, flash, redirect, render_template, request, url_for


app = Flask(__name__)

@app.context_processor
def inject_current_year():
    return {
        "current_year": datetime.now().year
    }

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/projects")
def projects():
    project_data = [
        {
            "title": "LED Baton",
            "slug": "led-baton",
            "summary": "An embedded LED system using an ATmega328P.",
            "thumbnail": "led-baton.jpg",
        }
    ]

    return render_template(
        "projects.html",
        projects=project_data,
    )

@app.route("/projects/<slug>")
def project_detail(slug):
    return render_template(
        "project_detail.html",
        slug=slug,
    )

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        subject = request.form.get("subject", "").strip()
        message = request.form.get("message", "").strip()

        if not all([name, email, subject, message]):
            flash("Please complete all fields.", "error")
            return render_template("contact.html")

        # Email sending or database storage can be added later.

        flash("Your message has been received.", "success")
        return redirect(url_for("contact"))

    return render_template("contact.html")
if __name__ == "__main__":
    app.run(debug=True)