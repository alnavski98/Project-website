from flask import Flask, render_template

app = Flask(__name__)


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

@app.route("/contact")
def contact():
    return render_template("contact.html")

if __name__ == "__main__":
    app.run(debug=True)