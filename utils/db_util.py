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
