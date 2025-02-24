import os
from datetime import date
from urllib.parse import quote
import dash_bootstrap_components as dbc
import pandas as pd
import sqlalchemy as sa
from dash import html, dcc

from constants import BRAND_ENCODING, BRAND_LABELS, USER_TYPE_LABELS


def read_request_df(conn):
    """Read request event data from the database.

        Args:
            conn: SQLAlchemy connection object.

        Returns:
            DataFrame: A pandas DataFrame containing the request events.
    """
    request_df = pd.read_sql_table('easyaudit_requestevent', conn)
    request_df['date'] = pd.to_datetime(request_df['datetime']).dt.date

    request_df['brand'] = request_df['url'].apply(
            lambda url: next((BRAND_ENCODING[key] for key in BRAND_ENCODING if key in url), 0)
    )

    return request_df


def read_phenotype_df(conn):
    """Read phenotype data from the database.

        Args:
            conn: SQLAlchemy connection object.

        Returns:
            DataFrame: A pandas DataFrame containing the phenotype data.
    """
    phenotype_df = pd.read_sql_table('clinicalcode_historicalgenericentity', conn)
    phenotype_df['date'] = pd.to_datetime(phenotype_df['created']).dt.date

    return phenotype_df


def render_filters(phenotype_df, request_df):
    """Render filter components for the dashboard.
            conn: SQLAlchemy connection object.
        Returns:
            Row: A Dash Row component containing filter components.
    """
    min_date = phenotype_df['date'].min()
    max_date = request_df['date'].max()

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


def get_filtered_phenotype_dfs(phenotype_df, start_date, end_date, brand):
    """Filter the phenotype DataFrame based on provided criteria.

        Args:
            phenotype_df (DataFrame): The DataFrame containing phenotype data.
            start_date (date): The start date for filtering.
            end_date (date): The end date for filtering.
            brand (int): The brand filter.

        Returns:
            tuple: Filtered DataFrames for new phenotypes, edited phenotypes, and published phenotypes.
    """

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
    """Filter the user DataFrame based on provided criteria.

        Args:
            request_df (DataFrame): The DataFrame containing request data.
            start_date (date): The start date for filtering.
            end_date (date): The end date for filtering.
            brand (int): The brand filter.

        Returns:
            DataFrame: Filtered DataFrame of users.
    """
    tot_users_df = request_df[['date', 'user_id', 'remote_ip', 'brand']]
    tot_users_df = tot_users_df[(tot_users_df.brand == brand) & (tot_users_df.date >= start_date) &
                                (tot_users_df.date <= end_date)]
    return tot_users_df


def get_conn():
    """
    Function to get SQL connection from environment variables.
    """
    POSTGRES_HOST = os.getenv('POSTGRES_HOST')
    POSTGRES_DB = os.getenv('POSTGRES_DB')
    POSTGRES_USER = os.getenv('POSTGRES_USER')
    POSTGRES_PASSWORD = quote(os.getenv('POSTGRES_PASSWORD'))
    POSTGRES_PORT = os.getenv('POSTGRES_PORT')

    conn_string = f'postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}'
    conn = sa.create_engine(conn_string)
    return conn
