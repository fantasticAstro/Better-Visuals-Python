import dash
from dash import dcc, html
import dash.dependencies as dd
import dash_bootstrap_components as dbc
from dash_bootstrap_templates import load_figure_template
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

import base64
import io
from zipfile import ZipFile

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
                        dbc.DropdownMenuItem("Clear Data", id="clear-data", n_clicks=0),
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
                                        [html.B("Instructions: "), "Select ", html.I("Export Budget"), " on your ",
                                         html.A("YNAB (You Need A Budget)", href="https://app.ynab.com/", target="_blank"),
                                         " page and upload the .zip file",
                                         html.Hr(),
                                         dcc.Upload(
                                             id='upload-data',
                                             children=html.Div(['Drag and Drop or ', html.B('Select File')]),
                                             style={
                                                 'width': '100%',
                                                 'height': '60px',
                                                 'lineHeight': '60px',
                                                 'borderWidth': '1px',
                                                 'borderStyle': 'dashed',
                                                 'borderRadius': '5px',
                                                 'textAlign': 'center',
                                                 "background-color": "#f8f9fa"
                                             },
                                             multiple=False,
                                         )],
                                    ),
                                    className="mb-4"
                                ),
                                dbc.Card(
                                    dbc.CardBody([
                                        html.B("Date Range Slider"),
                                        html.Hr(),
                                        dcc.RangeSlider(
                                            id="date-range-slider",
                                            min=0, max=12,
                                            allowCross=False,
                                            step=1,
                                        )
                                    ]
                                    ),
                                    className="mb-4"
                                ),
                                dbc.Card(
                                    dbc.CardBody(
                                        dcc.Graph(id='expense-category-graph')
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
                                        dcc.Graph(id='income-expense-graph')
                                    ),
                                    className="mb-4"
                                ),
                                dbc.Card(
                                    dbc.CardBody(
                                            dcc.Graph(id='account-balance-graph')
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
                dcc.Location(id='url'),
                dcc.Store(id='register-df'),
                dcc.Store(id='budget-df'),
            ],
            className="dbc",
        ),
        fluid=True,
        style={"margin": 0, "padding": 0, "width": "100%", "max-width": "100%", "overflow-x": "hidden"},
    )

    @dash_app.callback(
        dd.Output("register-df", "data"),
        dd.Output("budget-df", "data"),
        dd.Input('upload-data', 'contents'),
        dd.State('upload-data', 'filename')
    )
    def fetch_data(content, filename):
        save_folder = [storage['name'] for storage in dashboard_metadata["storage"] if storage['type'] == 'folder'][0]
        if content is None:
            files_to_check = ['register.json', 'budget.json']
            if check_if_saved_data_exists(files_to_check, save_folder=save_folder, userid=session['id']):
                register_df = fetch_data_from_disk('register.json', save_folder=save_folder, userid=session['id'])
                budget_df = fetch_data_from_disk('budget.json', save_folder=save_folder, userid=session['id'])

                return register_df, budget_df
            else:
                raise dash.exceptions.PreventUpdate

        content_type, content_string = content.split(',')
        content_decoded = base64.b64decode(content_string)
        zip_file = ZipFile(io.BytesIO(content_decoded))

        dfs = {text_file.filename.split(' ')[-1]: pd.read_csv(zip_file.open(text_file.filename))
               for text_file in zip_file.infolist() if text_file.filename.endswith('.csv')}

        register_df = dfs['Register.csv']
        budget_df = dfs['Budget.csv']

        # Convert currency values to float
        register_df['Inflow'] = register_df['Inflow'].str.replace(r'[^0-9.-]+', '', regex=True).astype(float)
        register_df['Outflow'] = register_df['Outflow'].str.replace(r'[^0-9.-]+', '', regex=True).astype(float)
        budget_df['Budgeted'] = budget_df['Budgeted'].str.replace(r'[^0-9.-]+', '', regex=True).astype(float)
        budget_df['Activity'] = budget_df['Activity'].str.replace(r'[^0-9.-]+', '', regex=True).astype(float)
        budget_df['Available'] = budget_df['Available'].str.replace(r'[^0-9.-]+', '', regex=True).astype(float)

        register_df = register_df.to_json(date_format='iso', orient='split')
        budget_df = budget_df.to_json(date_format='iso', orient='split')

        save_data_to_disk(register_df, 'register.json', save_folder=save_folder, userid=session['id'])
        save_data_to_disk(budget_df, 'budget.json', save_folder=save_folder, userid=session['id'])

        return register_df, budget_df

    @dash_app.callback(
        dd.Output("date-range-slider", "marks"),
        dd.Output("date-range-slider", "min"),
        dd.Output("date-range-slider", "max"),
        dd.Output("date-range-slider", "value"),
        dd.Input("budget-df", "modified_timestamp"),
        dd.State("budget-df", "data"),
    )
    def create_daterange(ts, budget_df):
        if budget_df is None:
            raise dash.exceptions.PreventUpdate
        budget_df = pd.read_json(budget_df, orient='split')

        date_range_decoder = {idx: month for idx, month in enumerate(budget_df['Month'].unique()[-12:])}
        date_range_value = [0, len(date_range_decoder) - 1]
        return date_range_decoder, date_range_value[0], date_range_value[1],date_range_value

    @dash_app.callback(
        dd.Output("income-expense-graph", "figure"),
        dd.Output("expense-category-graph", "figure"),
        dd.Output("account-balance-graph", "figure"),
        dd.Input("budget-df", "modified_timestamp"),
        dd.Input("date-range-slider", "value"),
        dd.State("register-df", "data"),
        dd.State("budget-df", "data"),
    )
    def create_graphs(ts, date_range_value, register_df, budget_df):
        if budget_df is None:
            raise dash.exceptions.PreventUpdate
        register_df = pd.read_json(register_df, orient='split')
        budget_df = pd.read_json(budget_df, orient='split')

        date_range_decoder = {idx: month for idx, month in enumerate(budget_df['Month'].unique()[-12:])}
        date_range_encoder = {month: idx for idx, month in date_range_decoder.items()}
        date_range_min, date_range_max = date_range_value[0], date_range_value[1]

        # Data transformations
        budget_df['date_range_encoded'] = budget_df['Month'].map(date_range_encoder)
        register_df['date_range_encoded'] = pd.to_datetime(register_df['Date']).dt.strftime('%b %Y').map(date_range_encoder)

        monthly_data = register_df.groupby(['date_range_encoded']).sum(numeric_only=True).reset_index()
        monthly_budget_activity = budget_df.groupby(['date_range_encoded', 'Month']).sum(numeric_only=True).reset_index()
        monthly_data = pd.merge(monthly_data, monthly_budget_activity, left_on='date_range_encoded', right_on='date_range_encoded')
        monthly_data['Savings'] = (monthly_data['Inflow'] - monthly_data['Outflow']).cumsum()
        monthly_data['3-Month Inflow Avg'] = monthly_data['Inflow'].rolling(window=3, min_periods=1).mean()
        monthly_data['3-Month Outflow Avg'] = monthly_data['Outflow'].rolling(window=3, min_periods=1).mean()

        register_df['Balance'] = register_df['Inflow'] - register_df['Outflow']
        register_df['Month'] = register_df['date_range_encoded'].map(date_range_decoder)
        monthly_account_balance = register_df.groupby(['date_range_encoded', 'Month', 'Account'])['Balance'].sum().reset_index()
        monthly_account_balance['Balance'] = monthly_account_balance.groupby('Account')['Balance'].transform(pd.Series.cumsum)

        # Applying date range filter (Can't apply before finding MA)
        monthly_data = monthly_data[(monthly_data['date_range_encoded'] >= date_range_min) & (monthly_data['date_range_encoded'] <= date_range_max)]
        monthly_account_balance = monthly_account_balance[(monthly_account_balance['date_range_encoded'] >= date_range_min) & (monthly_account_balance['date_range_encoded'] <= date_range_max)]
        budget_df = budget_df[(budget_df['date_range_encoded'] >= date_range_min) & (budget_df['date_range_encoded'] <= date_range_max)]
        register_df = register_df[(register_df['date_range_encoded'] >= date_range_min) & (register_df['date_range_encoded'] <= date_range_max)]

        total_income = register_df['Inflow'].sum()
        total_expense = register_df['Outflow'].sum()
        unspent_money = total_income - total_expense
        outflow_by_category = register_df.groupby(['Category Group', 'Category']).sum(numeric_only=True).reset_index()[['Category Group', 'Category', 'Outflow']]
        unspent_row = pd.DataFrame({'Category Group': ['Unspent'], 'Category': ['Unspent'], 'Outflow': [unspent_money]})
        outflow_by_category = pd.concat([outflow_by_category, unspent_row], ignore_index=True)
        outflow_by_category = outflow_by_category[outflow_by_category['Category Group'] != 'Inflow']

        # Creating colors
        template = pio.templates['flatly']
        color_list = [template.layout.colorway[i] for i in range(5)]
        color_light_list = [hex_to_rgba(color, 0.6) for color in color_list]

        # Creating income-expense-graph
        income_expense_fig = go.Figure()

        income_expense_fig.add_trace(go.Bar(x=monthly_data['Month'], y=monthly_data['Inflow'], name='Income', marker_color=color_list[0]))
        income_expense_fig.add_trace(go.Bar(x=monthly_data['Month'], y=monthly_data['Outflow'], name='Expenses', marker_color=color_list[1]))
        income_expense_fig.add_trace(go.Scatter(x=monthly_data['Month'], y=monthly_data['3-Month Inflow Avg'], name='3-Month Income Avg', line=dict(dash='dash'), marker_color=color_light_list[0]))
        income_expense_fig.add_trace(go.Scatter(x=monthly_data['Month'], y=monthly_data['3-Month Outflow Avg'], name='3-Month Expenses Avg', line=dict(dash='dash'), marker_color=color_light_list[1]))
        income_expense_fig.add_trace(go.Scatter(x=monthly_data['Month'], y=monthly_data['Savings'], name='Savings', mode='lines+markers', marker_color=color_light_list[2]))
        income_expense_fig.update_layout(title='Monthly Income, Expenses, and Savings', barmode='group')

        # Creating expense-category-graph
        expense_category_fig = px.sunburst(outflow_by_category, path=['Category Group', 'Category'], values='Outflow')
        expense_category_fig.update_traces(textinfo="label+percent entry")
        expense_category_fig.update_traces(hovertemplate='<b>%{label}</b><br>Amount: $%{value}<br>')
        expense_category_fig.update_layout(title='Expenses by Category Group and Category')

        # Creating account-balance-graph
        account_balance_fig = px.bar(monthly_account_balance, x='Month', y='Balance', color='Account', text='Balance', barmode="group")
        account_balance_fig.update_traces(texttemplate='%{text:.2s}', textposition='inside')
        account_balance_fig.update_layout(title='Monthly Closing Balance by Account', yaxis_title='Account Balance')

        return income_expense_fig, expense_category_fig, account_balance_fig

    @dash_app.callback(
        dd.Output('url', 'href'),
        dd.Input("clear-data", "n_clicks"),
        prevent_initial_call=True,
    )
    def clear_data(_):
        save_folder = [storage['name'] for storage in dashboard_metadata["storage"] if storage['type'] == 'folder'][0]
        clear_data_from_disk(save_folder=save_folder, userid=session['id'])
        return dashboard_metadata['url_base_pathname']

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
