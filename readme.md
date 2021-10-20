## About

This code is designed to pull NCAA women'S hockey pbp data (DI, DII or DIII) from stats.ncaa.org, put it
in a format as close to Stathlete's Big Data Cup format as possible, and save it as a csv in the format
"GameYear-GameMonth-GameDay_eventid.csv". See the end of this doc for the full data format.

Thanks to Dave MacPherson for setting up the scraping portion of this and Gilles Dignard for providing independently scraped pbp which was heavily used as a reference for parsing and testing.

## To use

-   Install all the required packages listed in "requirements.txt" (if you are using pip, you can do this by running `pip install -r requirements.txt`).
-   In "full_scrape.py" specify the start (`start_date`) and end dates (`end_date`) line you wish to scrape.
-   Ensure that `season_id` is correct. This can be checked by going to https://stats.ncaa.org/contests/scoreboards, selecting women's ice hockey & the desired division, and then getting the season_id out of the URL (ie 17800 from https://stats.ncaa.org/contests/scoreboards?utf8=%E2%9C%93&season_division_id=17800&game_date=10%2F21%2F2021&conference_id=0&tournament_id=&commit=Submit)
-   (OPTIONAL) If you want to save the play-by-play data csv's to a particular folder, indicate it as `pbp_dir`. If no directory is indicated, csv's will be saved to the current directory.
-   (OPTIONAL) If you want to save the full list of event IDs for the specified dates, set `schedule_filename` to be equal to the filepath you want the .csv to be saved to.
    -   The event ID is the unique schedule ID that appears in https://stats.ncaa.org/contests/{event_id}/box_score. This event ID is distinct from the game ID used to fetch the play by play for a specific game.
    -   For example, in https://stats.ncaa.org/contests/2120211/box_score, the event ID is 2120211.
-   Run "full_scrape.py".

## Cases currently unaccounted for + to be fixed, in order of priority

-   occasional pbp data that is a different format than the main format (ie https://stats.ncaa.org/game/play_by_play/5128689). PBP will be processed with no players or details for events and incorrect strength + goal timing formatting)
-   double or triple minors to the same player
-   games before the 2021 season
-   Powerplays spanning periods
-   teams containing parentheses
-   2+ goalscorers, not sure how that would even happen but it's in the pbp

## Cases currently unaccounted for + currently unfixable

-   games in which a game id has been generated but no data has been entered yet (usually occurs when trying to
    scrape a game that occurred on the same day of scraping)
-   Shootout and 2nd/3rd/etc OT formats, which vary by conference and are not currently recorded in stats.ncaa.org
-   Empty net strength (no obvious/consistent markers distinguishing a pulled goalie for an extra attacker, so not included)

If you find an issue, please open an issue in the "Issues" tab. For any other questions or comments,
please contact carleenmarkey@gmail.com

## Data format

The following documentation was modified from https://github.com/bigdatacup/Big-Data-Cup-2021/

-   Date (e.g. ‘2020-12-23’. Format = ‘yyyy-mm-dd’)
-   Game ID (unique game ID that appears at the end of https://stats.ncaa.org/game/play_by_play/)
-   Home Team (e.g. ‘Maine’)
-   Away Team (e.g. ‘Long Island University’)
-   Period (range from 1-3 for regulation, 4+ for overtime)
-   Clock (e.g. ‘00:19:34.0’. Format = ‘hh:mm:ss.ff’. If timestamps from the pbp are missing or not in that format, they will be left blank)
-   Home Team Skaters (range from 3-5 for home skaters currently on the ice)
-   Away Team Skaters (range from 3-6 for away skaters currently on the ice)
-   Home Team Goals (current goals scored by the home team at the time of the event)
-   Away Team Goals (current goals scored by the away team at the time of the event)
-   Team (name of the team responsible for the event)
-   Player (name of the player responsible for the event)
-   Event (type of event, e.g. ‘Play’, ‘Shot’, …)
-   Detail 1-2 (up to 2 supplementary details for each event, varies by event type)
-   Player 2 (name of a secondary player involved in an event, varies by event type)
-   Goalie (only shows up in the "Goalie" column if they have explicitly been named in the pbp. I assume this means they actually came in contact with the puck when making a save. Traditional SV% is not calculated this way, but the NCAA does this for whatever reason)

### Event Types

Shot

-   Player: Shooter
-   Player 2: Blocker if shot blocked
-   Detail 1: Shot Type (Wide, Missed, Blocked)
-   Detail 2: One timer (true or false)
-   Goalie: Goalie who made the save

Goal

-   Player: Shooter
-   Detail 1: first assist, if it exists
-   Detail 2: Second assist, if it exists

Faceoff Won

-   Player: Skater who won the draw
-   Player 2: Skater who lost the draw

Player Penalty

-   Player: Player who committed the infraction
-   Detail 1: Infraction Type (e.g. Slashing, Tripping, Roughing, Hooking, ...)
-   Detail 2: length of penalty
