import dash
from dash import dcc, html
import dash.dependencies as dd
import dash_bootstrap_components as dbc
from dash_bootstrap_templates import load_figure_template
import plotly.express as px
import plotly.graph_objects as go

from flask import session, redirect, url_for, request
from urllib.parse import urlencode, urlparse, urlunparse, parse_qs

import pandas as pd
from collections import Counter
from sklearn.preprocessing import MultiLabelBinarizer
import json

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import FlaskSessionCacheHandler

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
                                    dbc.CardBody([
                                        "View you change in taste by comparing your annual 'Your Top 100 Songs XXXX' Spotify playlists",
                                        html.Hr(),
                                        dbc.Spinner(id='loading',
                                                    children=[
                                                        html.Button("Fetch Data", id="fetch-data-button", n_clicks=0,
                                                                    className="btn btn-info btn-lg",
                                                                    style={'width': '100%'}),
                                                        dcc.Store(id='tracks-df'),
                                                        dcc.Store(id='tracks-encoded-df'),
                                                        dcc.Store(id='years-list'),
                                                        dcc.Store(id='artist-presence-df'),
                                                        dcc.Store(id='genre-counter-df'),
                                                        dcc.Store(id='color-map'),
                                                    ]),
                                    ]),
                                    className="mb-4"
                                ),
                                dbc.Card(
                                    dbc.CardBody(
                                        dcc.Graph(id='song-length-graph')
                                    ),
                                    className="mb-4"
                                ),
                                dbc.Card(
                                    dbc.CardBody(
                                        dcc.Graph(id='artist-occurance-graph')
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
                                        dcc.Graph(id='top-genre-graph')
                                    ),
                                    className="mb-4"
                                ),
                                dbc.Card(
                                    dbc.CardBody(
                                        [
                                            dcc.Dropdown(id='song-occurance-flow-year', searchable=False,
                                                         placeholder="Select a year"),
                                            dcc.Graph(id='song-occurance-flow-graph'),
                                            dcc.Graph(id='song-occurance-flow-table'),
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
                dcc.Location(id='url'),
            ],
            className="dbc",
        ),
        fluid=True,
        style={"margin": 0, "padding": 0, "width": "100%", "max-width": "100%", "overflow-x": "hidden"},
    )


    @dash_app.callback(
        dd.Output("tracks-df", "data"),
        dd.Output("tracks-encoded-df", "data"),
        dd.Output("artist-presence-df", "data"),
        dd.Output("genre-counter-df", "data"),
        dd.Output("years-list", "data"),
        dd.Output("song-occurance-flow-year", "options"),
        dd.Output("url", "href"),
        dd.Output("url", "refresh"),
        dd.Input("fetch-data-button", "n_clicks"),
        dd.State("url", "href"),
    )
    def fetch_spotify_data(n_clicks, current_url):
        auth_manager = SpotifyOAuth(scope=['playlist-read-private'], show_dialog=True, cache_handler=FlaskSessionCacheHandler(session))
        # Check for valid_token
        valid_token = auth_manager.validate_token(auth_manager.cache_handler.get_cached_token())
        # Check for the code in the URL
        parsed_url = urlparse(current_url)
        query_params = parse_qs(parsed_url.query)
        code = query_params.get("code", [None])[0]

        save_folder = [storage['name'] for storage in dashboard_metadata["storage"] if storage['type'] == 'folder'][0]
        if n_clicks == 0 and code is None:
            files_to_check = ['tracks.json', 'tracks_encoded.json', 'artist_presence.json', 'genre_year_counter.json', 'years.json']
            if check_if_saved_data_exists(files_to_check, save_folder=save_folder, userid=session['id']):
                tracks = fetch_data_from_disk('tracks.json', save_folder=save_folder, userid=session['id'])
                tracks_encoded = fetch_data_from_disk('tracks_encoded.json', save_folder=save_folder, userid=session['id'])
                artist_presence = fetch_data_from_disk('artist_presence.json', save_folder=save_folder, userid=session['id'])
                genre_year_counter = fetch_data_from_disk('genre_year_counter.json', save_folder=save_folder, userid=session['id'])
                years_json = fetch_data_from_disk('years.json', save_folder=save_folder, userid=session['id'])
                years = json.loads(years_json)

                return (tracks, tracks_encoded, artist_presence, genre_year_counter, years_json, years,) + (dash.no_update, )*2
            else:
                raise dash.exceptions.PreventUpdate

        auth_manager.get_auth_response = (lambda self: code).__get__(auth_manager, SpotifyOAuth)
        if code is not None:
            query_params.pop('code', None)
            parsed_url = parsed_url._replace(query=urlencode(query_params, True))
            current_url = urlunparse(parsed_url)

        if code is None and valid_token is None:
            # Redirect the user if the code is not present
            auth_url = auth_manager.get_authorize_url()
            return (dash.no_update,) * 6 + (auth_url, True)

        sp = spotipy.Spotify(auth_manager=auth_manager)
        response = sp.current_user_playlists()

        # Download and process "Your Top Songs" playlists
        playlists = []
        for item in response['items']:
            if item['name'].startswith("Your Top Songs") and item['owner']['display_name'] == "Spotify":
                playlists.append({
                    "playlist_year": item["name"][-4:],
                    "playlist_name": item["name"],
                    "playlist_id": item["id"]
                })

        playlists = pd.DataFrame(playlists)
        playlists = playlists.sort_values("playlist_year", ignore_index=True)

        # Download and process tracks from the playlists
        tracks = []
        for idx, row in playlists.iterrows():
            response = sp.playlist(row["playlist_id"])

            for item in response['tracks']['items']:
                tracks.append({
                    "name": item['track']['name'],
                    "artists": [i['name'] for i in item['track']['artists']],
                    "album": item['track']['album']['name'],
                    "release_year": item['track']['album']['release_date'][:4],
                    "duration": item['track']['duration_ms'] / 1000,
                    "track_id": item['track']['id'],
                    "artist_id": [i['id'] for i in item['track']['artists']],
                    "album_id": item['track']['album']['id'],
                    "playlist_year": row["playlist_year"],
                    "playlist_name": row["playlist_name"]
                })

        tracks = pd.DataFrame(tracks)
        tracks['my_id'] = tracks['name'] + "--" + tracks['artists'].apply(', '.join) + "--" + tracks['album']

        # Create tracks_encoded table
        temp = tracks.groupby('my_id').playlist_year.apply(list).reset_index()
        temp = temp.merge(tracks.drop(['playlist_year', 'playlist_name'], axis=1), on='my_id', how='left')

        mlb = MultiLabelBinarizer()

        tracks_encoded = pd.concat(
            [temp, pd.DataFrame(mlb.fit_transform(temp['playlist_year']), columns=mlb.classes_, index=temp.index)],
            axis=1)
        tracks_encoded = tracks_encoded.drop_duplicates('my_id').reset_index(drop=True)
        tracks_encoded = tracks_encoded.drop('playlist_year', axis=1)

        years = list(mlb.classes_)

        tracks_encoded["occurances"] = tracks_encoded[years].sum(axis=1)

        # Create artist-occurance-graph
        artists = list(set([j for i in tracks_encoded.artists.to_list() for j in i]))

        artist_presence = []
        for artist in artists:
            temp = (
                tracks_encoded.loc[tracks_encoded['artists'].apply(lambda x: artist in x), years]).sum().to_dict()
            temp["artist"] = artist
            artist_presence.append(temp)

        artist_presence = pd.DataFrame(artist_presence)
        artist_presence['occurances'] = artist_presence[years].sum(axis=1)
        artist_presence = artist_presence.sort_values('occurances', ascending=False)

        # Download and process genre
        artist_ids = list(set([j for i in tracks_encoded.artist_id.to_list() for j in i]))

        artist_genres = {}
        for i in range(0, len(artist_ids), 50):
            response = sp.artists(artist_ids[i:i + 50])
            for item in response['artists']:
                artist_genres[item['name']] = item['genres']

        artist_presence['genres'] = artist_presence['artist'].map(artist_genres)

        genre_year_counter = {year: [] for year in years}

        for idx, row in artist_presence.iterrows():
            for year in years:
                genre_year_counter[year] = genre_year_counter[year] + (row['genres'] * row[year])

        genre_year_counter = {k: Counter(v) for k, v in genre_year_counter.items()}

        genre_total_counter = Counter()
        for i in genre_year_counter.values():
            genre_total_counter.update(i)

        top_genres = [i[0] for i in genre_total_counter.most_common(5)]

        genre_year_counter = pd.DataFrame(genre_year_counter)
        genre_year_counter = genre_year_counter[genre_year_counter.index.isin(top_genres)]
        genre_year_counter = genre_year_counter.reindex(top_genres).astype(int)
        genre_year_counter = genre_year_counter.T

        tracks = tracks.to_json(date_format='iso', orient='split')
        tracks_encoded = tracks_encoded.to_json(date_format='iso', orient='split')
        artist_presence = artist_presence.to_json(date_format='iso', orient='split')
        genre_year_counter = genre_year_counter.to_json(date_format='iso', orient='split')
        years_json = json.dumps(years)

        save_data_to_disk(tracks, 'tracks.json', save_folder=save_folder, userid=session['id'])
        save_data_to_disk(tracks_encoded, 'tracks_encoded.json', save_folder=save_folder, userid=session['id'])
        save_data_to_disk(artist_presence, 'artist_presence.json', save_folder=save_folder, userid=session['id'])
        save_data_to_disk(genre_year_counter, 'genre_year_counter.json', save_folder=save_folder, userid=session['id'])
        save_data_to_disk(years_json, 'years.json', save_folder=save_folder, userid=session['id'])

        return (tracks, tracks_encoded, artist_presence, genre_year_counter, years_json, years) + (current_url, dash.no_update)

    @dash_app.callback(
        dd.Output("song-length-graph", "figure"),
        dd.Output("artist-occurance-graph", "figure"),
        dd.Output("top-genre-graph", "figure"),
        dd.Output("color-map", "data"),
        dd.Input("years-list", 'modified_timestamp'),  # Using only 1 ts since they should all be updated together
        dd.State("tracks-df", "data"),
        dd.State("artist-presence-df", "data"),
        dd.State("genre-counter-df", "data"),
        dd.State("years-list", "data"),
    )
    def create_graphs(ts, tracks, artist_presence, genre_year_counter, years):
        if ts is None:
            raise dash.exceptions.PreventUpdate

        tracks = pd.read_json(tracks, orient='split')
        artist_presence = pd.read_json(artist_presence, orient='split')
        genre_year_counter = pd.read_json(genre_year_counter, orient='split')
        years = json.loads(years)

        # Create song-length-graph
        song_length_fig = px.violin(tracks, x="playlist_year", y="duration", color="playlist_year", box=True,
                                    points="all", hover_data=['name', 'artists', 'album', 'duration'],
                                    labels={
                                        "playlist_year": "Year",
                                        "duration": "Song Length (secs)",
                                        "name": "Title",
                                        "artists": "Artist(s)",
                                        "album": "Album"
                                    },
                                    title="Song Length Across Years",
                                    height=600)

        # Set color map for consistency
        color_map = {i['name']: i['marker']['color'] for i in song_length_fig['data']}

        artist_occurance_fig = px.imshow(artist_presence[years].head(10).values.tolist(),
                                         labels=dict(x="Year", y="Artist", color="Occurances"),
                                         x=years,
                                         y=artist_presence.artist.to_list()[:10],
                                         height=800,
                                         title="Presence Of Your Top 10 Artists")
        artist_occurance_fig.update_xaxes(side="top")

        top_genre_fig = go.Figure()

        for idx, row in genre_year_counter.iterrows():
            top_genre_fig.add_trace(go.Scatterpolar(
                r=row,
                theta=genre_year_counter.columns,
                fill='toself',
                name=idx
            ))

        top_genre_fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True
                )),
            height=800,
            title='Presence Of Your Top 5 Genres')

        color_map = json.dumps(color_map)
        return song_length_fig, artist_occurance_fig, top_genre_fig, color_map

    @dash_app.callback(
        dd.Output("song-occurance-flow-graph", "figure"),
        dd.Output("song-occurance-flow-table", "figure"),
        dd.Input("color-map", 'modified_timestamp'),  # Using only 1 ts since color-map should be last updated
        dd.Input("song-occurance-flow-year", "value"),
        dd.State("tracks-encoded-df", "data"),
        dd.State("years-list", "data"),
        dd.State("color-map", "data"),
    )
    def create_song_occurance_flow(ts, year_filter, tracks_encoded, years, color_map):
        if ts is None:
            raise dash.exceptions.PreventUpdate

        tracks_encoded = pd.read_json(tracks_encoded, orient='split')
        years = json.loads(years)
        color_map = json.loads(color_map)

        if year_filter is None:
            year_filter = years[-1]

        dims = []
        for year in years:
            dims.append(go.parcats.Dimension(
                values=tracks_encoded[year],
                label=year, categoryarray=[1, 0],
                ticktext=['Top 100 🕪', '🔇']
            ))

        # Create parcats trace
        color = tracks_encoded[year_filter];
        colorscale = [[0, 'lightsteelblue'], [1, color_map[year_filter]]]

        g1 = go.Figure(data=[go.Parcats(dimensions=dims,
                                        line={'color': color, 'colorscale': colorscale},
                                        hoveron='color', hoverinfo='skip',
                                        arrangement='freeform')],
                       layout=go.Layout(title=f'{year_filter} Song Occurance Flow'))

        temp = tracks_encoded[(tracks_encoded[year_filter] == 1) & (tracks_encoded['occurances'] > 1)]
        temp = temp.sort_values(['occurances'] + years[::-1], ascending=False)
        temp = temp[['name', 'artists', 'album'] + years]
        temp['artists'] = temp['artists'].str.join(', ')

        header_values = ['<b>Title</b>', '<b>Artist(s)</b>', '<b>Album</b>'] + [f'<b>{i}</b>' for i in years]
        color_values = [["#EBF0F8"] * len(temp), ["#EBF0F8"] * len(temp), ["#EBF0F8"] * len(temp)] + [
            ["#EBF0F8" if j == 0 else color_map[i] for j in temp[i]] for i in years]
        temp[years] = temp[years].applymap({1: 'Top 100 🕪', 0: '🔇'}.get)
        cell_values = [temp[i] for i in temp.columns]

        g2 = go.Figure(data=[go.Table(
            header=dict(
                values=header_values,
                line_color='white', fill_color='white',
                align='center', font=dict(color='black', size=12)),
            cells=dict(
                values=cell_values,
                fill_color=color_values))],
            layout=go.Layout(height=1000, title=f'{year_filter} Songs Details'))

        return g1, g2

    @dash_app.callback(
        dd.Output('url', 'href', allow_duplicate=True),
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
