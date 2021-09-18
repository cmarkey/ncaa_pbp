import regex
from ncaa_pbp import ncaa_pbp_scrape_tester as pbp_scraper
import pandas as pd

test_pbp = pbp_scraper.pbp_scrape(game_id=4984716)
print(test_pbp[1])
pbp_unorganized_df = pd.DataFrame(test_pbp, columns=['Schedule ID','Game ID', 'Home Team','Away Team','Period', 'Home Team Goals', 'Away Team Goals', 'Clock', 'Home Team Event', 'Away Team Event'])
print(pbp_unorganized_df)
pbp_organized_df = pd.DataFrame(columns = ['Schedule ID','Game ID', 'Home Team','Away Team','Period', 'Home Team Goals', 'Away Team Goals', 'Clock', 'Team', 'Event','Player','Detail 1','Detail 2','Player 2', 'Goalie'])
pbp_organized_df[['Schedule ID','Game ID', 'Home Team','Away Team','Period', 'Home Team Goals', 'Away Team Goals', 'Clock']] = pbp_unorganized_df[['Schedule ID','Game ID', 'Home Team','Away Team','Period', 'Home Team Goals', 'Away Team Goals', 'Clock']]
#Set team who created event
pbp_organized_df.loc[pbp_unorganized_df['Home Team Event'] == '', 'Team'] = pbp_organized_df['Away Team']
pbp_organized_df.loc[pbp_unorganized_df['Away Team Event'] == '', 'Team'] = pbp_organized_df['Home Team']
#Set Event Type. If need to add new phrase for an event, add to the phrases list
shot_phrases = ['Shot']
faceoff_phrases = ['Faceoff', 'Face off']
goal_phrases = ['Goal']
goalie_in_phrases = ['at net', 'Goalie sub in']
goalie_pull_phrases = ['Empty Net', 'Goalie sub out']

pbp_organized_df.loc[(pbp_unorganized_df['Away Team Event'].str.contains('|'.join(shot_phrases), case=False) | pbp_unorganized_df['Home Team Event'].str.contains('|'.join(shot_phrases), case=False)), 'Event'] = 'Shot'
pbp_organized_df.loc[(pbp_unorganized_df['Away Team Event'].str.contains('|'.join(faceoff_phrases), case=False) | pbp_unorganized_df['Home Team Event'].str.contains('|'.join(faceoff_phrases), case=False)), 'Event'] = 'Faceoff'
pbp_organized_df.loc[(pbp_unorganized_df['Away Team Event'].str.contains('|'.join(goal_phrases), case=False) | pbp_unorganized_df['Home Team Event'].str.contains('|'.join(goal_phrases), case=False)), 'Event'] = 'Goal'
pbp_organized_df.loc[(pbp_unorganized_df['Away Team Event'].str.contains('|'.join(goalie_in_phrases), case=False) | pbp_unorganized_df['Home Team Event'].str.contains('|'.join(goalie_in_phrases), case=False)), 'Event'] = 'Goalie in net'
pbp_organized_df.loc[(pbp_unorganized_df['Away Team Event'].str.contains('|'.join(goalie_pull_phrases), case=False) | pbp_unorganized_df['Home Team Event'].str.contains('|'.join(goalie_pull_phrases), case=False)), 'Event'] = 'Goalie Pulled'

print(pbp_organized_df)
