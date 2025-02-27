# Best_Ball_Draft_Helper
This is a repository of python code intended to use data analysis and machine learning techniques to help me draft in my fantasy football Leagues.

We primarily use the Python data science library Pandas to perform data analysis on fantasy football data. For machine learning purposes, we use PyTorch and TensorFlow/Keras.

Planned additions/updates: 

- ~~Multi-agent reinforcement learning algorithms for optimizing draft picks (DQL, PPO, A2C, etc.)~~
- Integrate Sleeper.com API into RL algorithms.
- Best-Ball live draft board using Sleeper.com API (Waiting for the offseason due to API particularities)
- Update Touchdown Regression files for 2025 season (Waiting for nfl_data_py update)

-------------------------------------------------------------------------------------------------------------------------------
**Best Ball**

Contains three python scripts. Get_Sleeper_Player_Map.py should be run once a season after each draft to update it with rookies. Best_Ball_Draft_Board.py should be run once on draft day and generates a complete best ball draft board including projected fantasy point, ADP, VOR and other statistical data. Best_Ball_Live_Draft.py is meant to be run during each of your Sleeper.com picks and provides an up-to-date version of the best ball draft board.

**Draft_Optimizer**

Contains a variety of increasingly complex multi-agent reinforcement learning algorithms which train on the real-world draft board data provided by Best_Ball_Live_Draft.py. Current status of implementations:
1. Tabular Q-Learning (MAQL): Implemented. 
2. Deep Q-Learning (MADQL): Implemented. 
3. Advantage Actor-Critic (A2C): Implemented. Best performing algorithm.
4. Proximal Policy Optimization (PPO): Implemented. Near equal performance to A2C.

Thunderdome.py: A competitive evaluation environment where three agents of each of the above types draft against one another. Points per type are added up and a winner is deduced from the largest total points. We use this to evaluate the algorithms against one another.
![screenshot](Draft_Optimizer/thunderdome_1000.png)

Note: Due to the limitations of Q-learning, we Q-agent's state only encompasses its own team. The deep learning algorithms all take into account the other teams compositions.

**Dynasty**

Contains two python scripts and one called auxiliary file. Get_Sleeper_Player_Map.py should be run once a season after each draft to update it with rookies. Dynasty_Draft_Board.py should be run once on draft day and provides a complete dynasty draft board for your Sleeper.com league.

**Touchdown Regression**

Contains three python scripts meant to compute touchdown regression candidacy for the 2023 season (will update each offseason). We import play-by-play data from 2000-2022 via nfl_data_py and compute the expected touchdowns vs actual touchdowns for each non-rookie RB, WR, and TE player in the 2023 season. Each script generates a .csv file.
