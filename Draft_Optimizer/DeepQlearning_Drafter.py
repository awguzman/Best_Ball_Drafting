"""
This file constructs and trains a multi-agent Deep Q-Learning algorithm with Softmax exploration to optimally
draft a fantasy football team.
We take as input the Best_Ball_Draft_Board.cvs generated by Best_Ball_Draft_Board.py
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import StepLR

import warnings
# Suppress a warning from PyTorch that isn't valid due to batch_size in the replay buffer being larger than step_size in the LR scheduler
warnings.filterwarnings(
    "ignore",
    message=r"Detected call of `lr_scheduler.step\(\)` before `optimizer.step\(\)`",
    category=UserWarning,
)

class QNetwork(nn.Module):
    """Define neural networks used to predict our Q-values."""

    def __init__(self, state_size, action_size, hidden_layers):
        super(QNetwork, self).__init__()
        self.network = self.create_layers(state_size, action_size, hidden_layers)

    @staticmethod
    def create_layers(state_size, action_size, hidden_layers):
        """Helper method to create layers for the QNetwork."""
        layers = []
        input_size = state_size
        for hidden_size in hidden_layers:
            layers.append(nn.Linear(input_size, hidden_size))
            layers.append(nn.ReLU())
            input_size = hidden_size
        layers.append(nn.Linear(input_size, action_size))
        return nn.Sequential(*layers)

    def forward(self, state):
        return self.network(state)


class DeepQAgent:

    def __init__(self, team_id, state_size, action_size, hidden_layers, position_limits, learning_rate=5e-3,
                 discount_factor=0.8, temperature=1.0, temperature_min=0.1, temperature_decay=.999, max_norm=1.0):
        """ Initialize an individual agent for a team. """
        self.team_id = team_id  # Team identification for this agent
        self.position_limits = position_limits

        # Q-function hyperparameters
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor

        # Parameters for softmax exploration.
        self.temperature = temperature
        self.temperature_min = temperature_min
        self.temperature_decay = temperature_decay

        # Initialize Q-networks used for approximating Q-values.
        self.q_network = QNetwork(state_size, action_size, hidden_layers)
        self.target_network = QNetwork(state_size, action_size, hidden_layers)  # Double Q-learning
        self.optimizer = optim.AdamW(self.q_network.parameters(), lr=self.learning_rate)
        self.scheduler = StepLR(self.optimizer, step_size=2000, gamma=0.25)  # Reduce LR by a factor of 0.25 every 2000 steps.
        self.loss_fn = nn.SmoothL1Loss()  # Huber loss.
        self.max_norm = max_norm  # maximum gradient norm for gradient clipping.

        self.drafted_players = []  # List to store drafted players for this agent
        self.total_reward = 0  # Store the total accumulated reward for this agent
        self.total_points = 0  # Store the total accumulated fantasy points for this agent.
        self.position_counts = {"QB": 0, "RB": 0, "WR": 0, "TE": 0}  # Track drafted position counts

    def reset_agent(self):
        """Reset the agent's initial state for a new episode."""
        self.drafted_players = []
        self.total_reward = 0
        self.total_points = 0
        self.position_counts = {"QB": 0, "RB": 0, "WR": 0, "TE": 0}

    def get_state(self, all_agents):
        """Get the current state for the agent. We keep track of the position counts for all teams in the draft."""
        position_counts_tensor = torch.tensor(list(self.position_counts.values()), dtype=torch.float32) # Current agent's state

        # Other teams' position counts
        other_teams_counts = []
        for agent in all_agents:
            if agent.team_id != self.team_id:
                other_teams_counts.extend(agent.position_counts.values())
        other_teams_tensor = torch.tensor(other_teams_counts, dtype=torch.float32)

        # Combine into a single state tensor
        return torch.cat((position_counts_tensor, other_teams_tensor))

    def choose_action(self, state, exploit=False):
        """Choose an action using a softmax exploration policy."""
        state_tensor = state.unsqueeze(0)
        if exploit:  # Choose the best action if we are in an exploitative episode.
            action = self.q_network(state_tensor).argmax(dim=1).item()
        else:  # Otherwise, use softmax exploration.
            with torch.no_grad():
                q_values = self.q_network(state_tensor).squeeze(0)
                probabilities = torch.softmax(q_values / self.temperature, dim=0)
                action = torch.multinomial(probabilities, 1).item()
        return action

    def update_q_network(self, states, actions, rewards, next_states, dones, q_verbose=False):
        """Update the Q-network with double Q-learning using a batch of experiences."""
        # Compute current Q-values
        q_values = self.q_network(states).gather(1, actions.unsqueeze(1))

        # Compute target Q-values
        with torch.no_grad():
            next_q_values = self.target_network(next_states).max(dim=1)[0]
            target_q_values = rewards + (1 - dones) * self.discount_factor * next_q_values

        # Compute loss
        loss = self.loss_fn(q_values, target_q_values.unsqueeze(1))

        # Backpropagation
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.q_network.parameters(), self.max_norm)  # Gradient clipping.
        self.optimizer.step()


class ReplayBuffer:

    def __init__(self, capacity):
        """Initialize a shared replay buffer."""
        self.buffer = []
        self.capacity = capacity

    def add(self, experience):
        """Add a new experience to the buffer."""
        if len(self.buffer) >= self.capacity:
            self.buffer.pop(0)  # Remove the oldest experience if buffer is at capacity.
        self.buffer.append(experience)

    def sample(self, batch_size):
        """Sample a batch of experiences for Q-network updating."""
        indices = np.random.choice(len(self.buffer), batch_size, replace=False)
        batch = [self.buffer[i] for i in indices]
        # Unpack the batch into separate tensors
        states, actions, rewards, next_states, dones = zip(*batch)
        return (
            torch.stack(states),
            torch.tensor(actions, dtype=torch.long),
            torch.tensor(rewards, dtype=torch.float32),
            torch.stack(next_states),
            torch.tensor(dones, dtype=torch.float32),
        )


class FantasyDraft:

    def __init__(self, player_data, num_teams, num_rounds, state_size, action_size, hidden_layers, position_limits):
        """ Initialize the multi-agent draft simulation. """

        self.player_data = player_data.sort_values(by="projected_points", ascending=False)  # Expects a pandas DataFrame.
        self.num_teams = num_teams
        self.num_rounds = num_rounds
        self.draft_order = list(range(num_teams))
        self.position_limits = position_limits
        self.agents = [DeepQAgent(team_id=i, state_size=state_size, action_size=action_size, hidden_layers=hidden_layers,
                                  position_limits=position_limits) for i in range(num_teams)]

        # Setup replay buffer.
        self.batch_size = 240  # Batch a full draft of experiences.
        self.replay_buffer = ReplayBuffer(capacity=2400)  # Shared replay buffer equivalent to 10 drafts of experiences.

        # Track rewards and temperatures for debug purposes.
        self.reward_history = {i: [] for i in range(num_teams)}
        self.temperature_history = {i: [] for i in range(self.num_teams)}

        self.max_points_by_position = player_data.groupby("position")["projected_points"].max()  # Cache max possible points by position for reward normalization.
        self.target_update_frequency=10
        self.reset_draft()  # Get the environment ready for training.

    def reset_draft(self):
        """Reset the draft for a new episode."""
        self.available_players = self.player_data.copy()
        self.current_round = 0
        self.current_team = 0
        self.draft_order = list(range(self.num_teams))  # Reset draft order
        for agent in self.agents:
            agent.reset_agent()

    def run_episode(self, verbose=False, exploit=False):
        """Run a single episode of the draft."""
        self.reset_draft()
        while self.current_round < self.num_rounds:
            for team in self.draft_order:
                agent = self.agents[team]
                state = agent.get_state(self.agents)

                # Choose action and find the players corresponding to said action.
                action = agent.choose_action(state, exploit=exploit)
                position = list(self.position_limits.keys())[action]
                available_players = self.available_players[self.available_players["position"] == position]

                # If the action was invalid, punish and lose turn.
                if available_players.empty:
                    reward = -1
                    agent.total_reward += reward
                    next_state = agent.get_state(self.agents)
                    experience = (state, action, reward, next_state, False)
                    self.replay_buffer.add(experience)
                    continue

                # Draft the best player for the action.
                drafted_player = available_players.iloc[0]
                drafted_player_index = drafted_player.name

                # Add this player to the team.
                agent.total_points += drafted_player["projected_points"]
                agent.drafted_players.append(drafted_player["player_name"] + " " + drafted_player["position"])
                agent.position_counts[drafted_player["position"]] += 1

                # Compute reward and next state
                reward = self.get_reward(drafted_player, agent)
                agent.total_reward += reward
                next_state = agent.get_state(self.agents)

                # Add this experience to the replay buffer.
                experience = (state, action, reward, next_state, False)
                self.replay_buffer.add(experience)

                # Remove drafted player from the draft board.
                self.available_players = self.available_players.drop(drafted_player_index)

            self.current_round += 1
            self.draft_order.reverse()

        # Print episode summary
        if verbose:
            sum_rewards, sum_points = 0, 0
            for agent in self.agents:
                sum_rewards += agent.total_reward
                sum_points += agent.total_points
                print(
                    f"  Team {agent.team_id}: Total Reward = {round(agent.total_reward, 2)}, Position Counts = {agent.position_counts}, Drafted Players = {agent.drafted_players} ({round(agent.total_points, 2)} pts)")
            avg_reward = sum_rewards / self.num_teams
            avg_points = sum_points / self.num_teams
            print(f"Average total reward = {avg_reward}, Average total fantasy points = {avg_points}")

    def get_reward(self, drafted_player, agent):
        """Calculate the reward attained for drafting a given player by normalizing it with respect to the maximum
        possible points for that position. If we are exceeding position limits, give negative reward."""
        reward = drafted_player["projected_points"] / self.max_points_by_position[drafted_player["position"]]

        if agent.position_counts[drafted_player["position"]] > self.position_limits[drafted_player["position"]]:
            over_draft_penalty = agent.position_counts[drafted_player["position"]] - self.position_limits[
                drafted_player["position"]]

            if 0 in agent.position_counts.values():
                over_draft_penalty += 1

            reward = -(over_draft_penalty * reward)
            if reward < -1:
                reward = -1

        return reward

    def train(self, num_episodes, verbose=False):
        """Train the agents over multiple episodes."""
        for episode in range(num_episodes):
            self.run_episode(exploit=False)
            for agent in self.agents:
                # If replay buffer is large enough, train Q-Network on a random sample.
                if len(self.replay_buffer.buffer) >= self.batch_size:
                    batch = self.replay_buffer.sample(self.batch_size)
                    agent.update_q_network(*batch)

                agent.scheduler.step()  # Increment the step count on the learning rate scheduler.
                agent.temperature = max(agent.temperature * agent.temperature_decay,
                                        agent.temperature_min)  # decay temp value.
                self.reward_history[agent.team_id].append(agent.total_reward)  # Log rewards for debug purposes.

            # Update target networks periodically
            if episode % self.target_update_frequency == 0:
                for agent in self.agents:
                    agent.target_network.load_state_dict(agent.q_network.state_dict())

            if verbose:
                print(f"Episode {episode + 1}/{num_episodes} completed.")

    def plot_results(self):
        """Plot the learning progress for debug purposes."""
        plt.figure(figsize=(12, 6))
        for team_id, rewards in self.reward_history.items():
            # Compute and plot a moving average for total rewards for each team.
            smoothed_rewards = pd.Series(rewards).rolling(window=50).mean()
            plt.plot(smoothed_rewards, label=f"Team {team_id + 1} Total Rewards")

        plt.title("Total Rewards Over Episodes")
        plt.xlabel("Episode")
        plt.ylabel("Total Reward (Moving Average)")
        plt.legend()
        plt.show()

# Function to run a full training routine.
def run_training_routine():
    # Pandas database of 400 player draft board from FantasyPros.com
    player_data = pd.read_csv("../Best_Ball/Best_Ball_Draft_Board.csv").drop('Unnamed: 0', axis=1).rename(columns={
        "Player": "player_name", "POS": "position", "Fantasy Points": "projected_points"})

    # Setup draft parameters.
    num_teams = 12
    num_rounds = 20
    position_limits = {"QB": 3, "RB": 7, "WR": 8, "TE": 3}

    # Setup neural network structure parameters.
    state_size = len(position_limits) * num_teams   # position_counts + round_number + other_teams_position_counts
    action_size = len(position_limits)
    num_layers = 3  # Number of hidden layers.
    hidden_size = int(np.ceil(
        state_size * (2 / 3))) + action_size  # Dynamically increase hidden neuron number with both action and state sizes.
    hidden_layers = [hidden_size] * num_layers

    # Construct the draft environment.
    draft_simulator = FantasyDraft(player_data, num_teams, num_rounds, state_size, action_size, hidden_layers,
                                   position_limits)

    # Setup training routine.
    temperatures = [3.0, 2.0, 1.0]
    temperature_mins = [1.0, 0.5, 0.1]
    temperature_decays = [0.9995, 0.99935, 0.9975]
    max_norms = [1.0, 0.75, 0.5]  # Set the maximum norm values for gradient clipping
    num_episodes = [2000, 2000, 1000]

    # Run agents through the training routine.
    for phase in range(len(num_episodes)):
        for agent in draft_simulator.agents:
            agent.temperature = temperatures[phase]
            agent.temperature_min = temperature_mins[phase]
            agent.temperature_decay = temperature_decays[phase]
            agent.max_norm = max_norms[phase]

        print(f"\nBeginning training phase {phase + 1}. Number of episodes in this phase is {num_episodes[phase]}.")
        draft_simulator.train(num_episodes=num_episodes[phase], verbose=False)
        print(f"Phase {phase + 1} complete. Running a test draft with no exploitation.")
        draft_simulator.run_episode(verbose=True, exploit=True)

    # Plot rewards and temperatures for debug purposes.
    draft_simulator.plot_results()

    # Save Q-networks for competitive evaluation.
    for agent in draft_simulator.agents:
        torch.save(agent.q_network.state_dict(), f"Trained_Agents/Deep_Q_Agents/DeepQAgent_{agent.team_id}_Q_Network.pt")

# run_training_routine()