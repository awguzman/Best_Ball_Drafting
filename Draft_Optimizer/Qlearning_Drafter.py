"""
This file constructs and trains a multi-agent Q-Learning algorithm to optimally draft a fantasy football team.
We take as input the Best_Ball_Draft_Board.cvs generated by Best_Ball_Draft_Board.py
This is very much a work in progress with this being the first practice step in implementing increasingly complex algorithms.
"""

import numpy as np
import pandas as pd
import random
import matplotlib.pyplot as plt
from collections import defaultdict


class QAgent:
    def __init__(self, team_id, learning_rate=0.2, discount_factor=0.9, epsilon=1.0, epsilon_decay=0.999,
                 epsilon_min=0.05):
        """ Initialize an individual agent for a team. """
        self.team_id = team_id  # Team identification for this agent
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.epsilon_min = epsilon_min
        self.q_table = defaultdict(float)  # Q-table to store state-action values for this agent
        self.drafted_players = []  # List to store drafted players for this agent
        self.total_reward = 0  # Store the total accumulated reward for this agent
        self.position_counts = {position: 0 for position in position_limits}  # Track drafted positions

    def reset_agent(self):
        """Reset the agent's state for a new episode."""
        self.drafted_players = []
        self.total_reward = 0
        self.position_counts = {position: 0 for position in position_limits}  # Reset position counts

    def reset_q_table(self):
        """Reset the Q-table."""
        self.q_table = defaultdict(float)

    def get_state(self, available_players, round_number):
        """Get the current state representation for the agent."""
        return (tuple(sorted(self.drafted_players)), round_number)

    def choose_action(self, state, available_players):
        """Choose an action using an epsilon-greedy policy."""
        if random.random() < self.epsilon:  # With probability epsilon, choose a random action.
            return random.choice(available_players.index.tolist())
        else:  # Otherwise, choose the best action.
            return max(available_players.index, key=lambda player: self.q_table[(state, player)])

    def update_q_table(self, state, action, reward, next_state, available_players):
        """Update the Q-table using the Q-learning formula."""
        best_next_action = max(available_players.index, key=lambda player: self.q_table[(next_state, player)],
                               default=0)
        td_target = reward + self.discount_factor * self.q_table[(next_state, best_next_action)]
        td_delta = td_target - self.q_table[(state, action)]
        self.q_table[(state, action)] += self.learning_rate * td_delta


class FantasyDraft:
    def __init__(self, player_data, num_teams, num_rounds):
        """ Initialize the multi-agent draft simulation. """
        self.player_data = player_data  # Expects a pandas DataFrame.
        self.num_teams = num_teams
        self.num_rounds = num_rounds
        self.agents = [QAgent(team_id=i) for i in range(num_teams)]
        self.reset_draft()
        self.reward_history = {i: [] for i in range(num_teams)}  # Track rewards for debug purposes.
        self.epsilon_history = {i: [] for i in range(num_teams)}  # Track epsilon values for debug  purposes.
        self.draft_order = list(range(num_teams))

    def reset_draft(self):
        """Reset the draft for a new episode."""
        self.available_players = self.player_data.copy()
        self.current_round = 0
        self.current_team = 0
        self.draft_order = list(range(self.num_teams))  # Reset draft order
        for agent in self.agents:
            agent.reset_agent()

    def run_episode(self, verbose=False):
        """Run a single episode of the draft."""
        self.reset_draft()
        while self.current_round < self.num_rounds:
            for team in self.draft_order:
                agent = self.agents[team]
                state = agent.get_state(self.available_players, self.current_round)

                # Filter available players to respect position caps
                valid_players = self.available_players[
                    self.available_players['position'].apply(
                        lambda pos: agent.position_counts[pos] < position_limits[pos]
                    )
                ]

                # Check if there are any draftable players.
                if valid_players.empty:
                    raise Exception("There are no valid players for the agent to draft from!")

                action = agent.choose_action(state, valid_players)

                drafted_player = self.available_players.loc[action]
                agent.drafted_players.append(drafted_player["player_name"])
                agent.position_counts[drafted_player["position"]] += 1  # Increment position count
                reward = drafted_player["projected_points"]
                agent.total_reward += reward

                if verbose:
                    # Debug log for individual action choices.
                    print(f"Round {self.current_round} Team {agent.team_id}: Pick " + drafted_player["player_name"] +
                          " " + drafted_player["position"] + f", Reward " + str(drafted_player["projected_points"]))

                self.available_players = self.available_players.drop(action)

                next_state = agent.get_state(self.available_players, self.current_round + 1)
                agent.update_q_table(state, action, reward, next_state, self.available_players)

            self.current_round += 1  # Move to next round after all teams have picked.
            self.draft_order.reverse()  # Reverse the draft order for snake draft formats.

    def train(self, num_episodes, verbose=False):
        """Train the agents over multiple episodes."""
        for episode in range(num_episodes):
            self.run_episode(verbose=False)
            for agent in self.agents:
                agent.epsilon = max(agent.epsilon * agent.epsilon_decay, agent.epsilon_min)  # decay epsilon value.
                self.reward_history[agent.team_id].append(agent.total_reward)  # Log rewards for debug purposes.
                self.epsilon_history[agent.team_id].append(agent.epsilon)  # Log epsilon values for debug purposes.
            # Print episode summary
            print(f"Episode {episode + 1}/{num_episodes} completed.")
            if verbose:
                for agent in self.agents:
                    print(
                        f"  Team {agent.team_id}: Total Reward = {round(agent.total_reward, 2)}, Drafted Players = {agent.drafted_players}")
        print("Training complete!")

    def run_draft(self):
        """Run one full draft without any exploration."""
        self.reset_draft()
        while self.current_round < self.num_rounds:
            for team in self.draft_order:
                agent = self.agents[team]
                agent.epsilon, agent.epsilon_min = 0, 0
                state = agent.get_state(self.available_players, self.current_round)

                # Filter available players to respect position caps
                valid_players = self.available_players[
                    self.available_players['position'].apply(
                        lambda pos: agent.position_counts[pos] < position_limits[pos]
                    )
                ]

                # Check if there are any draftable players.
                if valid_players.empty:
                    raise Exception("There are no valid players for the agent to draft from!")

                action = agent.choose_action(state, valid_players)

                drafted_player = self.available_players.loc[action]
                agent.drafted_players.append(drafted_player["player_name"])
                agent.position_counts[drafted_player["position"]] += 1  # Increment position count
                reward = drafted_player["projected_points"]
                agent.total_reward += reward

                self.available_players = self.available_players.drop(action)

                next_state = agent.get_state(self.available_players, self.current_round + 1)
                agent.update_q_table(state, action, reward, next_state, self.available_players)

            self.current_round += 1  # Move to next round after all teams have picked.
            self.draft_order.reverse()  # Reverse the draft order for snake draft formats.

        for agent in self.agents:
            print( f"  Team {agent.team_id}: Total Reward = {round(agent.total_reward, 2)}, Drafted Players = {agent.drafted_players}")

    def plot_results(self):
        """Plot the learning progress for debug purposes."""
        # Plot total rewards
        plt.figure(figsize=(12, 6))
        for team_id, rewards in self.reward_history.items():
            # Compute a moving average for total rewards.
            smoothed_rewards = pd.Series(rewards).rolling(window=50).mean()
            plt.plot(smoothed_rewards, label=f"Team {team_id} Total Rewards")
        plt.title("Total Rewards Over Episodes")
        plt.xlabel("Episode")
        plt.ylabel("Total Reward (Moving Average)")
        plt.legend()
        plt.show()

        # Plot epsilon values
        plt.figure(figsize=(12, 6))
        for team_id, epsilons in self.epsilon_history.items():
            plt.plot(epsilons, label=f"Team {team_id} Epsilon")
            plt.title("Epsilon Decay Over Episodes")
            plt.xlabel("Episode")
            plt.ylabel("Epsilon")
            plt.legend()
            plt.show()


# Debug draft environment
# player_data = pd.DataFrame({
#     "player_name": ["QB1", "QB2", "QB3", "QB4", "QB5", "RB1", "RB2", "RB3", "RB4", "RB5",
#                     "WR1", "WR2", "WR3", "WR4", "WR5", "TE1", "TE2", "TE3", "TE4", "TE5"],
#     "position": ["QB", "QB", "QB", "QB", "QB", "RB", "RB", "RB", "RB", "RB",
#                  "WR", "WR", "WR", "WR", "WR", "TE", "TE", "TE", "TE", "TE"],
#     "projected_points": [360, 330, 300, 270, 240, 280, 220, 180, 150, 120,
#                          210, 170, 150, 140, 120, 140, 110, 80, 70, 60]
# })

# Player data provided by FantasyPros.com.
player_data = pd.read_csv("../Best_Ball/Best_Ball_Draft_Board.csv").drop('Unnamed: 0', axis=1).rename(columns={
    "Player": "player_name", "POS": "position", "Fantasy Points": "projected_points"})

num_teams = 10
num_rounds = 20
position_limits = {"QB": 3, "RB": 6, "WR": 8, "TE": 3}
draft_simulator = FantasyDraft(player_data, num_teams, num_rounds)


# Debug Training
draft_simulator.train(10000, verbose=False)
draft_simulator.plot_results()
draft_simulator.run_draft()



def experiment_with_parameters(draft_simulator, learning_rates, discount_factors, num_episodes):
    """Runs experiments for finding best performing learning rates and discount factors."""
    results = []
    for rates in learning_rates:
        for factor in discount_factors:
            # Update agents with new parameters and reset their Q-tables.
            for agent in draft_simulator.agents:
                agent.learning_rate = rates
                agent.discount_factor = factor
                agent.reset_q_table()

            # Train and collect results
            draft_simulator.train(num_episodes, verbose=False)
            avg_rewards = [np.mean(rewards) for rewards in draft_simulator.reward_history.values()]
            results.append({"learning_rate": rates,
                            "discount_factor": factor,
                            "average_reward": np.mean(avg_rewards)
                            })
            print(f"Experiment complete for learning rate {rates} and discount factor {factor}")

            # Reset simulator
            draft_simulator.reset_draft()

    return pd.DataFrame(results).sort_values(by="average_reward", ascending=False)


learning_rates = [0.15, 0.2, 0.25, 0.3]
discount_factors = [0.5, 0.75, 0.9, 0.95, 0.99]
num_episodes = 1000

# learning_results_df = experiment_with_parameters(draft_simulator, learning_rates, discount_factors, num_episodes)
# print(learning_results_df)


def experiment_with_epsilon(draft_simulator, epsilon_values, epsilon_decay_values, epsilon_min_values, num_episodes):
    """Runs experiments for finding the best epsilon values for the Epsilon-Greedy Policy."""
    results = []
    for epsilon in epsilon_values:
        for epsilon_decay in epsilon_decay_values:
            for epsilon_min in epsilon_min_values:
                for agent in draft_simulator.agents:
                    agent.epsilon = epsilon
                    agent.epsilon_decay = epsilon_decay
                    agent.epsilon_min = epsilon_min
                    agent.reset_q_table()

                draft_simulator.train(num_episodes, verbose=False)
                avg_rewards = [np.mean(rewards) for rewards in draft_simulator.reward_history.values()]
                results.append({
                    "epsilon": epsilon,
                    "epsilon_decay": epsilon_decay,
                    "epsilon_min": epsilon_min,
                    "average_reward": np.mean(avg_rewards)
                })
                print(f"Experiment complete for epsilon {epsilon}, decay {epsilon_decay} and minimum {epsilon_min}")

                # Reset simulator
                draft_simulator.reset_draft()

    return pd.DataFrame(results).sort_values(by="average_reward", ascending=False)


epsilon_values = [1.0]
epsilon_decay_values = [0.99, 0.995, 0.999]
epsilon_min_values = [0.01, 0.05, 0.1, 0.2]
num_episodes = 1000

# epsilon_results_df = experiment_with_epsilon(draft_simulator, epsilon_values, epsilon_decay_values, epsilon_min_values, num_episodes)
# print(epsilon_results_df)
