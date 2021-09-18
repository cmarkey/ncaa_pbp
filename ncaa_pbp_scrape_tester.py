import csv
from bs4 import BeautifulSoup
import requests
import datetime
import time
from random import randint


# Assign headers to use with requests.get - this helps to avoid a permissions error
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.84 Safari/537.36',
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
}

def find_pbp_id(sched_id):
    '''
    The schedule uses a different game ID from the play by play report
    This function takes the schedule's game ID and returns the play by play game ID

    Inputs:
    sched_id - the schedule game ID for the game to scrape the PBP ID from

    Outputs:
    PBP game ID
    '''

    # Extracts the HTML from the URL for the specific game:
    url = "https://stats.ncaa.org/contests/{}/box_score".format(sched_id)
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    # Initialize empty list:
    game_data = []

    # Extract the PBP game ID
    try:
        find_list = soup.find_all("ul", class_="level2")[0]
        pbp_id = find_list.select('li')[0].find('a').attrs['href'][16:-12]
    except:
        find_list = soup.find_all("ul", class_="level1")[0]
        pbp_id = find_list.select('li')[0].find('a').attrs['href'][16:]

    # Return the PBP game ID
    return pbp_id

def pbp_scrape(game_id = None, event_list = None, game_no = None, filename1 = None):
    #need to specify a game ID or event_list needs to be a list of the schedule IDs
    #filename1 should be the desired name of the output file
    if game_id is not None and event_list is None:
        pbp_game_id = game_id
        event_id = None
    elif event_list is not None and game_id is None:
        event_id = event_list[game_no]
        # Pull the PBP game ID for the specified game
        pbp_game_id = find_pbp_id(event_id)
    else:
        print("Please input a game ID or an event list of schedule IDs")
    # Specify the PBP page to extract, and pull its source code:
    url = "https://stats.ncaa.org/game/play_by_play/{}".format(pbp_game_id)
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    # Extract the data from each period's table
    period1 = soup.find_all("table", class_="mytable")[1]
    period2 = soup.find_all("table", class_="mytable")[2]
    period3 = soup.find_all("table", class_="mytable")[3]
    if len(soup.find_all("table", class_="mytable")) > 4:
        period4 = soup.find_all("table", class_="mytable")[4]
    else:
        # This is a lazy fix to an error - period 4 gets ignored if there was no OT in the game
        period4 = soup.find_all("table", class_="mytable")[1]

    # Extract the individual rows from each table:
    # There's probably a way to combine all of these into one to reduce the later code
    p1rows = period1.find_all('tr')
    p2rows = period2.find_all('tr')
    p3rows = period3.find_all('tr')
    away_team = p1rows[0].select('tr > td')[1].get_text(strip=True)
    home_team = p1rows[0].select('tr > td')[3].get_text(strip=True)
    # Initialize empty list:
    all_plays = []

    # Add each row to the master list:
    for i in range(1, len(p1rows)-1):
        all_plays.append([str(event_id),pbp_game_id, home_team, away_team, 1, p1rows[i].select('tr > td')[2].get_text(strip=True)[0], p1rows[i].select('tr > td')[2].get_text(strip=True)[2], p1rows[i].select('tr > td')[0].get_text(strip=True), p1rows[i].select('tr > td')[1].get_text(strip=True), p1rows[i].select('tr > td')[3].get_text(strip=True)])
    for i in range(1, len(p2rows)-1):
        all_plays.append([str(event_id),pbp_game_id, home_team, away_team, 2, p2rows[i].select('tr > td')[2].get_text(strip=True)[0], p2rows[i].select('tr > td')[2].get_text(strip=True)[2], p2rows[i].select('tr > td')[0].get_text(strip=True), p2rows[i].select('tr > td')[1].get_text(strip=True), p2rows[i].select('tr > td')[3].get_text(strip=True)])
    for i in range(1, len(p3rows)-1):
        all_plays.append([str(event_id), pbp_game_id, home_team, away_team, 3, p3rows[i].select('tr > td')[2].get_text(strip=True)[0], p3rows[i].select('tr > td')[2].get_text(strip=True)[2], p3rows[i].select('tr > td')[0].get_text(strip=True) , p3rows[i].select('tr > td')[1].get_text(strip=True), p3rows[i].select('tr > td')[3].get_text(strip=True)])
    if len(soup.find_all("table", class_="mytable")) > 4:
        p4rows = period4.find_all('tr')
        for i in range(1, len(p4rows)-1):
            all_plays.append([str(event_id),pbp_game_id, home_team, away_team, 4, p4rows[i].select('tr > td')[2].get_text(strip=True)[0], p4rows[i].select('tr > td')[2].get_text(strip=True)[2], p4rows[i].select('tr > td')[0].get_text(strip=True), p4rows[i].select('tr > td')[1].get_text(strip=True), p4rows[i].select('tr > td')[3].get_text(strip=True)])

    if filename1 is not None:
        # Write the row data to a CSV file:
        with open(filename1, "a", encoding='utf-16') as f:
            writer = csv.writer(f, delimiter="|")
            writer.writerows(all_plays)
    else:
        return all_plays

def main():

    # Build a list of all of the games you would like to scrape, using the game IDs found in the schedule:
    event_list = [1990094, 1988207]

    # Name your output files, using today's date in the file names:
    today = "-" + datetime.date.today().strftime("%m-%d")
    filename1 = "ncaa-pbp" + today + ".csv"

    # Run the code for each game in the event_list
    game_no = 0

    while game_no < len(event_list):
        event_id = event_list[game_no]
        pbp_scrape(event_id, event_list, game_no, filename1)

        # Iterate to the next game:
        game_no = game_no + 1

        '''
        # Sleep for a few seconds to avoid overloading the server:
        time.sleep(randint(2,3))
        '''

        # Print the event_id and game_no so we can keep track of progress while the code runs:
        print(event_id)
        print(game_no)

if __name__ == '__main__':
    main()
