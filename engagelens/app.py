import re
from datetime import datetime

import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
from dash import Dash, html, dcc, Output, Input, callback, get_asset_url

from utils import read_request_df, read_phenotype_df, render_filters, get_filtered_phenotype_dfs, \
     get_filtered_users_df, get_conn


app = Dash(__name__, requests_pathname_prefix='/dash/', external_stylesheets=[dbc.themes.BOOTSTRAP])

# PostgresSQL connection
conn = get_conn()

# @app.server.before_request
# def dash_app():
#     # Check if the session cookie exists
#     if 'sessionid' not in request.cookies:  # 'sessionid' is Django's default session cookie
#         print(request.cookies)
#         return redirect('/account/login/login')  # Redirect to Django login page if not authenticated
#     return app.index()


app.layout = dbc.Container(
        [
                dbc.Row(children=[
                        dbc.Col(
                                html.Img(src=get_asset_url('/images/concept_library_on_white.png'), style={
                                        'height': '80%',
                                        'width': '10%',
                                        'float': 'left',
                                        'aspect-ratio': 'auto'
                                }
                                         ),
                                md=5

                        ),
                        dbc.Col(
                                html.Div(
                                        children=html.H1('User Analytics Dashboard',
                                                         style={
                                                                 'text-align': 'left',
                                                                 'margin-bottom': '20px'
                                                         }
                                                         )
                                ),
                                md=7
                        )
                ],
                    className='logo-container'
                ),
                render_filters(conn),
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
                                                                html.H5("Phenotypes Edited",
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
                        ],
                        style={'margin-top': '20px'}
                ),
                dbc.Row(
                        [
                                dbc.Col(
                                        dcc.Loading(
                                                type="default",
                                                children=dcc.Graph(id='time-series-graph')
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
    request_df = read_request_df(conn)
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
    phenotype_df = read_phenotype_df(conn)
    if not user_type:
        return ["N/A", "N/A", "N/A"]

    start_date = datetime.fromisoformat(start_date).date()
    end_date = datetime.fromisoformat(end_date).date()

    new_phenotype_df, edit_phenotypes_df, published_phenotypes_df = get_filtered_phenotype_dfs(phenotype_df, start_date,
                                                                                               end_date, brand)

    edit_phenotypes_count = len(edit_phenotypes_df)
    published_phenotypes_count = published_phenotypes_df['id'].nunique()
    new_phenotypes_count = new_phenotype_df['id'].nunique()
    return [f"{new_phenotypes_count}", f"{edit_phenotypes_count}", f"{published_phenotypes_count}"]


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

    request_df = read_request_df(conn)

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
    phenotype_df = read_phenotype_df(conn)
    request_df = read_request_df(conn)

    start_date = datetime.fromisoformat(start_date).date()
    end_date = datetime.fromisoformat(end_date).date()

    tot_users_df = get_filtered_users_df(request_df, start_date, end_date, brand)

    if user_type:
        tot_users_df_filtered = tot_users_df[~tot_users_df.user_id.isna()]
        tot_users_ts = tot_users_df_filtered.groupby('date')['user_id'].nunique().reset_index(name='users')

        new_phenotype_df, edit_phenotypes_df, published_phenotypes_df = get_filtered_phenotype_dfs(phenotype_df,
                                                                                                   start_date, end_date,
                                                                                                   brand)

        edit_phenotypes_ts = edit_phenotypes_df.groupby('date').size().reset_index(name='edited phenotypes')
        published_phenotypes_ts = published_phenotypes_df.groupby('date')['id'].nunique().reset_index(
                name='published phenotypes')
        new_phenotypes_ts = new_phenotype_df.groupby('date')['id'].nunique().reset_index(name='new phenotypes')

        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        dates = pd.DataFrame(date_range.date, columns=['date'])

        dates.set_index('date', inplace=True)
        tot_users_ts.set_index('date', inplace=True)
        new_phenotypes_ts.set_index('date', inplace=True)
        published_phenotypes_ts.set_index('date', inplace=True)
        edit_phenotypes_ts.set_index('date', inplace=True)

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
                    orientation='h',
                    yanchor='bottom',
                    y=-0.3,
                    xanchor='center',
                    x=0.5,
                    font={'size': 18}
            )
    )

    return fig

# Expose the WSGI application object
server = app.server

# To run and test in local
if __name__ == '__main__':
    app.run_server(port=8050, debug=True)