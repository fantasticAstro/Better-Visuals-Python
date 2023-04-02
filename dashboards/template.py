import dash
from dash import dcc, html
import dash.dependencies as dd
import dash_bootstrap_components as dbc
from dash_bootstrap_templates import load_figure_template
import plotly.express as px
import plotly.graph_objects as go

from flask import session, redirect, url_for, request

import pandas as pd

from utils.utils import *

# stylesheet with the .dbc class from dash-bootstrap-templates library
dbc_css = "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates/dbc.min.css"
fa_css = "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.3.0/css/all.min.css"


def create_dash_app(server, google, dashboard_metadata):
    load_figure_template("flatly")

    dash_app = dash.Dash(
        server=server,
        url_base_pathname=dashboard_metadata['url_base_pathname'],
        external_stylesheets=[dbc.themes.FLATLY, dbc_css, fa_css],
    )

    dash_app.title = f"{dashboard_metadata['name']} | Better Visuals"

    navbar = dbc.Navbar(
        [
            dbc.Col(
                html.A(
                    html.I(className="fas fa-home text-white"),  # Font Awesome home icon
                    href="/",
                    style={"margin-right": "1rem"},  # Add some margin to the right of the icon
                ),
                width={"size": "auto"},
            ),
            dbc.Col(
                dbc.NavbarBrand(dashboard_metadata['name'], className="mb-0"),
                width={"size": True, "grow": True},
            ),
            dbc.Col(
                dbc.DropdownMenu(
                    [
                        dbc.DropdownMenuItem("Email: ", header=True, id="email-display"),
                        dbc.DropdownMenuItem(divider=True),
                        dbc.DropdownMenuItem("Logout", href="/logout", external_link=True),
                    ],
                    nav=True,
                    in_navbar=True,
                    label="More",
                    toggle_style={"color": "white", "border": "none"},  # Modify the color of the menu dropdown
                    right=True,
                ),
                width={"size": "auto"},
            ),
        ],
        color="primary",
        dark=True,
        style={"padding-left": "1rem", "padding-right": "1rem"},  # Add padding to the left and right edges
    )

    footer = html.Div(
        [
            html.P(
                [
                    "Created by ",
                    html.A("Kavish Hukmani", href="https://kavishhukmani.me/", target="_blank"),
                ],
                className="text-center",
            )
        ],
        style={"bottom": 0, "width": "100%", "background-color": "#f8f9fa", "padding": "0.5rem"},
    )

    dash_app.layout = dbc.Container(
        html.Div(
            [
                navbar,
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Card(
                                    dbc.CardBody(
                                        html.Button("Fetch Data", id="fetch-data-button", n_clicks=0,
                                                    className="btn btn-info btn-lg", style={'width': '100%'}),
                                    ),
                                    className="mb-4"
                                ),
                                dbc.Card(
                                    dbc.CardBody(
                                        dcc.Graph(id='iris-scatter-graph')
                                    ),
                                    className="mb-4"
                                ),
                                dbc.Card(
                                    dbc.CardBody(
                                        dcc.Graph(id='iris-parallel-graph')
                                    ),
                                    className="mb-4"
                                ),
                            ],
                            md=6
                        ),
                        dbc.Col(
                            [
                                dbc.Card(
                                    dbc.CardBody(
                                        dcc.Graph(id='iris-contour-graph')
                                    ),
                                    className="mb-4"
                                ),
                                dbc.Card(
                                    dbc.CardBody(
                                        [
                                            dcc.Dropdown(
                                                id="iris-dropdown",
                                                options=['sepal_length', 'sepal_width', 'petal_length', 'petal_width'],
                                                value=['sepal_length', 'sepal_width'],
                                                multi=True,
                                            ),
                                            dcc.Graph(id='iris-scatter-matrix-graph'),
                                        ]
                                    ),
                                    className="mb-4"
                                ),
                            ],
                            md=6
                        ),
                    ],
                    style={"margin-top": "1rem", "padding-left": "1rem", "padding-right": "1rem"},
                    # Add padding between the navbar and the top of the cards, and re-add padding for the cards
                ),
                footer,
                dcc.Store(id='iris-df'),
            ],
            className="dbc",
        ),
        fluid=True,
        style={"margin": 0, "padding": 0, "width": "100%", "max-width": "100%", "overflow-x": "hidden"},
    )

    @dash_app.callback(
        dd.Output("iris-df", "data"),
        dd.Input("fetch-data-button", "n_clicks")
    )
    def fetch_data(n_clicks):
        save_folder = [storage['name'] for storage in dashboard_metadata["storage"] if storage['type'] == 'folder'][0]
        if n_clicks == 0:
            files_to_check = ['iris.json']
            if check_if_saved_data_exists(files_to_check, save_folder=save_folder, userid=session['id']):
                iris_df = fetch_data_from_disk('iris.json', save_folder=save_folder, userid=session['id'])
                return iris_df
            else:
                raise dash.exceptions.PreventUpdate

        iris_df = px.data.iris()  # Replace with fetch code
        iris_df = iris_df.to_json(date_format='iso', orient='split')
        save_data_to_disk(iris_df, 'iris.json', save_folder=save_folder, userid=session['id'])

        return iris_df

    @dash_app.callback(
        dd.Output("iris-scatter-graph", "figure"),
        dd.Output("iris-parallel-graph", "figure"),
        dd.Output("iris-contour-graph", "figure"),
        dd.Output("iris-scatter-matrix-graph", "figure"),
        dd.Input("iris-df", 'modified_timestamp'),
        dd.Input("iris-dropdown", "value"),
        dd.State("iris-df", "data"),
    )
    def create_graphs(ts, dims, iris_df):
        if ts is None:
            raise dash.exceptions.PreventUpdate
        iris_df = pd.read_json(iris_df, orient='split')

        iris_scatter_fig = px.scatter(iris_df, x="sepal_width", y="sepal_length", color="species")

        iris_parallel_fig = px.parallel_coordinates(iris_df, color="species_id", labels={"species_id": "Species",
                                                                                    "sepal_width": "Sepal Width",
                                                                                    "sepal_length": "Sepal Length",
                                                                                    "petal_width": "Petal Width",
                                                                                    "petal_length": "Petal Length", },
                                                    color_continuous_midpoint=2)

        iris_contour_fig = px.density_contour(iris_df, x="sepal_width", y="sepal_length")

        iris_scatter_matrix_fig = px.scatter_matrix(iris_df, dimensions=dims, color="species")

        return iris_scatter_fig, iris_parallel_fig, iris_contour_fig, iris_scatter_matrix_fig

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
