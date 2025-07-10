import os
from datetime import date, datetime
from urllib.parse import quote

import pandas as pd
import psycopg2
from dateutil.relativedelta import relativedelta
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine

from constants import BRAND_ENCODING

def read_data_df(conn):
    """

    @param conn:
    @return:
    """
    phenotype_df = read_phenotype_df(conn)
    request_df = read_request_df(conn)

    return phenotype_df, request_df



def read_request_df(conn):
    """Read request event data from the database.

        Args:
            cursor: SQLAlchemy connection object.

        Returns:
            DataFrame: A pandas DataFrame containing the request events.
    """

    sql_query = f"""
                    SELECT 
                        t.user_id,  
                        t.query_string,
                        t.remote_ip,
                        t.url,
                        CAST(t.datetime as DATE)  as date
                    FROM 
                        easyaudit_requestevent t
                    WHERE 
                        method = 'GET'
                        
                        
    """
    request_df = pd.read_sql(sql_query, conn)
    request_df['brand'] = request_df['url'].apply(lambda x: next((value for brand, value in BRAND_ENCODING.items() if brand in x), 0))

    return request_df


def read_phenotype_df(conn):
    """Read phenotype data from the database.

        Args:
            conn: SQLAlchemy connection object.

        Returns:
            DataFrame: A pandas DataFrame containing the phenotype data.
    """

    sql_query = """
        WITH first_published_dates AS (
            SELECT 
                id, 
                MIN(history_date) AS first_publish_date
            FROM 
                clinicalcode_historicalgenericentity
            WHERE 
                publish_status = 2
            GROUP BY 
                id
        )
        SELECT 
            CAST(t.history_date AS DATE) as date,
            t.id,
            t.brands,
            t.publish_status,
            t.history_id,
            CAST(f.first_publish_date as DATE) AS publish_date
        FROM 
            clinicalcode_historicalgenericentity t
        LEFT JOIN 
            first_published_dates f
        ON 
            t.id = f.id;
        """

    phenotype_df = pd.read_sql(sql_query, conn)

    return phenotype_df

def read_data_from_store(data, schema):
    """
    Read data from the dash store.
    Args:
            data: data to read from the dash store.
            schema: schema of the date.

        Returns:
            DataFrame: A pandas DataFrame.
    """
    phenotype_df = pd.DataFrame(data)
    phenotype_df = phenotype_df.astype(schema)

    return phenotype_df

def get_date_range(start_date, end_date, freq):
    start_date = datetime.strptime(start_date, "%Y-%m-%d").replace(day=1)
    end_date = datetime.strptime(end_date, "%Y-%m-%d").replace(day=1) + relativedelta(months = 1)

    return pd.date_range(start=start_date, end=end_date, freq=freq)


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
    start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

    new_phenotype_df = phenotype_df[['date', 'id', 'brands', 'publish_status', 'history_id', 'publish_date']].copy()

    new_phenotype_df['min_version'] = new_phenotype_df.groupby('id')['history_id'].transform('min')
    new_phenotype_df = new_phenotype_df[(new_phenotype_df.date >= start_date) &
                                        (new_phenotype_df.date <= end_date)]
    if brand > 0 :
        new_phenotype_df = new_phenotype_df[new_phenotype_df.brands.apply(lambda brand_list: isinstance(brand_list, list) and brand in brand_list)].copy()
    # Create new boolean columns
    new_phenotype_df['is_new'] = new_phenotype_df['history_id'] == new_phenotype_df['min_version']
    new_phenotype_df['is_edited'] = new_phenotype_df['history_id'] != new_phenotype_df['min_version']
    new_phenotype_df['is_published'] = new_phenotype_df['date'] == new_phenotype_df['publish_date']

    return new_phenotype_df


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
    start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

    tot_users_df = request_df[['date', 'user_id', 'remote_ip', 'brand']]
    tot_users_df = tot_users_df[(tot_users_df.brand == brand) & (tot_users_df.date >= start_date) &
                                (tot_users_df.date <= end_date)]
    return tot_users_df


def get_conn():
    """
    Function to get a PostgreSQL connection or SQLAlchemy engine.

    Args:
        use_engine (bool): If True, returns an SQLAlchemy engine instead of a raw psycopg2 connection.

    Returns:
        - If use_engine=True: Returns SQLAlchemy engine.
        - If use_engine=False: Returns psycopg2 connection and cursor.
    """
    config_params = {
        'host': os.getenv('POSTGRES_HOST'),
        'dbname': os.getenv('POSTGRES_DB'),
        'user': os.getenv('POSTGRES_USER'),
        'password': os.getenv('POSTGRES_PASSWORD'),
        'port': os.getenv('POSTGRES_PORT')
    }

    db_url = f"postgresql://{config_params['user']}:{config_params['password']}@{config_params['host']}:{config_params['port']}/{config_params['dbname']}"
    engine = create_engine(db_url)
    return engine
