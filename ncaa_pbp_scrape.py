import csv
from bs4 import BeautifulSoup
import requests
import datetime
import time
from random import randint
import regex as re
import pandas as pd
from tqdm import tqdm
import os

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
    url = f"https://stats.ncaa.org/contests/{sched_id}/box_score"
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

def pbp_scrape(date, event_id, dir):
    """
    :param date date: the date of the game being scraped
    :param str event_id: the event id of the game being scraped
    :param str dir: the filepath of the directory where the pbp should be stored
    """
    # Pull the PBP game ID for the specified game
    pbp_game_id = find_pbp_id(event_id)

    # get the filename for the output
    filename = os.path.join(dir, f"{date}_{event_id}.csv")

    # Specify the PBP page to extract, and pull its source code:
    url = f"https://stats.ncaa.org/game/play_by_play/{pbp_game_id}"
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    # Extract the data from each period's table
    nested_periods = [period.find_all('tr') for period in soup.find_all("table", class_="mytable")[1:]]

    # Extract home and away team names
    [_, away_team, _, home_team] = [td.get_text(strip=True) for td in nested_periods[0][0].select('tr>td')]

    all_plays = []

    def processRow(row, period_no):
        [clock_time, event, score, extra] = [element.get_text(strip=True) for element in row.select('tr>td')]
        [home_score, away_score] = score.split("-")
        return [date, pbp_game_id, home_team, away_team, period_no, home_score, away_score, clock_time, event, extra]

    # ignore first row (the one with the teams, time, etc and last row (period end)
    for i, period in enumerate(nested_periods):
        all_plays += [processRow(row, i+1) for row in period[1:-1]]

    clean_pbp = parse_pbp(all_plays)

    clean_pbp.to_csv(filename,index=False)

def parse_pbp(raw_pbp):
    #setting the list pbp as a dataframe
    pbp_unorganized_df = pd.DataFrame(raw_pbp, columns=['Date','Game ID', 'Home Team','Away Team','Period', 'Home Team Goals', 'Away Team Goals', 'Clock', 'Away Team Event', 'Home Team Event'])

    #filtering out pbp lines that have no impact on play, and no impact the interpretation of other events
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

    if ~(((pbp_organized_df['Home Team Goals'].str.contains('-')).any(axis=0) == True) | ((pbp_organized_df['Away Team Goals'].str.contains('-')).any(axis=0) == True)):
        pbp_organized_df['Home Team Goals'] = pd.to_numeric(pbp_organized_df['Home Team Goals'])
        pbp_organized_df['Away Team Goals'] = pd.to_numeric(pbp_organized_df['Away Team Goals'])


    #set even strength as default
    pbp_organized_df['Home Team Players'] = 5
    pbp_organized_df['Away Team Players'] = 5

    #Clock formatting & sorting
    pbp_organized_df.loc[pbp_organized_df['Clock'] == '','Clock'] = "00:00:00"
    pbp_organized_df['Clock'] = pd.to_datetime(pbp_organized_df['Clock'], format="%M:%S:%f",errors="coerce")
    pbp_organized_df = pbp_organized_df.sort_values(['Period','Clock'], ascending=(True, False))
    #some games do not have time stamps for all events. In this case, the empty clock times are set to 00:00

    #parsing events, each code chunk is a type of event
    #shots, shot type, shooting player, blocking player if blocked, saving goalie if missed
    shot_phrases = ['Shot']
    shot_types = ['Missed', 'Wide', 'Blocked']
    pbp_organized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(shot_phrases), case=False), 'Event'] = 'Shot'
    for type in shot_types:
        pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Shot') & (pbp_unorganized_df['Event'].str.contains(type, case=False)), 'Detail 1'] = type
    #format 1
    if ((pbp_organized_df['Event'] == 'Shot') & pbp_unorganized_df['Event'].str.contains('\(')).any(axis=0) == True:
        pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Shot'), 'Player'] = pbp_unorganized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(shot_phrases), case=False), 'Event'].str.extract(r"Shot by (.*)\(.+\)", flags=re.IGNORECASE)[0]
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
        pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Faceoff Won'), 'Player'] = pbp_unorganized_df.loc[pbp_organized_df['Event']=='Faceoff Won', 'Event'].str.extract(r"Faceoff (.*) vs (.*), won by (.*)\s?\(.+\)", flags=re.IGNORECASE)[2]
        #setting the losers as Player 2
        away_faceoff_players = pbp_unorganized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(faceoff_phrases), case=False),'Event'].str.extract(r"Faceoff (.*) vs (.*), won by (.*)\s?\(.+\)", flags=re.IGNORECASE)[0]
        home_faceoff_players = pbp_unorganized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(faceoff_phrases), case=False),'Event'].str.extract(r"Faceoff (.*) vs (.*), won by (.*)\s?\(.+\)", flags=re.IGNORECASE)[1]
        faceoff_home_loser = ((pbp_organized_df['Team'] == pbp_organized_df['Away Team']) & (pbp_organized_df['Event'] == 'Faceoff Won'))
        faceoff_away_loser = ((pbp_organized_df['Team'] == pbp_organized_df['Home Team']) & (pbp_organized_df['Event'] == 'Faceoff Won'))
        pbp_organized_df.loc[faceoff_home_loser, 'Player 2'] = home_faceoff_players
        pbp_organized_df.loc[faceoff_away_loser, 'Player 2'] = away_faceoff_players

    #goal parsing
    goal_phrases = ['Goal ']
    pbp_organized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(goal_phrases), case=False), 'Event'] = 'Goal'
    #format 1
    if ((pbp_organized_df['Event'] == 'Goal') & pbp_unorganized_df['Event'].str.contains('\(')).any(axis=0) == True:
        pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Goal'), 'Player'] = pbp_unorganized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(goal_phrases), case=False), 'Event'].str.extract(r"GOAL by (.*) \s?\(.+\)", flags=re.IGNORECASE)[0]
        #1st assist
        assists = pbp_unorganized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(goal_phrases), case=False), 'Event'].str.extract(r"GOAL by (.*) \s?\(.+\),\s?Assist by (.*) On ice for \.+: On ice for \.+:", flags=re.IGNORECASE)[1]
        assists = assists[assists.notna()]
        #1st assist if it exists
        pbp_organized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(goal_phrases), case=False) & pbp_unorganized_df['Event'].str.contains('and'), 'Detail 1'] = assists.str.extract(r"(.*) and (.*),", flags=re.IGNORECASE)[0]
        if pbp_organized_df.loc[(pbp_unorganized_df['Event'].str.contains('|'.join(goal_phrases), case=False)) & (~pbp_unorganized_df['Event'].str.contains('and')) & (assists.notna())].empty == False:
            pbp_organized_df.loc[(pbp_unorganized_df['Event'].str.contains('|'.join(goal_phrases), case=False)) & (~pbp_unorganized_df['Event'].str.contains('and')) & (assists.notna()), 'Detail 1'] = assists.str.extract(r"(.*)", flags=re.IGNORECASE)[0]
        #2nd assist if it exists
        pbp_organized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(goal_phrases), case=False) & pbp_unorganized_df['Event'].str.contains('and'), 'Detail 2'] = assists.str.extract(r"(.*) and (.*),", flags=re.IGNORECASE)[1]

    if not (pbp_organized_df['Home Team Goals'].dtype == 'object'):
        if not (pbp_organized_df['Away Team Goals'].dtype == 'object'):
            pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Goal') &(pbp_organized_df['Team'] ==  pbp_organized_df['Home Team']), 'Home Team Goals'] -= 1
            pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Goal') &(pbp_organized_df['Team'] ==  pbp_organized_df['Away Team']), 'Away Team Goals'] -= 1

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
        pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Goalie in net'), 'Player'] = pbp_unorganized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(goalie_in_phrases), case=False), 'Event'].str.extract(r"Goalie sub \w+ (.*)\s?\(.+\)", flags=re.IGNORECASE)[0]
    if ((pbp_organized_df['Event'] == 'Goalie sub out') & pbp_unorganized_df['Event'].str.contains('\(')).any(axis=0) == True:
        pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Goalie sub out'), 'Player'] = pbp_unorganized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(goalie_pull_phrases), case=False), 'Event'].str.extract(r"Goalie sub \w+ (.*)\s?\(.+\)", flags=re.IGNORECASE)[0]

    #Penalties + empty net + strength calculations
    player_penalty_phrases = ['Minor penalty', 'Major penalty','Minor Penalty', 'Major Penalty']
    game_misconduct_phrases = ['Gamemisconduct']
    team_penalty_phrases = ['Benchminor']
    #player penalties
    pbp_organized_df.loc[(pbp_unorganized_df['Event'].str.contains('|'.join(player_penalty_phrases))), 'Event'] = 'Player Penalty'
    if ((pbp_organized_df['Event'] == 'Player Penalty') & pbp_unorganized_df['Event'].str.contains('\(')).any(axis=0) == True:
        #first format is if penalized player is serving penalty, second format is if another player is serving the penalty
        pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Player Penalty')& (~pbp_unorganized_df['Event'].str.contains('serving penalty')), 'Player'] = pbp_unorganized_df.loc[(pbp_unorganized_df['Event'].str.contains('|'.join(player_penalty_phrases)))& (~pbp_unorganized_df['Event'].str.contains('serving penalty')), 'Event'].str.extract(r"Penalty on (.*)\s?\(.+\) for (.*);duration:(.*)", flags=re.IGNORECASE)[0].str.title()
        pbp_organized_df.loc[(pbp_unorganized_df['Event'].str.contains('|'.join(player_penalty_phrases)))& (pbp_unorganized_df['Event'].str.contains('serving penalty')), 'Player'] = pbp_unorganized_df.loc[(pbp_unorganized_df['Event'].str.contains('|'.join(player_penalty_phrases)))& (pbp_unorganized_df['Event'].str.contains('serving penalty')), 'Event'].str.extract(r"Penalty on (.*)\s?\(.+\) for (.*);duration:(.*), (.*),(.*) serving penalty", flags=re.IGNORECASE)[0].str.title()
        pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Player Penalty'), 'Detail 1'] = pbp_unorganized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(player_penalty_phrases)), 'Event'].str.extract(r"Penalty on (.*)\s?\(.+\) for (.*);duration:(.*)", flags=re.IGNORECASE)[1].str.title()
        pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Player Penalty')& (~pbp_unorganized_df['Event'].str.contains('serving penalty')), 'Detail 2'] = pbp_unorganized_df.loc[(pbp_unorganized_df['Event'].str.contains('|'.join(player_penalty_phrases)))& (~pbp_unorganized_df['Event'].str.contains('serving penalty')), 'Event'].str.extract(r"Penalty on (.*)\s?\(.+\) for (.*);duration:(.*)", flags=re.IGNORECASE)[2]
        pbp_organized_df.loc[(pbp_unorganized_df['Event'].str.contains('|'.join(player_penalty_phrases)))& (pbp_unorganized_df['Event'].str.contains('serving penalty')), 'Detail 2'] = pbp_unorganized_df.loc[(pbp_unorganized_df['Event'].str.contains('|'.join(player_penalty_phrases)))& (pbp_unorganized_df['Event'].str.contains('serving penalty')), 'Event'].str.extract(r"Penalty on (.*)\s?\(.+\) for (.*);duration:(.*), (.*),(.*) serving penalty", flags=re.IGNORECASE)[2]
        #iterating through each team's penalties by period and calculating strength
        for team in ['Home Team', 'Away Team']:
            for period in [1,2,3,4]:
                penalty_min = list(pbp_organized_df[(pbp_organized_df['Event'] == 'Player Penalty') & (pbp_organized_df['Period'] == period)&(pbp_organized_df['Team'] == pbp_organized_df[team])]['Clock'])
                pp_end = list(pbp_organized_df[(pbp_organized_df['Event'] == 'Player Penalty') & (pbp_organized_df['Period'] == period)&(pbp_organized_df['Team'] == pbp_organized_df[team])]['Clock']-pd.to_timedelta(pd.to_numeric(pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Player Penalty') & (pbp_organized_df['Period'] == period)&(pbp_organized_df['Team'] == pbp_organized_df[team]), 'Detail 2']), unit='m'))
                for i in range(len(pp_end)):
                    coincidental_majors = ((pbp_organized_df['Clock'] == pbp_organized_df['Clock'].shift(-1)) & (pbp_organized_df['Clock'].shift(-1) == penalty_min[i])& (pbp_organized_df['Clock'] == penalty_min[i])) & ((pbp_unorganized_df['Event'].shift(-1).str.contains('Major Penalty')) & (pbp_unorganized_df['Event'].str.contains('Major Penalty'))& (pbp_organized_df['Team'] !=  pbp_organized_df['Team'].shift(-1)))
                    coincidental_minors_w_existing_penalties = ((pbp_organized_df['Clock'] == pbp_organized_df['Clock'].shift(-1)) & (pbp_organized_df['Clock'].shift(-1) == penalty_min[i]) & (pbp_organized_df['Clock'] == penalty_min[i])) & ((pbp_organized_df['Event'].shift(-1) == 'Player Penalty') & (pbp_organized_df['Event'] == 'Player Penalty')) & ((pbp_organized_df['Home Team Players'] < 5 ) | (pbp_organized_df['Away Team Players'] < 5 )) & (pbp_organized_df['Team'] !=  pbp_organized_df['Team'].shift(-1))
                    if ~(coincidental_majors.any(axis=0) == True)& ~(coincidental_minors_w_existing_penalties.any(axis=0) == True):
                        pre_penalty_event_exclusion = ~(((pbp_organized_df['Clock'] == pbp_organized_df['Clock'].shift(-1)) & (pbp_organized_df['Clock'].shift(-1) == penalty_min[i]) & (pbp_organized_df['Event'].shift(-1) == 'Player Penalty')) |((pbp_organized_df['Clock'] == pbp_organized_df['Clock'].shift(-2)) & (pbp_organized_df['Clock'].shift(-2) == penalty_min[i])& (pbp_organized_df['Event'].shift(-2) == 'Player Penalty'))|((pbp_organized_df['Clock'] == pbp_organized_df['Clock'].shift(-3)) & (pbp_organized_df['Clock'].shift(-3) == penalty_min[i])& (pbp_organized_df['Event'].shift(-3) == 'Player Penalty'))|((pbp_organized_df['Clock'] == pbp_organized_df['Clock'].shift(-4)) & (pbp_organized_df['Clock'].shift(-4) == penalty_min[i])& (pbp_organized_df['Event'].shift(-4) == 'Player Penalty')))
                        pbp_organized_df.loc[(pbp_organized_df['Period'] == period) & (pbp_organized_df['Clock'] > pp_end[i]) & (penalty_min[i] >= pbp_organized_df['Clock']) & (pbp_organized_df['Event'] != 'Player Penalty') & pre_penalty_event_exclusion, team+' Players'] -= 1
                        pbp_organized_df.loc[(pbp_organized_df['Period'] == period) & (pbp_organized_df['Clock'] > pp_end[i]) & (penalty_min[i] > pbp_organized_df['Clock']) & (pbp_organized_df['Event'] == 'Player Penalty') & (pbp_organized_df['Clock'] != penalty_min[i]) & pre_penalty_event_exclusion, team+' Players'] -= 1

                        coincidental = ((pbp_organized_df['Clock'] == pbp_organized_df['Clock'].shift(-1)) & (pbp_organized_df['Clock'].shift(-1) == penalty_min[i])& (pbp_organized_df['Clock'] == penalty_min[i]) & (pbp_organized_df['Event'].shift(-1) == 'Player Penalty') & (pbp_organized_df['Event'] == 'Player Penalty'))
                        #if there is a goal during the penalty time, the scoring team is not the penalized team, and the strength is not even when the goal is scored, add a player back onto penalized team after goal is scored
                        if (((pbp_organized_df['Event'] == 'Goal') & (pbp_organized_df['Period'] == period) & (pbp_organized_df['Team'] !=  pbp_organized_df[team])& (pbp_organized_df['Clock'] > pp_end[i]) & (penalty_min[i] >= pbp_organized_df['Clock'])).any(axis=0) == True) & ~(coincidental.any(axis=0) == True):
                            goal_time = list(pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Goal') & (pbp_organized_df['Team'] != pbp_organized_df[team])& (pbp_organized_df['Clock'] > pp_end[i]) & (penalty_min[i] >= pbp_organized_df['Clock']),'Clock'])
                            pre_goal_event_exclusion = ~(((pbp_organized_df['Clock'] == pbp_organized_df['Clock'].shift(-1)) & (pbp_organized_df['Clock'].shift(-1) == goal_time[0]) & (pbp_organized_df['Event'].shift(-1) == 'Goal')))
                            pbp_organized_df.loc[(pbp_organized_df['Period'] == period) & (pbp_organized_df['Clock'] >= pp_end[i]) & (goal_time[0] >= pbp_organized_df['Clock'])& (pbp_organized_df['Event'] != 'Goal') & (pbp_organized_df['Clock'] != penalty_min[i]) & pre_goal_event_exclusion, team+' Players'] += 1
                            pbp_organized_df.loc[(pbp_organized_df['Period'] == period) & (pbp_organized_df['Clock'] >= pp_end[i]) & (goal_time[0] > pbp_organized_df['Clock']) & (pbp_organized_df['Event'] == 'Goal') & pre_goal_event_exclusion, team+' Players'] += 1
                pbp_organized_df.loc[(pbp_organized_df[team+' Players'] < 3),team+' Players'] = 3

    #team penalties
    pbp_organized_df.loc[(pbp_unorganized_df['Event'].str.contains('|'.join(team_penalty_phrases))), 'Event'] = 'Team Penalty'
    if ((pbp_organized_df['Event'] == 'Team Penalty') & pbp_unorganized_df['Event'].str.contains('\(')).any(axis=0) == True:
        #setting player who served penalty + penalty + duration
        first = pbp_unorganized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(team_penalty_phrases)), 'Event'].str.extract(r"Penalty on Team\(.+\) for (.*);duration:(.*), (.*),(.*) serving penalty", flags=re.IGNORECASE)[3].str.title()
        last = pbp_unorganized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(team_penalty_phrases)), 'Event'].str.extract(r"Penalty on Team\(.+\) for (.*);duration:(.*), (.*),(.*) serving penalty", flags=re.IGNORECASE)[2].str.title()
        pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Team Penalty'), 'Player'] = first+" "+last
        pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Team Penalty'), 'Detail 1'] = pbp_unorganized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(team_penalty_phrases), case=False), 'Event'].str.extract(r"Penalty on Team\(.+\) for (.*);duration:(.*), (.*),(.*) serving penalty", flags=re.IGNORECASE)[0].str.title()
        pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Team Penalty'), 'Detail 2'] = pbp_unorganized_df.loc[pbp_unorganized_df['Event'].str.contains('|'.join(team_penalty_phrases), case=False), 'Event'].str.extract(r"Penalty on Team\(.+\) for (.*);duration:(.*), (.*),(.*) serving penalty", flags=re.IGNORECASE)[1].str.title()

        #iterating through each team's penalties by period and calculating strength
        for team in ['Home Team', 'Away Team']:
            for period in [1,2,3,4]:
                penalty_min = list(pbp_organized_df[(pbp_organized_df['Event'] == 'Team Penalty') & (pbp_organized_df['Period'] == period)&(pbp_organized_df['Team'] == pbp_organized_df[team])]['Clock'])
                pp_end = list(pbp_organized_df[(pbp_organized_df['Event'] == 'Team Penalty') & (pbp_organized_df['Period'] == period)&(pbp_organized_df['Team'] == pbp_organized_df[team])]['Clock']-pd.to_timedelta(pd.to_numeric(pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Team Penalty') & (pbp_organized_df['Period'] == period)&(pbp_organized_df['Team'] == pbp_organized_df[team]), 'Detail 2']), unit='m'))
                for i in range(len(pp_end)):
                    coincidental_majors = ((pbp_organized_df['Clock'] == pbp_organized_df['Clock'].shift(-1)) & (pbp_organized_df['Clock'].shift(-1) == penalty_min[i])& (pbp_organized_df['Clock'] == penalty_min[i])) & ((pbp_unorganized_df['Event'].shift(-1).str.contains('Major Penalty')) & (pbp_unorganized_df['Event'].str.contains('Major Penalty')))
                    coincidental_minors_w_existing_penalties = ((pbp_organized_df['Clock'] == pbp_organized_df['Clock'].shift(-1)) & (pbp_organized_df['Clock'].shift(-1) == penalty_min[i]) & (pbp_organized_df['Clock'] == penalty_min[i])) & ((pbp_organized_df['Event'].shift(-1) == 'Team Penalty') & (pbp_organized_df['Event'] == 'Team Penalty')) & ((pbp_organized_df['Home Team Players'] < 5 ) | (pbp_organized_df['Away Team Players'] < 5 ))
                    if ~(coincidental_majors.any(axis=0) == True)& ~(coincidental_minors_w_existing_penalties.any(axis=0) == True):
                        pre_penalty_event_exclusion = ~(((pbp_organized_df['Clock'] == pbp_organized_df['Clock'].shift(-1)) & (pbp_organized_df['Clock'].shift(-1) == penalty_min[i]) & (pbp_organized_df['Event'].shift(-1) == 'Team Penalty')) |((pbp_organized_df['Clock'] == pbp_organized_df['Clock'].shift(-2)) & (pbp_organized_df['Clock'].shift(-2) == penalty_min[i])& (pbp_organized_df['Event'].shift(-2) == 'Team Penalty'))|((pbp_organized_df['Clock'] == pbp_organized_df['Clock'].shift(-3)) & (pbp_organized_df['Clock'].shift(-3) == penalty_min[i])& (pbp_organized_df['Event'].shift(-3) == 'Team Penalty'))|((pbp_organized_df['Clock'] == pbp_organized_df['Clock'].shift(-4)) & (pbp_organized_df['Clock'].shift(-4) == penalty_min[i])& (pbp_organized_df['Event'].shift(-4) == 'Team Penalty')))
                        pbp_organized_df.loc[(pbp_organized_df['Period'] == period) & (pbp_organized_df['Clock'] > pp_end[i]) & (penalty_min[i] >= pbp_organized_df['Clock']) & (pbp_organized_df['Event'] != 'Team Penalty') & pre_penalty_event_exclusion, team+' Players'] -= 1
                        pbp_organized_df.loc[(pbp_organized_df['Period'] == period) & (pbp_organized_df['Clock'] > pp_end[i]) & (penalty_min[i] > pbp_organized_df['Clock']) & (pbp_organized_df['Event'] == 'Team Penalty') & (pbp_organized_df['Clock'] != penalty_min[i]) & pre_penalty_event_exclusion, team+' Players'] -= 1

                        coincidental = ((pbp_organized_df['Clock'] == pbp_organized_df['Clock'].shift(-1)) & (pbp_organized_df['Clock'].shift(-1) == penalty_min[i])& (pbp_organized_df['Clock'] == penalty_min[i]) & (pbp_organized_df['Event'].shift(-1) == 'Team Penalty') & (pbp_organized_df['Event'] == 'Team Penalty'))
                        #if there is a goal during the penalty time, the scoring team is not the penalized team, and the strength is not even when the goal is scored, add a player back onto penalized team after goal is scored
                        if (((pbp_organized_df['Event'] == 'Goal') & (pbp_organized_df['Period'] == period) & (pbp_organized_df['Team'] !=  pbp_organized_df[team])& (pbp_organized_df['Clock'] > pp_end[i]) & (penalty_min[i] >= pbp_organized_df['Clock'])).any(axis=0) == True) & ~(coincidental.any(axis=0) == True):
                            goal_time = list(pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Goal') & (pbp_organized_df['Team'] != pbp_organized_df[team])& (pbp_organized_df['Clock'] > pp_end[i]) & (penalty_min[i] >= pbp_organized_df['Clock']),'Clock'])
                            pre_goal_event_exclusion = ~(((pbp_organized_df['Clock'] == pbp_organized_df['Clock'].shift(-1)) & (pbp_organized_df['Clock'].shift(-1) == goal_time[0]) & (pbp_organized_df['Event'].shift(-1) == 'Goal')))
                            pbp_organized_df.loc[(pbp_organized_df['Period'] == period) & (pbp_organized_df['Clock'] >= pp_end[i]) & (goal_time[0] >= pbp_organized_df['Clock'])& (pbp_organized_df['Event'] != 'Goal') & (pbp_organized_df['Clock'] != penalty_min[i]) & pre_goal_event_exclusion, team+' Players'] += 1
                            pbp_organized_df.loc[(pbp_organized_df['Period'] == period) & (pbp_organized_df['Clock'] >= pp_end[i]) & (goal_time[0] > pbp_organized_df['Clock']) & (pbp_organized_df['Event'] == 'Goal') & pre_goal_event_exclusion, team+' Players'] += 1
                pbp_organized_df.loc[(pbp_organized_df[team+' Players'] < 3),team+' Players'] = 3

    #print(pbp_organized_df.iloc[60:70])

    #if clock is equal to goal time and index is not less than goal index, do n
    # & (pbp_organized_df['Event'] != 'Team Penalty')
    pre_penalty_event_exclusion = ((pbp_organized_df['Clock'] == pbp_organized_df['Clock'].shift(-1)) & ((pbp_organized_df['Event'].shift(-1) == 'Team Penalty') | (pbp_organized_df['Event'].shift(-2) == 'Team Penalty')| (pbp_organized_df['Event'].shift(-3) == 'Team Penalty')| (pbp_organized_df['Event'].shift(-4) == 'Team Penalty')| (pbp_organized_df['Event'].shift(-5) == 'Team Penalty')))
    #print(pbp_organized_df['Event'].shift(-1)[63:74])
    #print(pbp_organized_df.iloc[80:86])
    #print(coincidental.iloc[80:86])

    #print(pbp_organized_df.loc[(pbp_organized_df['Event'] == 'Team Penalty')])

    #empty_net_phrases = ['Empty Net']
    #pbp_organized_df.loc[(pbp_unorganized_df['Event'].str.contains('|'.join(empty_net_phrases), case=False), 'Event'] = 'Empty Net'
    #if ((pbp_organized_df['Event'] == 'Empty Net') & pbp_unorganized_df['Event'].str.contains('\(')).any(axis=0) == True:
    #    print('z')

    #clock formatting
    pbp_organized_df['Clock'] = pbp_organized_df['Clock'].dt.time

    #filtering out repeated shots after goals
    double_count_shots = (pbp_organized_df['Player'] == pbp_organized_df['Player'].shift(1)) & (pbp_organized_df['Event'] == 'Shot')
    pbp_organized_df = pbp_organized_df[~double_count_shots]

    return pbp_organized_df

def run_full_scrape(games, pbp_dir):
    """
    :param List[date, int] games: a list of games, with each game formatted as [date, event_id]
    :param str pbp_dir: the filepath of the directory that pbp's should be saved to
    """

    # Run the code for each game in the event_list
    print("Scrape PBP Data per Event")
    with tqdm(games) as t:
        for date, event_id in t:
            t.set_description(f"Date: {date}, Event ID: {event_id}")

            pbp_scrape(date, event_id, pbp_dir)

            # Sleep for a few seconds to avoid overloading the server:
            # time.sleep(randint(2,3))
