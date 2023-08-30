import datetime
from typing import Union

import pandas as pd
from google.cloud import bigquery, exceptions

from scrape.scraper import ScrapeResult

from .config import BigQueryConfig


def check_dataset_exists(
    dataset_id: str,
    bigquery_client: bigquery.Client,
) -> bool:
    try:
        bigquery_client.get_dataset(dataset_id)
        return True
    except exceptions.NotFound:
        return False


def check_table_exists(
    table: Union[
        bigquery.Table,
        bigquery.TableReference,
        str,
    ],
    bigquery_client: bigquery.Client,
) -> bool:
    try:
        bigquery_client.get_table(table)
        return True
    except exceptions.NotFound:
        return False


def last_execution(url: str, bigquery_config: BigQueryConfig) -> datetime.date:
    query = f"""
        SELECT MAX(scraping_date) as last_execution
        FROM `{bigquery_config.code_table!s}`
        INNER JOIN `{bigquery_config.website_table!s}` USING (website_id)
        WHERE url = '{url}'
        """
    try:
        job = bigquery_config.client.query(query)
        return next(job.result()).last_execution
    except exceptions.NotFound:
        print("Not found.")
        return


def download_previous_codes(
    url: str, bigquery_config: BigQueryConfig
) -> pd.DataFrame:
    query = f"""
        SELECT *
        FROM `{bigquery_config.code_table!s}`
        INNER JOIN `{bigquery_config.website_table!s}`
        USING (website_id)
        WHERE
            url = '{url}'
            AND scraping_date = (
                SELECT MAX(scraping_date)
                FROM `{bigquery_config.code_table!s}`
            )
        """
    return bigquery_config.client.query(query).to_dataframe()


def upload_website_data(
    result: ScrapeResult, bigquery_config: BigQueryConfig
) -> None:
    query = f"""
    INSERT INTO `{bigquery_config.website_table!s}` (
        website_id, website_name, website_name_clean, url
    )
    WITH t as (
    SELECT
        {result.website_id!r} website_id
        , {result.website_name!r}
        , {result.website_name_clean!r}
        , {result.url!r}
    )
    SELECT * FROM t WHERE NOT EXISTS (
        SELECT *
        FROM `{bigquery_config.website_table!s}` w
        WHERE w.website_id = t.website_id
    )
    """
    bigquery_config.client.query(query)


def upload_scrape_result(
    result: ScrapeResult, bigquery_config: BigQueryConfig
) -> None:
    # vérifie que les tables existent
    for table in (bigquery_config.code_table, bigquery_config.website_table):
        if not check_table_exists(table, bigquery_config.client):
            if bigquery_config.create_table_if_needed:
                bigquery_config.client.create_table(table)
            else:
                raise ValueError(f"Table '{table!s}' does not exist.")

    # charge les données du site
    upload_website_data(result=result, bigquery_config=bigquery_config)

    # charge les données des codes
    bigquery_config.client.load_table_from_dataframe(
        dataframe=result.codes_db_format,
        destination=bigquery_config.code_table,
    )
