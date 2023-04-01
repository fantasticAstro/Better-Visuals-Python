import dash
from dash import dcc
from dash import html
import dash.dependencies as dd
import dash_bootstrap_components as dbc
from dash_bootstrap_templates import load_figure_template
from flask import session, redirect, url_for, request
from utils.db_util import db, SpotifyClientID
import os
import plotly.express as px
import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyPKCE
from spotipy.cache_handler import CacheFileHandler

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
        html.Div(
            [
                html.H1(dashboard_metadata['name'], className="bg-primary text-white p-2 mb-2 text-center"),
                html.Div(id="email-display"),
                dcc.Input(id="spotify-clientid", type="text", placeholder="Enter you Client ID"),
                html.Button("Submit", id="submit-button", n_clicks=0),
                html.Div(id="stored-value"),
                html.Button("Fetch Data", id="fetch-data-button", n_clicks=0),
                dcc.Graph(id='song-length-graph')
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
        dd.Output("stored-value", "value"),
        [dd.Input("submit-button", "n_clicks")],
        [dd.State("spotify-clientid", "value")]
    )
    def store_and_display_user_value(n_clicks, clientid):
        if n_clicks > 0:
            user_email = session['email']
            stored_value = SpotifyClientID.query.get(user_email)
            if stored_value:
                stored_value.clientid = clientid
            else:
                stored_value = SpotifyClientID(email=user_email, clientid=clientid)
                db.session.add(stored_value)
            db.session.commit()
            return f"Client ID: {clientid}", clientid
        stored_value = SpotifyClientID.query.get(session['email'])
        if stored_value:
            return f"Client ID: {stored_value.clientid if stored_value else 'No ClientID stored'}", stored_value.clientid
        return "No Client ID stored", None


    @dash_app.callback(
        dd.Output("song-length-graph", "figure"),
        [dd.Input("fetch-data-button", "n_clicks"),
         dd.Input("stored-value", "value")]
    )
    def fetch_spotify_data(n_clicks, SPOTIPY_CLIENT_ID):
        if n_clicks > 0:
            sp = spotipy.Spotify(
                auth_manager=SpotifyPKCE(client_id=SPOTIPY_CLIENT_ID, scope=['playlist-read-private'], open_browser=True,
                                         cache_handler=CacheFileHandler(cache_path='.spotipy_cache')))
            """ Note: Spotipy is unable to work with multiple client ids in parallel since it would need multiple 
            instances, per client id. This would need multiple callback servers at multiple ports which would not scale.
            """
            response = sp.current_user_playlists()

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

            tracks = []
            for idx, row in playlists.iterrows():
                # print(f"Extracting {row['playlist_name']}...")
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

            fig = px.violin(tracks, x="playlist_year", y="duration", color="playlist_year", box=True, points="all",
                            hover_data=['name', 'artists', 'album', 'duration'], template='plotly_white',
                            labels={
                                "playlist_year": "Year",
                                "duration": "Song Length (secs)",
                                "name": "Title",
                                "artists": "Artist(s)",
                                "album": "Album"
                            },
                            title="Song Length Across Years",
                            height=600)

            return fig
        return {}

    @dash_app.server.before_request
    def ensure_logged_in():
        if request.path.startswith(dash_app.config['url_base_pathname'].rstrip('/')) and not google.authorized:
            return redirect(url_for("welcome"))

    return dash_app