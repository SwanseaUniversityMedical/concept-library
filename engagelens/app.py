import base64
import json
import re
import zlib
from datetime import datetime

import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
from dash import Dash, html, dcc, Output, Input, callback, get_asset_url
from flask import request, redirect
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from constants import BRAND_LOGO_PATHS, GRANULARITY_OPTIONS
from utils import read_request_df, read_phenotype_df, render_filters, get_filtered_phenotype_dfs, \
    get_filtered_users_df, get_conn

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
# app = Dash(__name__, requests_pathname_prefix='/dash/', external_stylesheets=[dbc.themes.BOOTSTRAP])

# PostgresSQL connection
conn = get_conn()

# Data read here as it does not change much
# TODO: consider caching as the data doesn't change much
phenotype_df = read_phenotype_df(conn)
request_df = read_request_df(conn)


# Create a session factory
# SessionLocal = sessionmaker(bind=conn)

def validate_django_session():
    """
    Validates the Django session for a given user by checking the session ID stored in the cookies.

    This function retrieves the session cookie (`sessionid`) from the request, checks if the session
    exists and hasn't expired by querying the `django_session` table in the database, and verifies
    if the session contains a valid user ID (`_auth_user_id`).

    Returns:
        bool: True if the session is valid and contains an authenticated user ID, otherwise False.
    """
    def decode_base64(session_str):
        """
        Decodes a base64-encoded string, adding padding if necessary.
        The function ensures the base64-encoded data has the correct length by adding '=' padding
        if the length of the input string is not a multiple of 4, which is required for base64 decoding.
        Args:
            data (str): The base64-encoded string to be decoded.

        Returns:
            bytes: The decoded data as a bytes object.

        Raises:
            binascii.Error: If the input data is incorrectly formatted for base64 decoding.
        """
        session_parts = session_str.split(':')
        data = session_parts[0][1:]

        # Add padding if necessary (length should be a multiple of 4)
        padding_needed = len(data) % 4
        if padding_needed:
            data += '=' * (4 - padding_needed)
        # Decode the base64-encoded data
        return base64.urlsafe_b64decode(data)

    session_cookie = request.cookies.get('sessionid')
    if session_cookie:
        with SessionLocal() as db_session:
            # Query to check if the session exists and has not expired
            result = db_session.execute(
                text("""
                    SELECT session_data 
                    FROM django_session
                    WHERE session_key = :session_key AND expire_date > NOW()
                """),
                {'session_key': session_cookie}
            ).fetchone()

            if result:
                session_data = result[0]
                try:
                    # Decode the base64-encoded session data
                    decoded_data = decode_base64(session_data)  # Add padding if necessary
                    # decompressing the data
                    decompressed_data = zlib.decompress(decoded_data)
                    # Deserialize the data (Django typically uses JSON)
                    session_dict = json.loads(decompressed_data.decode('utf-8'))

                    return '_auth_user_id' in session_dict

                except Exception as e:
                    print(e)
                    return False

    return False

# @app.server.before_request
# def restrict_access():
#     """
#     A before-request function that restricts access to the application by validating the user's session.
#
#     This function checks if the current request has a valid Django session. If the session is invalid
#     or the user is not authenticated, it redirects the user to the login page.
#
#     Redirects:
#         Flask redirect: Redirects the user to the login page if the session is invalid.
#     """
#     is_auth = validate_django_session()
#     if not is_auth:
#         return redirect(f'/account/login/?next=/dash/')

app.layout = dbc.Container(
        [
                dbc.Row(children=[
                        dbc.Col(
                                id='branding',
                                md=5

                        ),
                        dbc.Col(
                                html.Div(
                                        children=html.H1('User Analytics Dashboard')
                                ),
                                md=7
                        )
                ],
                    className='logo-container'
                ),
                render_filters(phenotype_df, request_df),
                dbc.Row(
                        id="kpi-row",
                        children=[
                                dbc.Col(
                                        dbc.Card(
                                                dcc.Loading(
                                                        type="default",
                                                        children=dbc.CardBody([
                                                                html.H5("Total Users", className="card-title"),
                                                                html.H2(id="total-users", className='card-title')
                                                        ])
                                                ),
                                                className='kpi-card'
                                        ),
                                        md=3
                                ),
                                dbc.Col(
                                        dbc.Card(
                                                dcc.Loading(
                                                        type="default",
                                                        children=dbc.CardBody([
                                                                html.H5("New Phenotypes", className="card-title"),
                                                                html.H2(id="new-phenotypes", className='card-title')
                                                        ])
                                                ),
                                                className='kpi-card'
                                        ),
                                        md=3
                                ),
                                dbc.Col(
                                        dbc.Card(
                                                dcc.Loading(
                                                        type="default",
                                                        children=dbc.CardBody([
                                                                html.H5("Phenotype Edits",
                                                                        className="card-title"),
                                                                html.H2(id='edit-phenotypes', className='card-title')
                                                        ])
                                                ),
                                                className='kpi-card'
                                        ),
                                        md=3
                                ),
                                dbc.Col(
                                        dbc.Card(
                                                dcc.Loading(
                                                        type="default",
                                                        children=dbc.CardBody([
                                                                html.H5("Phenotypes Published",
                                                                        className="card-title"),
                                                                html.H2(id='published-phenotypes',
                                                                        className='card-title')
                                                        ])
                                                ),
                                                className='kpi-card'
                                        ),
                                        md=3
                                )
                        ]
                ),
                dbc.Row(
                        [
                                dbc.Col(
                                        dcc.Loading(
                                                type="default",
                                                children=[html.Div(
                                                            [
                                                                    dbc.RadioItems(
                                                                        id="radios",
                                                                        className="btn-group",
                                                                        inputClassName="btn-check",
                                                                        labelClassName="btn btn-outline-primary",
                                                                        labelCheckedClassName="active",
                                                                        options=GRANULARITY_OPTIONS,
                                                                        value=1,
                                                                    ),
                                                            ],
                                                            className="radio-group",
                                                        ),
                                                    dcc.Graph(id='time-series-graph')]
                                        ),
                                        md=8,
                                        style={'padding': '0'}
                                ),
                                dbc.Col(
                                        dcc.Loading(
                                                type="default",
                                                children=dcc.Graph(id='tree-map')
                                        ),
                                        md=4,
                                        style={'padding': '0'}
                                )
                        ],
                        className='plots-container',
                )
        ],

        fluid=True,
        style={'padding': '20px'}
)


@callback(
Output(component_id='branding', component_property='children'),
    Input(component_id='brand-dropdown', component_property='value')
)
def render_header_logo(brand):
    match brand:
        case 1:
            logo_loc = BRAND_LOGO_PATHS[1]['path']
            href = BRAND_LOGO_PATHS[1]['href']
        case 2:
            logo_loc = BRAND_LOGO_PATHS[2]['path']
            href = BRAND_LOGO_PATHS[2]['href']
        case 3:
            logo_loc = BRAND_LOGO_PATHS[3]['path']
            href = BRAND_LOGO_PATHS[3]['href']
        case _:
            logo_loc = BRAND_LOGO_PATHS[0]['path']
            href = BRAND_LOGO_PATHS[0]['href']


    return html.A(
                    html.Img(id='header-logo' ,
                             src = get_asset_url(logo_loc),
                             ),
                    href=href,
                    target='_self'
                )

@callback(
        Output('total-users', 'children'),
        Input('start-date-filter', 'date'),
        Input('end-date-filter', 'date'),
        Input('brand-dropdown', 'value'),
        Input('usertype-dropdown', 'value')
)
def render_user_kpi(start_date, end_date, brand, user_type):
    """Render the total user KPI.

        Args:
            start_date (str): The start date selected by the user.
            end_date (str): The end date selected by the user.
            brand (int): The brand selected by the user.
            user_type (int): The user type selected by the user

    .

        Returns:
            int: The total number of users.
    """
    start_date = datetime.fromisoformat(start_date).date()
    end_date = datetime.fromisoformat(end_date).date()

    tot_users_df = get_filtered_users_df(request_df, start_date, end_date, brand)

    if user_type:
        tot_users_df_filtered = tot_users_df[~tot_users_df.user_id.isna()]
        tot_users_count = tot_users_df_filtered.user_id.nunique()
    else:
        tot_users_df_filtered = tot_users_df[tot_users_df.user_id.isna()]
        tot_users_count = tot_users_df_filtered.remote_ip.nunique()

    return f"{tot_users_count}"


@callback(
        [Output('new-phenotypes', 'children'),
         Output('edit-phenotypes', 'children'),
         Output('published-phenotypes', 'children')],
        Input('start-date-filter', 'date'),
        Input('end-date-filter', 'date'),
        Input('brand-dropdown', 'value'),
        Input('usertype-dropdown', 'value')
)
def render_phenotype_kpis(start_date, end_date, brand, user_type):
    """Render the phenotypes KPI.

        Args:
            start_date (str): The start date selected by the user.
            end_date (str): The end date selected by the user.
            brand (int): The brand selected by the user.
            user_type (int): The user type selected by the user

        Returns:
            int: The total number of new phenotypes.
    """
    if not user_type:
        return ["N/A", "N/A", "N/A"]

    start_date = datetime.fromisoformat(start_date).date()
    end_date = datetime.fromisoformat(end_date).date()

    filtered_phenotype_df = get_filtered_phenotype_dfs(phenotype_df, start_date, end_date, brand)

    # Count of unique phenotypes that were published
    unique_published_count = filtered_phenotype_df[filtered_phenotype_df['is_published']]['id'].nunique()
    # Total number of edits made
    total_edits_count = filtered_phenotype_df['is_edited'].sum()
    # Total number of new phenotypes
    new_phenotypes_count = filtered_phenotype_df['is_new'].sum()

    return [f"{new_phenotypes_count}", f"{total_edits_count}", f"{unique_published_count}"]


@callback(
        Output('tree-map', 'figure'),
        Input('start-date-filter', 'date'),
        Input('end-date-filter', 'date'),
        Input('brand-dropdown', 'value'),
        Input('usertype-dropdown', 'value')
)
def render_tree_map(start_date, end_date, brand, user_type):
    """Render the tree map.

        Args:
            start_date (str): The start date selected by the user.
            end_date (str): The end date selected by the user.
            brand (int): The brand selected by the user.
            user_type (int): The user type selected by the user

        Returns:
            Figure: A Plotly figure for the tree map.
    """
    def extract_search_value(url):
        match = re.search(r'search=([\w+]+)', url)
        if match:
            return match.group(1).replace('+', ' ')
        else:
            return None

    start_date = datetime.fromisoformat(start_date).date()
    end_date = datetime.fromisoformat(end_date).date()

    search_term_df = request_df[['date', 'user_id', 'query_string', 'brand']]
    search_term_df = search_term_df[(search_term_df.brand == brand) & (search_term_df.date >= start_date) &
                                    (search_term_df.date <= end_date)]
    search_term_df['search_value'] = search_term_df['query_string'].apply(extract_search_value)
    if user_type:
        search_term_df = search_term_df[~search_term_df.user_id.isna()]
    else:
        search_term_df = search_term_df[search_term_df.user_id.isna()]

    if len(search_term_df) == 0:
        return px.treemap(title="Search Terms: No data available to render Tree Map")

    tree_map_data = search_term_df.groupby('search_value').size().reset_index(name='count')

    figure = px.treemap(tree_map_data, path=['search_value'], values='count',
                        title='Search Terms')
    figure.update_traces(
            textfont=dict(
                    size=25  # Adjust font size as needed
            )
    )

    return figure


@callback(
        Output('time-series-graph', 'figure'),
        Input('start-date-filter', 'date'),
        Input('end-date-filter', 'date'),
        Input('brand-dropdown', 'value'),
        Input('usertype-dropdown', 'value')
)
def render_time_series(start_date, end_date, brand, user_type):
    """Render the time series graph.

        Args:
            start_date (str): The start date selected by the user.
            end_date (str): The end date selected by the user.
            brand (int): The brand selected by the user.
            user_type (str): The user type selected by the user.

        Returns:
            Figure: A Plotly figure for the time series graph.
    """

    start_date = datetime.fromisoformat(start_date).date()
    end_date = datetime.fromisoformat(end_date).date()

    tot_users_df = get_filtered_users_df(request_df, start_date, end_date, brand)

    if user_type:
        tot_users_df_filtered = tot_users_df[~tot_users_df.user_id.isna()]
        tot_users_ts = tot_users_df_filtered.groupby('date')['user_id'].nunique().reset_index(name='users')

        new_phenotype_df = get_filtered_phenotype_dfs(phenotype_df, start_date, end_date, brand)

        # edit_phenotypes_ts = edit_phenotypes_df.groupby('date').size().reset_index(name='edited phenotypes')
        # published_phenotypes_ts = published_phenotypes_df.groupby('date')['id'].nunique().reset_index(
        #         name='published phenotypes')
        new_phenotypes_ts = new_phenotype_df.groupby('date')['id'].nunique().reset_index(name='new phenotypes')

        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        dates = pd.DataFrame(date_range.date, columns=['date'])

        dates.set_index('date', inplace=True)
        tot_users_ts.set_index('date', inplace=True)
        new_phenotypes_ts.set_index('date', inplace=True)
        # published_phenotypes_ts.set_index('date', inplace=True)
        # edit_phenotypes_ts.set_index('date', inplace=True)

        time_series_data = pd.concat([dates, tot_users_ts, new_phenotypes_ts, published_phenotypes_ts,
                                      edit_phenotypes_ts], axis=1)
        time_series_data.fillna(0, inplace=True)

        fig = px.line(time_series_data, x=time_series_data.index,
                      y=['edited phenotypes', 'new phenotypes', 'published phenotypes', 'users'],
                      labels={'value': 'Count', 'date': 'Date'},
                      title='Time Series Data')
    else:
        tot_users_df_filtered = tot_users_df[tot_users_df.user_id.isna()]
        tot_users_ts = tot_users_df_filtered.groupby('date')['remote_ip'].nunique().reset_index(name='users')

        fig = px.line(tot_users_ts, x='date',
                      y=['users'],
                      labels={'value': 'Count', 'date': 'Date'},
                      title='Time Series Data',
                      line_shape='spline')

    fig.update_layout(
            legend=dict(
                title_text="",
                    orientation='h',
                    yanchor='top',
                    y=1.2,
                    xanchor='center',
                    x=0.5,
                    font={'size': 15}
            )
    )
    return fig

# Expose the WSGI application object
server = app.server

# To run and test in local
if __name__ == '__main__':
    app.run_server(port=8050, debug=True)
