# Import the required libraries
from bs4 import BeautifulSoup
import requests
from datetime import timedelta, date, datetime
import ncaa_pbp_scrape as pbp_scraper
import csv
import pandas as pd


def scrape(start_date, end_date, season_id, headers):
    """
    :param start_date: starting date to scrape (inclusive)
    :param end_date: ending date to scrape (inclusive)
    :param season_id: id of the seaosn to scrape (from schedule page URL)
    :param headers: headers to avoid permissions errors

    :return several .csvs of scraped games
    """

    # Initialize the date variable to iterate through
    current_date = start_date

    # Initialize an empty list to store our data in
    game_data = []

    # Run through the code for all dates in the date range
    while current_date <= end_date:
        # Specify the URL using the current date in our loop
        url = f"https://stats.ncaa.org/season_divisions/{season_id}/scoreboards?game_date={current_date.month}%2F{current_date.day}%2F{current_date.year}"
        print("URL:", url)

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
                    # Add the current date you're scraping and the game ID to your list
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
            # Write the current date's list to a CSV file
            # only useful if caching this information
            # with open(file_name, "a", encoding="utf-16", newline="") as f:
            #     writer = csv.writer(f, delimiter=",")
            #     writer.writerows(game_data)
        except:
            pass

        # Iterate to the next date
        current_date = current_date + timedelta(days=1)
        pbp_scraper.run_full_scrape(game_data)


if __name__ == "__main__":
    # Assign headers to use with requests.get - this helps to avoid a permissions error
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.84 Safari/537.36",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    }

    # 2021-22 season id. Grab this from the URL on the schedule page. Ex: https://stats.ncaa.org/season_divisions/17460/scoreboards?
    SEASON_ID = 17800
    
    start_date = date(2021, 9, 24)
    end_date = date(2021, 9, 24)
    scrape(start_date, end_date, SEASON_ID, HEADERS)
