import json
from dataclasses import dataclass, field

from google.cloud import bigquery, storage


@dataclass
class StorageConfig:
    project_id: str
    client: storage.Client = field(init=False)
    bucket_name: str
    scrape_config_path: str

    def __post_init__(self):
        self.client = storage.Client(project=self.project_id)


@dataclass
class BigQueryConfig:
    project_id: str
    client: bigquery.Client = field(init=False)
    dataset_id: str
    _code_table: dict
    _website_table: dict
    create_table_if_needed: bool = False

    def __post_init__(self):
        self.client = bigquery.Client(project=self.project_id)

    @property
    def code_table(self) -> bigquery.Table:
        table_id = self._code_table["table_id"]
        table_ref = f"{self.project_id}.{self.dataset_id}.{table_id}"
        schema = self.create_schema(self._code_table["fields"])
        return bigquery.Table(table_ref, schema)

    @property
    def website_table(self) -> bigquery.Table:
        table_id = self._website_table["table_id"]
        table_ref = f"{self.project_id}.{self.dataset_id}.{table_id}"
        schema = self.create_schema(self._website_table["fields"])
        return bigquery.Table(table_ref, schema)

    @staticmethod
    def create_schema(fields: dict[str, str]):
        return [bigquery.SchemaField(**field) for field in fields]


@dataclass
class GoogleCloudConfig:
    storage: StorageConfig
    bigquery: BigQueryConfig


@dataclass
class ScrapeConfig:
    url: str
    send_alert: bool
    min_discount: int


def read_cloud_config(config_file: str) -> GoogleCloudConfig:
    with open(config_file) as file:
        data = json.load(file)
    storage_config = StorageConfig(**data["storage"])
    bigquery_config = BigQueryConfig(**data["bigquery"])
    return GoogleCloudConfig(storage=storage_config, bigquery=bigquery_config)


def load_scrape_config_from_storage(storage_config: StorageConfig):
    bucket = storage_config.client.get_bucket(storage_config.bucket_name)
    blob = bucket.blob(storage_config.scrape_config_path)

    with blob.open(mode="rb") as file:
        data = json.load(file)

    return ScrapeConfig(**data)
