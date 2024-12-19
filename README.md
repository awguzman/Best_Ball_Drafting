# Best_Ball_Draft_Helper
This is a repository of python code intended to use data analysis and machine learning techniques to help me draft in my Fantasy football Leagues.

We primarily use the Python data analysis library Pandas to perform data analysis on fantasy football data.

Planned additions: 

Advance Actor-Critic method for optimal draft picks

-------------------------------------------------------------------------------------------------------------------------------
**Best Ball**

Contains three python scripts. Get_Sleeper_Player_Map.py should be run once a season after each draft to update it with rookies. Best_Ball_Draft_Board.py should be run once on draft day and generates a complete best ball draft board including projected fantasy point, ADP, VOR and other statistical data. Best_Ball_Live_Draft.py is meant to be run during each of your Sleeper.com picks and provides an up-to-date version of the best ball draft board.

**Dynasty**

Contains two python scripts and one called auxilary file. Get_Sleeper_Player_Map.py should be run once a season after each draft to update it with rookies. Dynasty_Draft_Board.py should be run once on draft day and provides a complete dynasty draft board for your Sleeper.com league.

**Touchdown Regression**

Contains three python scripts meant to compute touchdown regression candidacy for the 2023 season (will update each offseason). We import play-by-play data from 2000-2022 via nfl_data_py and compute the expected touchdowns vs actual touchdowns for each non-rookie RB, WR, and TE player in the 2023 season. Each script generates a .csv file.
