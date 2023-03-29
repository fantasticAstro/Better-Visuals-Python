import os
import json
import importlib
from flask import Flask, redirect, url_for, render_template, session, request
from flask_dance.contrib.google import make_google_blueprint, google
from utils.db_util import init_db, db
import logging
import traceback


# Flask app + Google OAuth setup
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY")
app.config["GOOGLE_OAUTH_CLIENT_ID"] = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
app.config["GOOGLE_OAUTH_CLIENT_SECRET"] = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")

google_bp = make_google_blueprint(
    client_id=app.config["GOOGLE_OAUTH_CLIENT_ID"],
    client_secret=app.config["GOOGLE_OAUTH_CLIENT_SECRET"],
    scope=["profile", "email"],
    offline=True,
)
app.register_blueprint(google_bp, url_prefix="/login")

# Configure Flask's built-in logger
app.logger.setLevel(logging.INFO)
handler = logging.FileHandler("user.log")
handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
app.logger.addHandler(handler)

# Initialize the database
init_db(app)

# Create the database tables
with app.app_context():
    db.create_all()

# Read the list of dashboards from the JSON file
with open("dashboards_config.json", "r") as f:
    dashboards_data = json.load(f)
    dashboard_data_list = dashboards_data["dashboards"]

# Dynamically import and create Dash apps for all dashboards
for dashboard_metadata in dashboard_data_list:
    dashboard_file = dashboard_metadata["file"]
    dashboard_module = importlib.import_module(f"dashboards.{dashboard_file}")
    create_dash_app = getattr(dashboard_module, "create_dash_app")
    create_dash_app(app, google, dashboard_metadata)


# Create Home Page (requires login)
@app.route("/")
def index():
    if not google.authorized:
        return redirect(url_for("welcome"))

    resp = google.get("/oauth2/v1/userinfo")
    assert resp.ok, resp.text
    user_info = resp.json()
    session['email'] = user_info['email']
    session['given_name'] = user_info['given_name']

    app.logger.info(f"User logged in: email={session['email']}, name={session['given_name']}")
    return render_template("index.html", given_name=user_info['given_name'], dashboards=dashboard_data_list)


# Create Welcome Page (prompts login)
@app.route("/welcome")
def welcome():
    return render_template("welcome.html")


# Create Logout Page
@app.route("/logout")
def logout():
    app.logger.info(f"User logged out: email={session['email']}, name={session['given_name']}")
    session.clear()
    return redirect(url_for("welcome"))


# Error Handlers - 404
@app.errorhandler(404)
def page_not_found(e):
    app.logger.error(f"Error 404: {e}")
    return render_template("error-404.html"), 404


@app.errorhandler(Exception)
def handle_exception(e):
    app.logger.error(f"Error 500: {e}")
    app.logger.error(traceback.format_exc())
    return render_template("error.html"), 500


if __name__ == "__main__":
    app.run(debug=True)
