import csv
from bs4 import BeautifulSoup
import requests
import datetime
import time
from random import randint
import regex as re
import pandas as pd


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

def pbp_scrape(date, event_list, game_no, dir=None):
    #filename1 should be the desired name of the output file
    event_id = event_list[game_no]
    # Pull the PBP game ID for the specified game
    pbp_game_id = find_pbp_id(event_id)
    filename = str(date)+"_"+str(event_id)+".csv"
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
        all_plays.append([str(date),pbp_game_id, home_team, away_team, 1, p1rows[i].select('tr > td')[2].get_text(strip=True)[0], p1rows[i].select('tr > td')[2].get_text(strip=True)[2], p1rows[i].select('tr > td')[0].get_text(strip=True), p1rows[i].select('tr > td')[1].get_text(strip=True), p1rows[i].select('tr > td')[3].get_text(strip=True)])
    for i in range(1, len(p2rows)-1):
        all_plays.append([str(date),pbp_game_id, home_team, away_team, 2, p2rows[i].select('tr > td')[2].get_text(strip=True)[0], p2rows[i].select('tr > td')[2].get_text(strip=True)[2], p2rows[i].select('tr > td')[0].get_text(strip=True), p2rows[i].select('tr > td')[1].get_text(strip=True), p2rows[i].select('tr > td')[3].get_text(strip=True)])
    for i in range(1, len(p3rows)-1):
        all_plays.append([str(date), pbp_game_id, home_team, away_team, 3, p3rows[i].select('tr > td')[2].get_text(strip=True)[0], p3rows[i].select('tr > td')[2].get_text(strip=True)[2], p3rows[i].select('tr > td')[0].get_text(strip=True) , p3rows[i].select('tr > td')[1].get_text(strip=True), p3rows[i].select('tr > td')[3].get_text(strip=True)])
    if len(soup.find_all("table", class_="mytable")) > 4:
        p4rows = period4.find_all('tr')
        for i in range(1, len(p4rows)-1):
            all_plays.append([str(date),pbp_game_id, home_team, away_team, 4, p4rows[i].select('tr > td')[2].get_text(strip=True)[0], p4rows[i].select('tr > td')[2].get_text(strip=True)[2], p4rows[i].select('tr > td')[0].get_text(strip=True), p4rows[i].select('tr > td')[1].get_text(strip=True), p4rows[i].select('tr > td')[3].get_text(strip=True)])

    clean_pbp = parse_pbp(all_plays)

    clean_pbp.to_csv(filename,index=False)

def parse_pbp(raw_pbp):
    #setting the list pbp as a dataframe
    pbp_unorganized_df = pd.DataFrame(raw_pbp, columns=['Date','Game ID', 'Home Team','Away Team','Period', 'Home Team Goals', 'Away Team Goals', 'Clock', 'Away Team Event', 'Home Team Event'])

    #filtering out pbp lines that have no impact on play or the interpretation of other events
    #this code chunk has to be here otherwise the rest of the code breaks
    unwanted_pbp = ['Timeout', 'Shootout', 'Start power play for']
    pbp_unorganized_df['Event'] = pbp_unorganized_df['Home Team Event']+pbp_unorganized_df['Away Team Event']
    pbp_filter = pbp_unorganized_df['Event'].str.contains('|'.join(unwanted_pbp), case=False)
    pbp_unorganized_df = pbp_unorganized_df[~pbp_filter]
    pbp_organized_df = pd.DataFrame(columns = ['Date','Game ID', 'Home Team','Away Team','Period', 'Home Team Goals', 'Away Team Goals', 'Clock', 'Home Team Players','Away Team Players', 'Team', 'Event','Player','Detail 1','Detail 2','Player 2', 'Goalie'])
    pbp_organized_df[['Date','Game ID', 'Home Team','Away Team','Period', 'Home Team Goals', 'Away Team Goals', 'Clock']] = pbp_unorganized_df[['Date','Game ID', 'Home Team','Away Team','Period', 'Home Team Goals', 'Away Team Goals', 'Clock']]

    #Set team who created event
    pbp_organized_df.loc[pbp_unorganized_df['Away Team Event'] == '', 'Team'] = pbp_organized_df['Home Team']
    pbp_organized_df.loc[pbp_unorganized_df['Home Team Event'] == '', 'Team'] = pbp_organized_df['Away Team']
    pbp_unorganized_df['Event'] = pbp_unorganized_df['Home Team Event']+pbp_unorganized_df['Away Team Event']

    #set even strength as default
    pbp_organized_df['Home Team Players'] = 5
    pbp_organized_df['Away Team Players'] = 5

    #Clock formatting
    if pbp_organized_df['Clock'].any(axis=0) != "00:00":
        pbp_organized_df['Clock'] = pd.to_datetime(pbp_organized_df['Clock'], format="%M:%S:%f")

    #some games do not have time stamps for all events. In this case, the empty clock times are set to 00:00
    else:
        pbp_organized_df.loc[pbp_organized_df['Clock'] == '','Clock'] = "00:00"
        pbp_organized_df['Clock'] = pd.to_datetime(pbp_organized_df['Clock'], format="%M:%S")

    #parsing events, each code chunk is a type of event
    #shots, shot type, shooting player, blocking player if blocked, saving goalie if missed
    shot_phrases = ['Shot']
    shot_types = ['Missed', 'Wide', 'Blocked']
    pbp_organized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(shot_phrases), case=False), 'Event'] = 'Shot'
    for type in shot_types:
        pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Shot') & (pbp_unorganized_df['Event'].str.contains(type, case=False)), 'Detail 1'] = type
    #format 1
    if ((pbp_organized_df['Event'] == 'Shot') & pbp_unorganized_df['Event'].str.contains('\(')).any(axis=0) == True:
        pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Shot'), 'Player'] = pbp_unorganized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(shot_phrases), case=False), 'Event'].str.extract(r"Shot by (.*)\(\w+\)", flags=re.IGNORECASE)[0]
        pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Shot'), 'Goalie'] = pbp_unorganized_df.loc[(pbp_organized_df['Event'] == 'Shot'), 'Event'].str.extract(r"save (.*)", flags=re.IGNORECASE)[0]
        pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Shot'), 'Player 2'] = pbp_unorganized_df.loc[(pbp_organized_df['Event'] == 'Shot'), 'Event'].str.extract(r"BLOCKED by (.*)", flags=re.IGNORECASE)[0]
    #format 2
    #elif len(((pbp_organized_df['Event'] == 'Shot') & pbp_unorganized_df['Event'].str.contains('\,')) :
    #    pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Shot'), 'Player'] = pbp_unorganized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(shot_phrases), case=False), 'Event'].str.split().str[3] + " "+pbp_unorganized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(shot_phrases), case=False), 'Event'].str.split(' |\(').str[4]
    #    pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Shot') & (pbp_organized_df['Detail 1'] == 'Missed'), 'Goalie'] = pbp_unorganized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(shot_phrases), case=False) & pbp_unorganized_df['Event'].str.contains('save', case=False), 'Event'].str.split('\.| ').str[-3] + " "+pbp_unorganized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(shot_phrases), case=False) & pbp_unorganized_df['Event'].str.contains('save', case=False), #'Event'].str.split('\.| ').str[-2]
    #    pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Shot') & (pbp_organized_df['Detail 1'] == 'Blocked'), 'Player 2'] = pbp_unorganized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(shot_phrases), case=False) & pbp_unorganized_df['Event'].str.contains('blocked', case=False), 'Event'].str.split('\.| ').str[-3] + " "+pbp_unorganized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(shot_phrases), case=False) & pbp_unorganized_df['Event'].str.contains('blocked', case=False), #'Event'].str.split('\.| ').str[-2]

    #faceoff parsing
    faceoff_phrases = ['Faceoff', 'Face off']
    pbp_organized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(faceoff_phrases), case=False), 'Event'] = 'Faceoff Won'
    #format 1
    if ((pbp_organized_df['Event'] == 'Faceoff Won') & pbp_unorganized_df['Event'].str.contains('\(')).any(axis=0) == True:
        #setting Player as winner of faceoff
        pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Faceoff Won'), 'Player'] = pbp_unorganized_df.loc[pbp_organized_df['Event']=='Faceoff Won', 'Event'].str.extract(r"Faceoff (.*) vs (.*), won by (.*)\s?\(\w+\)", flags=re.IGNORECASE)[2]
        #setting the losers as Player 2
        away_faceoff_players = pbp_unorganized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(faceoff_phrases), case=False),'Event'].str.extract(r"Faceoff (.*) vs (.*), won by (.*)\s?\(\w+\)", flags=re.IGNORECASE)[0]
        home_faceoff_players = pbp_unorganized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(faceoff_phrases), case=False),'Event'].str.extract(r"Faceoff (.*) vs (.*), won by (.*)\s?\(\w+\)", flags=re.IGNORECASE)[1]
        faceoff_home_loser = ((pbp_organized_df['Team'] == pbp_organized_df['Away Team']) & (pbp_organized_df['Event'] == 'Faceoff Won'))
        faceoff_away_loser = ((pbp_organized_df['Team'] == pbp_organized_df['Home Team']) & (pbp_organized_df['Event'] == 'Faceoff Won'))
        pbp_organized_df.loc[faceoff_home_loser, 'Player 2'] = home_faceoff_players
        pbp_organized_df.loc[faceoff_away_loser, 'Player 2'] = away_faceoff_players

    #goal parsing
    goal_phrases = ['Goal ']
    pbp_organized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(goal_phrases), case=False), 'Event'] = 'Goal'
    #format 1
    if ((pbp_organized_df['Event'] == 'Goal') & pbp_unorganized_df['Event'].str.contains('\(')).any(axis=0) == True:
        pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Goal'), 'Player'] = pbp_unorganized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(goal_phrases), case=False), 'Event'].str.extract(r"GOAL by (.*) \s?\(\w+\)", flags=re.IGNORECASE)[0]
        #1st assist
        assists = pbp_unorganized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(goal_phrases), case=False), 'Event'].str.extract(r"GOAL by (.*) \s?\(\w+\),\s?Assist by (.*) On ice for \w+: On ice for \w+:", flags=re.IGNORECASE)[1]
        assists = assists[assists.notna()]
        #1st assist if it exists
        pbp_organized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(goal_phrases), case=False) & pbp_unorganized_df['Event'].str.contains('and'), 'Detail 1'] = assists.str.extract(r"(.*) and (.*),", flags=re.IGNORECASE)[0]
        if pbp_organized_df.loc[(pbp_unorganized_df['Event'].str.contains('|'.join(goal_phrases), case=False)) & (~pbp_unorganized_df['Event'].str.contains('and')) & (assists.notna())].empty == False:
            pbp_organized_df.loc[(pbp_unorganized_df['Event'].str.contains('|'.join(goal_phrases), case=False)) & (~pbp_unorganized_df['Event'].str.contains('and')) & (assists.notna()), 'Detail 1'] = assists.str.extract(r"(.*)", flags=re.IGNORECASE)[0]
        #2nd assist if it exists
        pbp_organized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(goal_phrases), case=False) & pbp_unorganized_df['Event'].str.contains('and'), 'Detail 2'] = assists.str.extract(r"(.*) and (.*),", flags=re.IGNORECASE)[1]


    #shootout parsing
    #shootout_phrases = ['Shootout']
    #shootout_types = ['Made', 'Wide', 'Missed']
    #pbp_organized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(shootout_phrases), case=False), 'Event'] = 'Shootout Attempt'
    #for type in shootout_types:
    #    pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Shootout Attempt') & (pbp_unorganized_df['Event'].str.contains(type, case=False)), 'Detail 1'] = type
    ##format 1
    #if ((pbp_organized_df['Event'] == 'Shootout Attempt') & pbp_unorganized_df['Event'].str.contains('\(')).any(axis=0) == True:
    #    pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Shootout Attempt'), 'Player'] = pbp_unorganized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(shootout_phrases), case=False), 'Event'].str.extract(r"(.*) and (.*),", flags=re.IGNORECASE)[1]
    #    pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Shootout Attempt'), 'Player'] = pbp_unorganized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(shootout_phrases), case=False), 'Event'].str.split(' |\(').str[2] + " "+pbp_unorganized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(shootout_phrases), case=False), 'Event'].str.split(' |\(').str[3]
    #    pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Shootout Attempt') & (pbp_organized_df['Detail 1'] == 'Missed'), 'Goalie'] = pbp_unorganized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(shootout_phrases), case=False), 'Event'].str.split(' |\(').str[-2] + " "+pbp_unorganized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(shootout_phrases), case=False), 'Event'].str.split(' |\(').str[-1]
    #    pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Shootout Attempt') & (pbp_organized_df['Detail 1'] == 'Wide'), 'Goalie'] = pbp_unorganized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(shootout_phrases), case=False), 'Event'].str.split(' |\(').str[-2] + " "+pbp_unorganized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(shootout_phrases), case=False), 'Event'].str.split(' |\(').str[-1]
    #    pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Shootout Attempt') & (pbp_organized_df['Detail 1'] == 'Made'), 'Goalie'] = pbp_unorganized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(shootout_phrases), case=False), 'Event'].str.split(' |\(').str[-2] + " "+pbp_unorganized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(shootout_phrases), case=False), 'Event'].str.split(' |\(').str[-1]

    #goalie shenanigans
    goalie_in_phrases = ['at net', 'Goalie sub in']
    goalie_pull_phrases = ['Goalie sub out']
    pbp_organized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(goalie_in_phrases), case=False), 'Event'] = 'Goalie in net'
    pbp_organized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(goalie_pull_phrases), case=False), 'Event'] = 'Goalie sub out'
    if ((pbp_organized_df['Event'] == 'Goalie in net') & pbp_unorganized_df['Event'].str.contains('\(')).any(axis=0) == True:
        pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Goalie in net'), 'Player'] = pbp_unorganized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(goalie_in_phrases), case=False), 'Event'].str.extract(r"Goalie sub \w+ (.*)\s?\(\w+\)", flags=re.IGNORECASE)[0]
    if ((pbp_organized_df['Event'] == 'Goalie sub out') & pbp_unorganized_df['Event'].str.contains('\(')).any(axis=0) == True:
        pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Goalie sub out'), 'Player'] = pbp_unorganized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(goalie_pull_phrases), case=False), 'Event'].str.extract(r"Goalie sub \w+ (.*)\s?\(\w+\)", flags=re.IGNORECASE)[0]

    #Penalties + empty net + strength calculations
    player_penalty_phrases = ['Minor penalty', 'Major Penalty', 'Penalty on']
    game_misconduct_phrases = ['Gamemisconduct']
    team_penalty_phrases = ['Benchminor', 'Benchgamemisconduct']
    #player penalties
    pbp_organized_df.loc[(pbp_unorganized_df['Event'].str.contains('|'.join(player_penalty_phrases))), 'Event'] = 'Player Penalty'
    if ((pbp_organized_df['Event'] == 'Player Penalty') & pbp_unorganized_df['Event'].str.contains('\(')).any(axis=0) == True:
        #first format is if penalized player is serving penalty, second format is if another player is serving the penalty
        pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Player Penalty')& (~pbp_unorganized_df['Event'].str.contains('serving penalty')), 'Player'] = pbp_unorganized_df.loc[(pbp_unorganized_df['Event'].str.contains('|'.join(player_penalty_phrases)))& (~pbp_unorganized_df['Event'].str.contains('serving penalty')), 'Event'].str.extract(r"Penalty on (.*)\s?\(\w+\) for (.*);duration:(.*)", flags=re.IGNORECASE)[0].str.title()
        pbp_organized_df.loc[(pbp_unorganized_df['Event'].str.contains('|'.join(player_penalty_phrases)))& (pbp_unorganized_df['Event'].str.contains('serving penalty')), 'Player'] = pbp_unorganized_df.loc[(pbp_unorganized_df['Event'].str.contains('|'.join(player_penalty_phrases)))& (pbp_unorganized_df['Event'].str.contains('serving penalty')), 'Event'].str.extract(r"Penalty on (.*)\s?\(\w+\) for (.*);duration:(.*), (.*),(.*) serving penalty", flags=re.IGNORECASE)[0].str.title() +pbp_unorganized_df.loc[(pbp_unorganized_df['Event'].str.contains('|'.join(player_penalty_phrases)))& (pbp_unorganized_df['Event'].str.contains('serving penalty')), 'Event'].str.extract(r"Penalty on (.*)\s?\(\w+\) for (.*);duration:(.*), (.*),(.*) serving penalty", flags=re.IGNORECASE)[3].str.title()
        #print(pbp_unorganized_df.loc[(pbp_unorganized_df['Event'].str.contains('|'.join(player_penalty_phrases)))& (pbp_unorganized_df['Event'].str.contains('serving penalty')), 'Event'].str.extract(r"Penalty on (.*)\s?\(\w+\) for (.*);duration:(.*), (.*),(.*) serving penalty", flags=re.IGNORECASE)[0].str.title() +pbp_unorganized_df.loc[(pbp_unorganized_df['Event'].str.contains('|'.join(player_penalty_phrases)))& (~pbp_unorganized_df['Event'].str.contains('serving penalty')), 'Event'].str.extract(r"Penalty on (.*)\s?\(\w+\) for (.*);duration:(.*), (.*),(.*) serving penalty", flags=re.IGNORECASE)[3].str.title())
        pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Player Penalty'), 'Detail 1'] = pbp_unorganized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(player_penalty_phrases)), 'Event'].str.extract(r"Penalty on (.*)\s?\(\w+\) for (.*);duration:(.*)", flags=re.IGNORECASE)[1].str.title()
        pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Player Penalty')& (~pbp_unorganized_df['Event'].str.contains('serving penalty')), 'Detail 2'] = pbp_unorganized_df.loc[(pbp_unorganized_df['Event'].str.contains('|'.join(player_penalty_phrases)))& (~pbp_unorganized_df['Event'].str.contains('serving penalty')), 'Event'].str.extract(r"Penalty on (.*)\s?\(\w+\) for (.*);duration:(.*)", flags=re.IGNORECASE)[2]
        pbp_organized_df.loc[(pbp_unorganized_df['Event'].str.contains('|'.join(player_penalty_phrases)))& (pbp_unorganized_df['Event'].str.contains('serving penalty')), 'Detail 2'] = pbp_unorganized_df.loc[(pbp_unorganized_df['Event'].str.contains('|'.join(player_penalty_phrases)))& (pbp_unorganized_df['Event'].str.contains('serving penalty')), 'Event'].str.extract(r"Penalty on (.*)\s?\(\w+\) for (.*);duration:(.*), (.*),(.*) serving penalty", flags=re.IGNORECASE)[2]
        #iterating through each team's penalties by period and calculating strength
        for team in ['Home Team', 'Away Team']:
            for period in [1,2,3,4]:
                penalty_min = list(pbp_organized_df[(pbp_organized_df['Event'] == 'Player Penalty') & (pbp_organized_df['Period'] == period)&(pbp_organized_df['Team'] == pbp_organized_df[team])]['Clock'])
                pp_end = list(pbp_organized_df[(pbp_organized_df['Event'] == 'Player Penalty') & (pbp_organized_df['Period'] == period)&(pbp_organized_df['Team'] == pbp_organized_df[team])]['Clock']-pd.to_timedelta(pd.to_numeric(pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Player Penalty') & (pbp_organized_df['Period'] == period)&(pbp_organized_df['Team'] == pbp_organized_df[team]), 'Detail 2']), unit='m'))
                for i in range(len(pp_end)):
                    pbp_organized_df.loc[(pbp_organized_df['Period'] == period) & (pbp_organized_df['Clock'] > pp_end[i]) & (penalty_min[i] >= pbp_organized_df['Clock']), team+' Players'] -= 1
                    if ((pbp_organized_df['Event'] == 'Goal')&(pbp_organized_df['Team'] !=  pbp_organized_df[team])& (pbp_organized_df['Clock'] > pp_end[i]) & (penalty_min[i] >= pbp_organized_df['Clock'])).any(axis=0) == True:
                        goal_time = list(pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Goal')&(pbp_organized_df['Team'] != pbp_organized_df[team])& (pbp_organized_df['Clock'] > pp_end[i]) & (penalty_min[i] >= pbp_organized_df['Clock']),'Clock'])
                        pbp_organized_df.loc[(pbp_organized_df['Period'] == period) & (pbp_organized_df['Clock'] > pp_end[i]) & (goal_time[0] == pbp_organized_df['Clock']), team+' Players'] = 5
                        pbp_organized_df.loc[(pbp_organized_df['Period'] == period) & (pbp_organized_df['Clock'] > pp_end[i]) & (goal_time[0] >= pbp_organized_df['Clock']), team+' Players'] = 5
            pbp_organized_df.loc[(pbp_organized_df[team+' Players'] < 3),team+' Players'] = 3
    #print(pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Player Penalty')])

    #team penalties
    pbp_organized_df.loc[(pbp_unorganized_df['Event'].str.contains('|'.join(team_penalty_phrases))), 'Event'] = 'Team Penalty'
    #print(pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Team Penalty')])
    if ((pbp_organized_df['Event'] == 'Team Penalty') & pbp_unorganized_df['Event'].str.contains('\(')).any(axis=0) == True:
        #setting player who served penalty + penalty + duration
        first = pbp_unorganized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(team_penalty_phrases)), 'Event'].str.extract(r"Penalty on Team\(\w+\) for (.*);duration:(.*), (.*),(.*) serving penalty", flags=re.IGNORECASE)[3].str.title()
        last = pbp_unorganized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(team_penalty_phrases)), 'Event'].str.extract(r"Penalty on Team\(\w+\) for (.*);duration:(.*), (.*),(.*) serving penalty", flags=re.IGNORECASE)[2].str.title()
        pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Team Penalty'), 'Player'] = first+" "+last
        pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Team Penalty'), 'Detail 1'] = pbp_unorganized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(team_penalty_phrases), case=False), 'Event'].str.extract(r"Penalty on Team\(\w+\) for (.*);duration:(.*), (.*),(.*) serving penalty", flags=re.IGNORECASE)[0].str.title()
        pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Team Penalty'), 'Detail 2'] = pbp_unorganized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(team_penalty_phrases), case=False), 'Event'].str.extract(r"Penalty on Team\(\w+\) for (.*);duration:(.*), (.*),(.*) serving penalty", flags=re.IGNORECASE)[1].str.title()
    #    print(pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Team Penalty'), 'Player'])
        #iterating through each team's penalties by period and calculating strength
        for team in ['Home Team', 'Away Team']:
            for period in [1,2,3,4]:
                penalty_min = list(pbp_organized_df[(pbp_organized_df['Event'] == 'Team Penalty') & (pbp_organized_df['Period'] == period)&(pbp_organized_df['Team'] == pbp_organized_df[team])]['Clock'])
                pp_end = list(pbp_organized_df[(pbp_organized_df['Event'] == 'Team Penalty') & (pbp_organized_df['Period'] == period)&(pbp_organized_df['Team'] == pbp_organized_df[team])]['Clock']-pd.to_timedelta(pd.to_numeric(pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Team Penalty') & (pbp_organized_df['Period'] == period)&(pbp_organized_df['Team'] == pbp_organized_df[team]), 'Detail 2']), unit='m'))
                for i in range(len(pp_end)):
                    pbp_organized_df.loc[(pbp_organized_df['Period'] == period) & (pbp_organized_df['Clock'] > pp_end[i]) & (penalty_min[i] >= pbp_organized_df['Clock']), team+' Players'] -= 1
                    if ((pbp_organized_df['Event'] == 'Goal')&(pbp_organized_df['Team'] !=  pbp_organized_df[team])& (pbp_organized_df['Clock'] > pp_end[i]) & (penalty_min[i] >= pbp_organized_df['Clock'])).any(axis=0) == True:
                        goal_time = list(pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Goal')&(pbp_organized_df['Team'] != pbp_organized_df[team])& (pbp_organized_df['Clock'] > pp_end[i]) & (penalty_min[i] >= pbp_organized_df['Clock']),'Clock'])
                        pbp_organized_df.loc[(pbp_organized_df['Period'] == period) & (pbp_organized_df['Clock'] > pp_end[i]) & (goal_time[0] == pbp_organized_df['Clock']), team+' Players'] = 5
                        pbp_organized_df.loc[(pbp_organized_df['Period'] == period) & (pbp_organized_df['Clock'] > pp_end[i]) & (goal_time[0] >= pbp_organized_df['Clock']), team+' Players'] = 5
            pbp_organized_df.loc[(pbp_organized_df[team+' Players'] < 3),team+' Players'] = 3
    #print(pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Team Penalty')])

    #empty_net_phrases = ['Empty Net']
    #pbp_organized_df.loc[(pbp_unorganized_df['Event'].str.contains('|'.join(empty_net_phrases), case=False), 'Event'] = 'Empty Net'
    #if ((pbp_organized_df['Event'] == 'Empty Net') & pbp_unorganized_df['Event'].str.contains('\(')).any(axis=0) == True:
    #    print('z')

    #clock formatting
    pbp_organized_df['Clock'] = pbp_organized_df['Clock'].dt.time

    #pbp_organized_df.to_csv('test_pbp.csv',index=False)

    return pbp_organized_df

def run_full_scrape(games):

    # Build a list of all of the games you would like to scrape, using the game IDs found in the schedule:
    event_list = games[1]
    dates = games[0]

    # Name your output files, using today's date in the file names:
    today = "-" + datetime.date.today().strftime("%m-%d")
    filename1 = "ncaa-pbp" + today + ".csv"

    # Run the code for each game in the event_list
    game_no = 0

    while game_no < len(event_list):
        event_id = event_list.loc[game_no]
        date = dates[game_no]
        pbp_scrape(date, event_list, game_no, filename1)

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
