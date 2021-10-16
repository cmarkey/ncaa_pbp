This code is designed to pull WOMEN'S hockey pbp data from stats.ncaa.org, put it
in a format as close to Stathlete's Big Data Cup format as possible, and save it as a csv in the format
"GameYear-GameMonth-GameDay_eventid.csv". See the end of this doc for the full data format.

To use:
• Run "full_scrape.py" with the start (start_date) and end dates (end_date) line you wish to scrape.
• Use ncaa-schedule-finder.py to pull all the event IDs (unique schedule ID that appears in the middle
of https://stats.ncaa.org/contests/2120211/box_score) for games played between specified dates

Currently unaccounted for cases:
- games in which a game id has been generated but no data has been entered yet (usually occurs when trying to
scrape a game that occurred on the same day of scraping)
- occasional pbp data that is a different format than the main format
- games before the 2021 season
- Shootout and 2nd/3rd/etc OT formats, which vary by conference and are not currently recorded in stats.ncaa.org
- Empty net strength
- Powerplays spanning periods

If you find an issue, please open an issue in the "Issues" tab. For any other questions or comments,
please contact carleenmarkey@gmail.com

The following documentation was modified from https://github.com/bigdatacup/Big-Data-Cup-2021/

Data format:
Date (e.g. ‘2020-12-23’. Format = ‘yyyy-mm-dd’)
Game ID (unique game ID that appears at the end of https://stats.ncaa.org/game/play_by_play/)
Home Team (e.g. ‘Maine’)
Away Team (e.g. ‘Long Island University’)
Period (range from 1-3 for regulation, 4+ for overtime)
Clock (e.g. ‘00:19:34.0’. Format = ‘hh:mm:ss.ff’)
Home Team Skaters (range from 3-5 for home skaters currently on the ice)
Away Team Skaters (range from 3-6 for away skaters currently on the ice)
Home Team Goals (current goals scored by the home team at the time of the event)
Away Team Goals (current goals scored by the away team at the time of the event)
Team (name of the team responsible for the event)
Player (name of the player responsible for the event)
Event (type of event, e.g. ‘Play’, ‘Shot’, …)
Detail 1-2 (up to 2 supplementary details for each event, varies by event type)
Player 2 (name of a secondary player involved in an event, varies by event type)
Goalie (only shows up in the "Goalie" column if they have explicitly been named in the pbp.
I assume this means they actually came in contact with the puck when making a save. Traditional SV%
is not calculated this way, but the NCAA does this for whatever reason)

Events

Shot

Players Involved

Player: Shooter
Coordinates

X,Y Coordinate: Release location
Event Details

Detail 1: Shot Type (Deflection, Fan, Slapshot, Snapshot, Wrap around, Wristshot)
Detail 2: Shot destination (on net, missed or blocked)
Detail 3: Traffic (true or false)
Detail 4: One timer (true or false)

Goal
Shot attempts that are successful (goal)

Players Involved

Player: Shooter
Coordinates

X,Y Coordinate: Release location of the puck
Event Details

Detail 1: Shot Type (Deflection, Fan, Slapshot, Snapshot, Wrap around, Wristshot)
Detail 2: Shot destination (on net, missed or blocked)
Detail 3: Traffic (true or false)
Detail 4: One timer (true or false)

Play
Pass attempts that are successful

Event Types

Direct (e.g. a tape-to-tape pass)
Indirect (e.g. a pass that is rimmed along the boards)
Players Involved

Player: Passer
Player 2: Intended pass target
Coordinates

X,Y Coordinate: Pass release location
X,Y Coordinate: Pass target location
Event details

Detail 1: Pass Type

Direct (eg. a tape-to-tape pass)
Indirect (eg. a pass that is rimmed around the boards)

Incomplete Play
Pass attempts that are unsuccessful

Event Types

Direct (e.g. a tape-to-tape pass)
Indirect (e.g. a pass that is rimmed along the boards)
Players Involved

Player: Passer
Player 2: Intended pass target
Coordinates

X,Y Coordinate: Pass release location
X,Y Coordinate: Pass target location
Event details

Detail 1: Pass Type

Direct (eg. a tape-to-tape pass)
Indirect (eg. a pass that is rimmed around the boards)

Takeaway
Steals, pass interceptions and won battles that lead to a change in possession

Players Involved

Player: Skater credited with the takeaway
Coordinates

X,Y Coordinate: Location where the skater gained possession when taking the puck away

Puck Recovery
Possession gains initiated by retrieving a loose puck that was created by a missed/blocked/saved shot, an advance (e.g. dump-out/dump-in), a faceoff or a broken play

Players Involved

Player: Skater who recovered the puck
Coordinates

X,Y Coordinate: Location where skater gained possession

Dump In/Out
Actions in which a skater intentionally concedes possession by advancing the puck up ice

Players Involved

Player: Skater who dumped/advanced the puck
Coordinates

X,Y Coordinate: Location where skater released the puck
Event details

Detail 1: Possession Outcome (Retained, Lost)

Zone Entry
Attempts to move the puck into the offensive zone from the neutral zone

Players Involved

Player: Entry skater
Player 2: Targeted defender
Coordinates

X,Y Coordinate: Point of release for dumps/advances, point where puck crossed the blueline for passes and carries
Event details

Detail 1: Entry Type (Carried, Dumped, Played)

Faceoff Win
Faceoffs

Players Involved

Player: Skater who won the draw
Player 2: Skater who lost the draw
Coordinates

X,Y Coordinate: Location of faceoff dot

Penalty Taken
Infractions

Players Involved

Player: Skater who took the penalty
Player 2: Skater who drew the penalty
Coordinates

X,Y Coordinate: Location of infraction
Event Details

Detail 1: Infraction Type (e.g. Slashing, Tripping, Roughing, Hooking, ...)
Penalties:
Detail 1: Infraction type
Detail 2: length of Penalty
