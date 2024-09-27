import re
from datetime import datetime
import os


import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import sqlalchemy as sa
from dash import Dash, html, dcc, Output, Input, callback

from constants import BRAND_ENCODING, BRAND_LABELS, USER_TYPE_LABELS



app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP, 'assets/style.css'])

if not os.getenv('REMOTE', 'false') != 'false':
    from dotenv import load_dotenv
    load_dotenv()


POSTGRES_HOST = os.getenv('POSTGRES_HOST')
POSTGRES_DB = os.getenv('POSTGRES_DB')
POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
POSTGRES_PORT = os.getenv('POSTGRES_PORT')
conn_string = f'postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}'

# Reading dataframes
conn = sa.create_engine(conn_string)


def read_request_df(conn):
    request_df = pd.read_sql_table('easyaudit_requestevent', conn)
    request_df['date'] = pd.to_datetime(request_df['datetime']).dt.date

    request_df['brand'] = request_df['url'].apply(
            lambda url: next((BRAND_ENCODING[key] for key in BRAND_ENCODING if key in url), 0)
    )

    return request_df

def read_phenotype_df(conn):
    phenotype_df = pd.read_sql_table('clinicalcode_historicalgenericentity', conn)
    phenotype_df['date'] = pd.to_datetime(phenotype_df['created']).dt.date

    return phenotype_df

def render_filters():
    min_date = read_phenotype_df(conn)['date'].min()
    max_date = read_request_df(conn)['date'].max()
    return dbc.Row(
            children=[
                    dbc.Col(
                            [
                                    html.Label('Start Date', className='filter-label'),
                                    dcc.DatePickerSingle(
                                            className='date-picker',
                                            id='start-date-filter',
                                            min_date_allowed=min_date,
                                            max_date_allowed=max_date,
                                            display_format='DD-MM-YYYY',
                                            date=min_date
                                    )
                            ],
                            md=3,
                            className='filter'
                    ),
                    dbc.Col(
                            [
                                    html.Label('End Date', className='filter-label'),
                                    dcc.DatePickerSingle(
                                            className='date-picker',
                                            id='end-date-filter',
                                            min_date_allowed=min_date,
                                            max_date_allowed=max_date,
                                            display_format='DD-MM-YYYY',
                                            date=max_date
                                    )
                            ],
                            md=3,
                            className='filter'
                    ),
                    dbc.Col(
                            [
                                    html.Label('Brand', className='filter-label'),
                                    dcc.Dropdown(
                                            className='drop-down',
                                            options=BRAND_LABELS,
                                            value=0,
                                            id='brand-dropdown'
                                    )
                            ],
                            md=3,
                            className='filter'
                    ),
                    dbc.Col(
                            [
                                    html.Label('User Type', className='filter-label'),
                                    dcc.Dropdown(
                                            className='drop-down',
                                            options=USER_TYPE_LABELS,
                                            value=1,
                                            id='usertype-dropdown'
                                    )
                            ],
                            md=3,
                            className='filter'
                    )
            ],
            className='filters-container'
    )



app.layout = dbc.Container(
        [
                dbc.Row(children=[
                        dbc.Col(
                                html.Img(src="assets/images/concept_library_on_white.png", style={
                                        'height': '80%',
                                        'width': '10%',
                                        'float': 'left'
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
                ]
                ),
                render_filters(),
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
                        style={'margin-top': '20px'}
                )
        ],
        fluid=True,
        style={'padding': '20px'}
)


def get_filtered_phenotype_dfs(phenotype_df, start_date, end_date, brand):
    new_phenotype_df = phenotype_df[phenotype_df['status'] == 2][['date', 'created_by_id', 'id', 'brands',
                                                                  'publish_status', 'history_id']]

    new_phenotype_df['min_version'] = new_phenotype_df.groupby('id')['history_id'].transform('min')
    new_phenotype_df = new_phenotype_df[(new_phenotype_df.date >= start_date) &
                                        (new_phenotype_df.date <= end_date)]
    if brand > 0:
        new_phenotype_df = new_phenotype_df[new_phenotype_df.brands.apply(lambda brand_list: brand in brand_list)]

    edit_phenotypes_df = new_phenotype_df[new_phenotype_df.history_id != new_phenotype_df.min_version]
    published_phenotypes_df = new_phenotype_df[new_phenotype_df.publish_status == 2]

    return new_phenotype_df, edit_phenotypes_df, published_phenotypes_df


def get_filtered_users_df(request_df, start_date, end_date, brand):
    tot_users_df = request_df[['date', 'user_id', 'remote_ip', 'brand']]
    tot_users_df = tot_users_df[(tot_users_df.brand == brand) & (tot_users_df.date >= start_date) &
                                (tot_users_df.date <= end_date)]
    return tot_users_df


@callback(
        Output('total-users', 'children'),
        Input('start-date-filter', 'date'),
        Input('end-date-filter', 'date'),
        Input('brand-dropdown', 'value'),
        Input('usertype-dropdown', 'value')
)
def render_user_kpi(start_date, end_date, brand, user_type):
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


if __name__ == '__main__':
    app.run_server(port=8050)
