import dash
from dash import dcc
from dash import html
import dash.dependencies as dd
import dash_bootstrap_components as dbc
from dash_bootstrap_templates import load_figure_template
from flask import session, redirect, url_for, request
from utils.db_util import db, Dashboard1Table1
import plotly.express as px


# stylesheet with the .dbc class from dash-bootstrap-templates library
dbc_css = "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates/dbc.min.css"


def create_dash_app(server, google, dashboard_metadata):
    load_figure_template("flatly")

    df = px.data.tips()
    fig = px.bar(df, x="sex", y="total_bill", color="smoker", barmode="group")

    dash_app = dash.Dash(
        server=server,
        url_base_pathname=dashboard_metadata['url_base_pathname'],
        assets_folder=dashboard_metadata['assets_folder'],
        external_stylesheets=[dbc.themes.FLATLY, dbc_css],
    )
    dash_app.layout = dbc.Container(
        html.Div(
            [
                html.H1(dashboard_metadata['name'], className="bg-primary text-white p-2 mb-2 text-center"),
                html.Div(id="email-display"),
                dcc.Input(id="user-value", type="text", placeholder="Enter a value"),
                html.Button("Submit", id="submit-button", n_clicks=0),
                html.Div(id="stored-value"),
                dcc.Graph(id="example-graph", figure=fig),
            ],
            className="dbc",
        )
    )

    @dash_app.callback(
        dd.Output("email-display", "children"),
        [dd.Input("email-display", "id")]
    )
    def update_email(_):
        return f"Logged in as {session.get('email', 'unknown')}"

    @dash_app.callback(
        dd.Output("stored-value", "children"),
        [dd.Input("submit-button", "n_clicks")],
        [dd.State("user-value", "value")]
    )
    def store_and_display_user_value(n_clicks, user_value):
        if n_clicks > 0:
            user_email = session['email']
            stored_value = Dashboard1Table1.query.get(user_email)
            if stored_value:
                stored_value.value = user_value
            else:
                stored_value = Dashboard1Table1(email=user_email, value=user_value)
                db.session.add(stored_value)
            db.session.commit()
            return f"Stored value: {user_value}"
        stored_value = Dashboard1Table1.query.get(session['email'])
        return f"Stored value: {stored_value.value if stored_value else 'No value'}"

    @dash_app.server.before_request
    def ensure_logged_in():
        if request.path.startswith(dash_app.config['url_base_pathname'].rstrip('/')) and not google.authorized:
            return redirect(url_for("welcome"))

    return dash_app