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

debug = False

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

    p = re.compile(r'([0-9]+).*([0-9]+)')

    def processRow(row, period_no):
        [clock_time, away_team_event, score, home_team_event] = [element.get_text(strip=True) for element in row.select('tr>td')]
        # extract scores
        m = p.match(score)
        home_score = m.group(1)
        away_score = m.group(2)
        return [date, pbp_game_id, home_team, away_team, period_no, home_score, away_score, clock_time, away_team_event, home_team_event]

    # ignore first row (the one with the teams, time, etc and last row (period end)
    for i, period in enumerate(nested_periods):
        all_plays += [processRow(row, i+1) for row in period[1:-1]]

    if debug:
        return parse_pbp(all_plays)

    clean_pbp = parse_pbp(all_plays)
    clean_pbp.to_csv(filename,index=False)

def parse_pbp(raw_pbp):
    # columns that really just get carried over verbatim from the original dataset
    carry_columns = ['Date','Game ID', 'Home Team','Away Team','Period', 'Home Team Goals', 'Away Team Goals', 'Clock']

    #setting the list pbp as a dataframe
    pbp_unorganized_df = pd.DataFrame(raw_pbp, columns=(carry_columns+['Away Team Event', 'Home Team Event']))

    #filtering out pbp lines that have no impact on play, and no impact the interpretation of other events
    #this code chunk has to be here otherwise the rest of the code breaks
    unwanted_pbp = ['Timeout', 'Shootout', 'Start power play for']
    pbp_unorganized_df['Event'] = pbp_unorganized_df['Home Team Event']+pbp_unorganized_df['Away Team Event']
    pbp_filter = pbp_unorganized_df['Event'].str.contains('|'.join(unwanted_pbp), case=False)
    pbp_unorganized_df = pbp_unorganized_df[~pbp_filter]
    pbp_organized_df = pd.DataFrame(columns = carry_columns + ['Home Team Players','Away Team Players', 'Team', 'Event', 'Player','Detail 1','Detail 2','Player 2', 'Goalie'])
    pbp_organized_df[carry_columns] = pbp_unorganized_df[carry_columns]

    #Set team who created event
    pbp_organized_df.loc[pbp_unorganized_df['Away Team Event'] == '', 'Team'] = pbp_organized_df['Home Team']
    pbp_organized_df.loc[pbp_unorganized_df['Home Team Event'] == '', 'Team'] = pbp_organized_df['Away Team']

    # typecast goals to be numeric
    pbp_organized_df[['Home Team Goals', 'Away Team Goals']] = pbp_organized_df[['Home Team Goals', 'Away Team Goals']].apply(pd.to_numeric, errors='ignore')

    #set even strength as default
    pbp_organized_df['Home Team Players'] = 5
    pbp_organized_df['Away Team Players'] = 5

    #Clock formatting & sorting
    pbp_organized_df['Clock'] = pd.to_datetime(pbp_organized_df['Clock'], format="%M:%S:%f",errors="coerce")
    pbp_organized_df = pbp_organized_df.sort_values(['Period','Clock'], ascending=(True, False))

    ######################################################
    # parsing events, each code chunk is a type of event #
    ######################################################


    #
    # shots, shot type, shooting player, blocking player if blocked, saving goalie if missed
    #
    shot_phrases = ['Shot']
    shot_types = ['Missed', 'Wide', 'Blocked', 'Pipe']

    shot_mask = pbp_unorganized_df['Event'].str.contains('|'.join(shot_phrases), case=False).fillna(False)

    pbp_organized_df.loc[shot_mask, 'Event'] = 'Shot'
    for type in shot_types:
        pbp_organized_df.loc[shot_mask & (pbp_unorganized_df['Event'].str.contains(type, case=False)), 'Detail 1'] = type
    #format 1
    if (
        (pbp_organized_df["Event"] == "Shot")
        & pbp_unorganized_df["Event"].str.contains("\(")
    ).any(axis=0) == True:
        pbp_organized_df.loc[shot_mask, ["Player", "Player 2", "Goalie"]] = (
            pbp_unorganized_df.loc[shot_mask, "Event"]
            .str.extract(
                r"Shot by (.*)\(.+\) *(BLOCKED by (.*)|MISSED, save (.*)|WIDE|MISSED|PIPE)",
                flags=re.IGNORECASE,
            )
            .rename(columns={0: "Player", 2: "Player 2", 3: "Goalie"})
            .drop(columns=[1])
        )

    #
    # faceoff parsing
    #
    faceoff_phrases = ['Faceoff', 'Face off']
    faceoff_mask = pbp_unorganized_df['Event'].str.contains('|'.join(faceoff_phrases), case=False).fillna(False)
    pbp_organized_df.loc[faceoff_mask, 'Event'] = 'Faceoff Won'

    # format 1
    if (faceoff_mask & pbp_unorganized_df["Event"].str.contains("\(")).any(axis=0) == True:
        faceoff_info = pbp_unorganized_df.loc[faceoff_mask, "Event"].str.extract(
            r"Faceoff (.*) vs (.*), won by (.*)\s?\(.+\)", flags=re.IGNORECASE
        )
        # setting Player as winner of faceoff
        pbp_organized_df.loc[faceoff_mask, "Player"] = faceoff_info[2]
        # setting the losers as Player 2
        pbp_organized_df.loc[faceoff_mask, "Player 2"] = faceoff_info.apply(
            lambda x: x[0] if x[0] != x[2] else x[1], axis="columns"
        )


    #
    # goal parsing
    #
    goal_phrases = ['Goal ']
    goal_mask = pbp_unorganized_df['Event'].str.contains('|'.join(goal_phrases), case=False).fillna(False)
    pbp_organized_df.loc[goal_mask, 'Event'] = 'Goal'

    # format 1
    if (goal_mask & pbp_unorganized_df['Event'].str.contains('\(')).any(axis=0) == True:
        goal_info = pbp_unorganized_df.loc[goal_mask, "Event"].str.extract(
            r"GOAL by (.*) \s?\(.+\),\s?Assist by ((.*) and (.*),|(.*)) On ice for .+: On ice for .+:",
            flags=re.IGNORECASE,
        )

        # goalscorer goes in Player, primary assist player goes in Detail 1, secondary assist player goes in Detail 2
        pbp_organized_df.loc[goal_mask, ["Player", "Detail 1", "Detail 2"]] = (
            goal_info.assign(temp=lambda x: x[2].fillna("") + x[4].fillna(""))
            .drop(columns=[1, 2, 4])
            .rename(columns={0: "Player", "temp": "Detail 1", 3: "Detail 2"})
        )

    if not (pbp_organized_df['Home Team Goals'].dtype == 'object' or pbp_organized_df['Away Team Goals'].dtype == 'object'):
        # modify goals so the score change doesn't start until after the goal event
        pbp_organized_df.loc[goal_mask & (pbp_organized_df['Team'] ==  pbp_organized_df['Home Team']), 'Home Team Goals'] -= 1
        pbp_organized_df.loc[goal_mask & (pbp_organized_df['Team'] ==  pbp_organized_df['Away Team']), 'Away Team Goals'] -= 1

    #
    # goalie shenanigans
    #
    goalie_in_phrases = ['at net', 'Goalie sub in']
    goalie_pull_phrases = ['Goalie sub out']

    goalie_in_mask = pbp_unorganized_df['Event'].str.contains('|'.join(goalie_in_phrases), case=False)
    goalie_pull_mask = pbp_unorganized_df['Event'].str.contains('|'.join(goalie_pull_phrases), case=False)

    pbp_organized_df.loc[goalie_in_mask, 'Event'] = 'Goalie in net'
    pbp_organized_df.loc[goalie_pull_mask, 'Event'] = 'Goalie sub out'

    # format 1
    if (
        (pbp_organized_df["Event"] == "Goalie in net")
        & pbp_unorganized_df["Event"].str.contains("\(")
    ).any(axis=0) == True:
        pbp_organized_df.loc[
            goalie_in_mask | goalie_pull_mask, "Player"
        ] = pbp_unorganized_df.loc[goalie_in_mask | goalie_pull_mask, "Event"].str.extract(
            r"Goalie sub \w+ (.*)\s?\(.+\)", flags=re.IGNORECASE)[0]



    #
    # Penalties + empty net + strength calculations
    #
    player_penalty_phrases = ['Minor penalty', 'Major penalty']
    player_penalty_mask = pbp_unorganized_df['Event'].str.contains('|'.join(player_penalty_phrases), case=False)
    game_misconduct_phrases = ['Gamemisconduct']
    team_penalty_phrases = ['Benchminor']

    # player penalties
    pbp_organized_df.loc[player_penalty_mask, 'Event'] = 'Player Penalty'
    # format 1
    if (player_penalty_mask & pbp_unorganized_df['Event'].str.contains('\(')).any(axis=0) == True:
        #first format is if penalized player is serving penalty, second format is if another player is serving the penalty
        player_penalty_info = pbp_unorganized_df.loc[player_penalty_mask, "Event"].str.extract(
            r"Penalty on (.*)\s?\(.+\) for (.*);duration:([1-9]*),* *((.*),(.*) serving penalty)*", flags=re.IGNORECASE
        )
        pbp_organized_df.loc[player_penalty_mask, ["Player", "Detail 1", "Detail 2"]] = (
            player_penalty_info.assign(temp=lambda x: x[1].str.title())
            .drop(columns=[1, 3])
            .rename(columns={0: "Player", "temp": "Detail 1", 2: "Detail 2"})
        )

    #team penalties
    team_penalty_mask = pbp_unorganized_df['Event'].str.contains('|'.join(team_penalty_phrases), case=False)
    pbp_organized_df.loc[team_penalty_mask, 'Event'] = 'Team Penalty'

    # format 1
    if (team_penalty_mask & pbp_unorganized_df['Event'].str.contains('\(')).any(axis=0) == True:
        team_penalty_info = pbp_unorganized_df.loc[team_penalty_mask, "Event"].str.extract(
            r"Penalty on Team\(.+\) for (.*);duration:(.*), (.*),(.*) serving penalty",
            flags=re.IGNORECASE,
        )
        # setting player who served penalty + penalty + duration
        pbp_organized_df.loc[team_penalty_mask, ["Player", "Detail 1", "Detail 2"]] = (
            team_penalty_info.assign(
                Player=lambda x: x[3].str.title() + " " + x[2].str.title(),
                temp=lambda x: x[0].str.title(),
            )
            .drop(columns=[0, 2, 3])
            .rename(columns={"temp": "Detail 1", 1: "Detail 2"})
        )

    #
    # calculate strength
    #
    penalties = []
    for i in range(pbp_organized_df.shape[0]):
        current_row = pbp_organized_df.iloc[i]

        # adjust strength based on existing penalties
        def adjust_strength(penalty):
            # ignore coincidental penalties
            # will screw up if penalty -> other event -> penalty all at the same time indicator
            if not (penalty["start_time"] == current_row.Clock and "Penalty" in current_row.Event):
                current_row[f"{penalty['team']} Players"] -= 1
            return penalty


        penalties = [
            adjust_strength(penalty)
            for penalty in penalties
            if (current_row.Period < penalty["end_period"])
            or (
                penalty["end_period"] == current_row.Period
                and penalty["end_time"] < current_row.Clock
            )
        ]

        # add new penalties
        if current_row.Event == "Player Penalty" or current_row.Event == "Team Penalty":
            penalty_time = datetime.timedelta(minutes=int(current_row["Detail 2"]))
            end_time = current_row.Clock - penalty_time
            end_period = current_row.Period

            if end_time.day == 31:
                # go into next period; adjust end time and end_period
                end_time = pd.Timestamp(
                    datetime.datetime(1900, 1, 1, 0, 20)
                    - penalty_time
                    + datetime.timedelta(
                        minutes=current_row.Clock.minute,
                        seconds=current_row.Clock.second,
                        microseconds=current_row.Clock.microsecond,
                    )
                )
                end_period += 1

            penalties.append(
                {
                    "team": "Home Team" if current_row.Team == current_row["Home Team"] else "Away Team",
                    "end_period": end_period,
                    "start_time" : current_row.Clock,
                    "end_time": end_time,
                }
            )

        # if there is a goal during the penalty time,
        # the scoring team is not the penalized team,
        # and the strength is not even when the goal is scored,
        # add a player back onto penalized team after goal is scored
        if current_row.Event == "Goal" and current_row["Home Team Players"] != current_row["Away Team Players"]:
            for penalty in penalties:
                if current_row['Team'] != penalty['team']:
                    penalties.remove(penalty)
                    break

        pbp_organized_df.iloc[i] = current_row

    if debug:
        return((pbp_unorganized_df, pbp_organized_df))

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
