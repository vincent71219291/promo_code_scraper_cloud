import datetime

from google.cloud import exceptions

from scrape.alert import create_alert, send_mail
from scrape.codes import select_new_codes
from scrape.config import (
    load_browser_options,
    load_scrape_config_from_storage,
    read_cloud_config,
)
from scrape.driver import init_driver
from scrape.html import df_to_html
from scrape.queries import download_previous_codes, last_execution, upload_scrape_result
from scrape.scraper import CodeScraper
from scrape.secrets import get_secret_string


def main():
    # importe les paramètres de configuration des services Google Cloud
    cloud_config = read_cloud_config("./cloud_config.json")

    # télécharge et importe les paramètres de configuration du script
    scrape_config = load_scrape_config_from_storage(cloud_config.storage)

    # vérifie que le script n'a pas déjà été exécuté aujourd'hui
    last_exec_date = last_execution(
        url=scrape_config.url, bigquery_config=cloud_config.bigquery
    )
    today = datetime.date.today()
    if last_exec_date == today:
        print(f"Script was already executed today ({today}). Ending script.")
        return

    options = load_browser_options(cloud_config.storage)
    driver = init_driver(options=options)

    # scrape les codes promo
    scraper = CodeScraper(driver, scrape_config.url)
    result = scraper.scrape()
    scraper.close_driver()

    # récupère les anciens codes et recherche les codes originaux
    print("Attempting to retrieve previous codes...")
    try:
        previous_codes = download_previous_codes(
            url=scrape_config.url, bigquery_config=cloud_config.bigquery
        )
        new_codes = select_new_codes(
            current_codes=result.codes,
            previous_codes=previous_codes,
            threshold=scrape_config.min_discount,
        )
        print("Done.")
    except exceptions.NotFound:
        print("No previous codes found.")
        new_codes = result.codes

    # sauvegarde les codes actifs dans la BDD
    print("Uploading scraping data...")
    upload_scrape_result(result, bigquery_config=cloud_config.bigquery)
    print("Done.")

    # envoie une alerte email ou non selon les paramètres de configuration
    if not scrape_config.send_alert:
        print("Sending alert is off.")
    else:
        if new_codes.empty:
            print("No new codes found. No alerts were sent.")
        else:
            try:
                user = get_secret_string("EMAIL_USER", cloud_config.storage.project_id)
                password = get_secret_string(
                    "EMAIL_PASS", cloud_config.storage.project_id
                )

            except NameError:
                print("Email user or password not found.")
                raise

            df_html = df_to_html(result.codes_human_readable, new_codes.index)
            alert = create_alert(
                sender=user,
                receiver=user,
                website=result.website_name,
                table=df_html,
            )
            send_mail(sender=user, password=password, receiver=user, message=alert)
            print(f"Alert sent to {user!r}.")


if __name__ == "__main__":
    main()
