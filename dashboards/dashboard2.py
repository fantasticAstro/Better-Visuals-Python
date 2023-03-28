import dash
from dash import dcc
from dash import html
import dash.dependencies as dd
import dash_bootstrap_components as dbc
from dash_bootstrap_templates import load_figure_template
from flask import session, redirect, url_for, request


# stylesheet with the .dbc class from dash-bootstrap-templates library
dbc_css = "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates/dbc.min.css"


def create_dash_app(server, google, dashboard_metadata):
    load_figure_template("flatly")

    dash_app = dash.Dash(
        server=server,
        url_base_pathname=dashboard_metadata['url_base_pathname'],
        assets_folder=dashboard_metadata['assets_folder'],
        external_stylesheets=[dbc.themes.FLATLY, dbc_css],
    )
    dash_app.layout = dbc.Container(
        html.Div([
            html.H1(dashboard_metadata['name'], className="bg-primary text-white p-2 mb-2 text-center"),
            html.Div(id="email-display"),
            dcc.Graph(id="example-graph2", figure={
                "data": [{"x": [1, 2, 3], "y": [2, 4, 1], "type": "bar", "name": "NY"}],
                "layout": {"title": "Example Dashboard 2"}
            }),
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

    @dash_app.server.before_request
    def ensure_logged_in():
        if request.path.startswith(dash_app.config['url_base_pathname'].rstrip('/')) and not google.authorized:
            return redirect(url_for("welcome"))

    return dash_app
