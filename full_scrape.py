# Import the required libraries
from bs4 import BeautifulSoup
import requests
from datetime import timedelta, date, datetime
import ncaa_pbp_scrape as pbp_scraper
import csv
from tqdm import tqdm
import os


def full_scrape(start_date, end_date, season_id, headers, schedule_filename=None, pbp_dir="./"):
    """
    :param date start_date: starting date to scrape (inclusive)
    :param date end_date: ending date to scrape (inclusive)
    :param int season_id: id of the seaosn to scrape (from schedule page URL)
    :param dict headers: headers to avoid permissions errors
    :param schedule_filename: filename for .csv of dates and event ids
    :type schedule_filename: str or None
    :param pbp_dir: directory path for where pbp files should go
    :type pbp_dir: str

    :return several .csvs of scraped games
    """

    # create any needed folders for pbp_dir
    if pbp_dir:
        if not os.path.exists(pbp_dir):
            os.makedirs(pbp_dir)
    else:
        pbp_dir = "./"

    # Initialize the date variable to iterate through
    current_date = start_date

    # Initialize an empty list to store our data in
    game_data = []

    # Run through the code for all dates in the date range
    print("Scrape Event IDs for Each Date")
    with tqdm(total = (end_date-start_date).days) as pbar:
        while current_date <= end_date:
            # Specify the URL using the current date in our loop
            url = f"https://stats.ncaa.org/season_divisions/{season_id}/scoreboards?game_date={current_date.month}%2F{current_date.day}%2F{current_date.year}"
            pbar.set_description(current_date.strftime('%m-%d-%Y'))

            # Pull the HTML from the URL
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.text, "html.parser")

            # If games exist, loop through the table rows. If games do not exist, skip this date
            try:
                # Find all the table rows
                game_rows = soup.find_all("tr")

                for i in range(1, len(game_rows)):
                    # All game URLs are stored in rows with four items in them, so ignore all other sizes of rows
                    if len(game_rows[i]) != 4:
                        pass
                    else:
                        # Add the current date you're scraping and the event ID to your list
                        game_data.append(
                            [
                                str(current_date),
                                game_rows[i]
                                .select("tr > td")[0]
                                .find("a")
                                .attrs["href"][10:]
                                .replace("/box_score", ""),
                            ]
                        )
            except:
                pass

            # Iterate to the next date
            pbar.update(1)
            current_date = current_date + timedelta(days=1)

    # scrape data
    pbp_scraper.run_full_scrape(game_data, pbp_dir)

    # Write the list of dates and event IDs to a CSV file
    if schedule_filename:
        with open(schedule_filename, "a", encoding="utf-16", newline="") as f:
            writer = csv.writer(f, delimiter=",")
            writer.writerows(game_data)

if __name__ == "__main__":
    # Assign headers to use with requests.get - this helps to avoid a permissions error
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.84 Safari/537.36",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    }

    # 2021-22 season id. Grab this from the URL on the schedule page. Ex: https://stats.ncaa.org/season_divisions/17460/scoreboards?
    SEASON_ID = 17800

    start_date = date(2021, 10, 9)
    end_date = date(2021, 10, 9)

    # OPTIONAL: if you want to save a csv of dates and event ids, indicate the filename here
    schedule_filename = None

    # OPTIONAL: if you want to save the pbp csv's in a directory, indicate it here
    # if not indicated, csv's will be saved to the current directory
    pbp_dir = "pbp"

    full_scrape(start_date, end_date, SEASON_ID, HEADERS, schedule_filename, pbp_dir)
