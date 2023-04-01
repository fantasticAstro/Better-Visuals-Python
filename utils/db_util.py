import os
import json
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Read the dashboard config for the table names
with open("dashboards_config.json", "r") as f:
    dashboards_data = json.load(f)
    dashboard_storage_metadata = {dashboard['file']: dashboard.get('storage',[]) for dashboard in dashboards_data["dashboards"]}


def init_db(app):
    db_path = os.path.join(os.path.abspath(__file__ + '/../../'), 'sqlite.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)


class Dashboard1Table1(db.Model):
    __tablename__ = [storage['name'] for storage in dashboard_storage_metadata['dashboard1'] if storage['type'] == 'SQL'][0]
    email = db.Column(db.String(120), primary_key=True)
    value = db.Column(db.String(120), nullable=False)

    def __init__(self, email, value):
        self.email = email
        self.value = value

    def __repr__(self):
        return f'<UserInput {self.email} {self.value}>'


class SpotifyClientID(db.Model):
    __tablename__ = [storage['name'] for storage in dashboard_storage_metadata['spotify_test'] if storage['type'] == 'SQL'][0]
    email = db.Column(db.String(120), primary_key=True)
    clientid = db.Column(db.String(120), nullable=False)

    def __init__(self, email, clientid):
        self.email = email
        self.clientid = clientid

    def __repr__(self):
        return f'<UserInput {self.email} {self.clientid}>'
