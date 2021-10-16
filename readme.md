## About:
This code is designed to pull WOMEN'S hockey pbp data from stats.ncaa.org, put it
in a format as close to Stathlete's Big Data Cup format as possible, and save it as a csv in the format
"GameYear-GameMonth-GameDay_eventid.csv". See the end of this doc for the full data format.

## To use:
- Run "full_scrape.py" with the start (start_date) and end dates (end_date) line you wish to scrape.
- Use ncaa-schedule-finder.py to pull all the event IDs (unique schedule ID that appears in the middle
of https://stats.ncaa.org/contests/2120211/box_score) for games played between specified dates

## Cases currently unaccounted for
- games in which a game id has been generated but no data has been entered yet (usually occurs when trying to
scrape a game that occurred on the same day of scraping)
- occasional pbp data that is a different format than the main format (ie https://stats.ncaa.org/game/play_by_play/5128689)
- games before the 2021 season
- Shootout and 2nd/3rd/etc OT formats, which vary by conference and are not currently recorded in stats.ncaa.org
- Empty net strength
- Powerplays spanning periods

## To Do, in order of priority
- alternative pbp formats
- Empty net strength
- Powerplays spanning periods

If you find an issue, please open an issue in the "Issues" tab. For any other questions or comments,
please contact carleenmarkey@gmail.com

## Data format
The following documentation was modified from https://github.com/bigdatacup/Big-Data-Cup-2021/

- Date (e.g. ‘2020-12-23’. Format = ‘yyyy-mm-dd’)
- Game ID (unique game ID that appears at the end of https://stats.ncaa.org/game/play_by_play/)
- Home Team (e.g. ‘Maine’)
- Away Team (e.g. ‘Long Island University’)
- Period (range from 1-3 for regulation, 4+ for overtime)
- Clock (e.g. ‘00:19:34.0’. Format = ‘hh:mm:ss.ff’)
- Home Team Skaters (range from 3-5 for home skaters currently on the ice)
- Away Team Skaters (range from 3-6 for away skaters currently on the ice)
- Home Team Goals (current goals scored by the home team at the time of the event)
- Away Team Goals (current goals scored by the away team at the time of the event)
- Team (name of the team responsible for the event)
- Player (name of the player responsible for the event)
- Event (type of event, e.g. ‘Play’, ‘Shot’, …)
- Detail 1-2 (up to 2 supplementary details for each event, varies by event type)
- Player 2 (name of a secondary player involved in an event, varies by event type)
- Goalie (only shows up in the "Goalie" column if they have explicitly been named in the pbp. I assume this means they actually came in contact with the puck when making a save. Traditional SV% is not calculated this way, but the NCAA does this for whatever reason)

### Event Types
Shot
- Player: Shooter
- Player 2: if shot blocked, Blocker
- Detail 1: Shot Type (Wide, Missed, Blocked)
- Detail 2: One timer (true or false)

Goal
- Player: Shooter
- Detail 1: first assist, if it exists
- Detail 2: Second assist, if it exists

Faceoff Won
- Player: Skater who won the draw
- Player 2: Skater who lost the draw

Player Penalty
- Player: Player who committed the infraction
- Detail 1: Infraction Type (e.g. Slashing, Tripping, Roughing, Hooking, ...)
- Detail 2: length of penalty
