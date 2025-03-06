# -*- coding: utf-8 -*-
"""ControlConAproximaciones.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/github/MrCharli03/RL_BFRRCE/blob/main/src/ControlConAproximaciones.py

Author: Esteban Becerra, Carlos Cruzado, Anastasiya Ruzhytska Email: esteban.becerraf@um.es carlos.cruzadoe1@um.es anastasiya.r.r@um.es Date: 2025/02/24
"""

#@title Importación de librerias

import gymnasium as gym
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict

class SARSA_SemiGradient:
    def __init__(self, env, lr=0.01, gamma=0.99, epsilon=0.1):
        self.env = env
        self.gamma = gamma
        self.epsilon = epsilon
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.q_network = DQN(env.observation_space.shape[0], env.action_space.n).to(self.device)
        self.optimizer = optim.Adam(self.q_network.parameters(), lr=lr)
        self.loss_fn = nn.MSELoss()

    def policy(self, state):
        """Política ε-greedy."""
        if np.random.rand() < self.epsilon:
            return self.env.action_space.sample()

        state_tensor = torch.tensor(state, dtype=torch.float32).to(self.device).unsqueeze(0)
        with torch.no_grad():
            return torch.argmax(self.q_network(state_tensor)).item()

    def train(self, num_episodes=1000):
        episode_rewards = []

        for _ in range(num_episodes):
            state = self.env.reset(seed=42)
            action = self.policy(state)
            done = False
            total_reward = 0

            while not done:
                next_state, reward, done, info = self.env.step(action)
                next_action = self.policy(next_state)

                state_tensor = torch.tensor(state, dtype=torch.float32).to(self.device).unsqueeze(0)
                next_state_tensor = torch.tensor(next_state, dtype=torch.float32).to(self.device).unsqueeze(0)

                loss = self.loss_fn(
                    self.q_network(state_tensor)[0, action],
                    reward + self.gamma * self.q_network(next_state_tensor)[0, next_action]
                )

                self.optimizer.zero_grad()
                loss.backward()
                self.optimizer.step()

                state, action = next_state, next_action
                total_reward += reward

            episode_rewards.append(total_reward)

        return episode_rewards

import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import random
import gym
from collections import deque

# Red neuronal DQN con dos capas ocultas y activación ReLU
class DQN(nn.Module):
    def __init__(self, state_dim, action_dim):
        super(DQN, self).__init__()
        self.fc = nn.Sequential(
            nn.Linear(state_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 128),
            nn.ReLU(),
            nn.Linear(128, action_dim)
        )

    def forward(self, x):
        return self.fc(x)


class DQNAgent:
    def __init__(self, env, lr=0.001, gamma=0.99, epsilon=1.0, epsilon_decay=0.995, epsilon_min=0.01, buffer_size=10000, batch_size=64, update_target=100):
        self.env = env
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.epsilon_min = epsilon_min
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.q_network = DQN(env.observation_space.shape[0], env.action_space.n).to(self.device)
        self.target_network = DQN(env.observation_space.shape[0], env.action_space.n).to(self.device)
        self.target_network.load_state_dict(self.q_network.state_dict())  # Inicializa target igual a la principal
        self.target_network.eval()  # La red objetivo NO se entrena directamente

        self.optimizer = optim.Adam(self.q_network.parameters(), lr=lr)
        self.loss_fn = nn.MSELoss()

        self.memory = deque(maxlen=buffer_size)  # Replay Buffer optimizado
        self.batch_size = batch_size
        self.update_target = update_target
        self.steps = 0  # Contador para actualizar red objetivo

    def policy(self, state):
        """Política ε-greedy."""
        if np.random.rand() < self.epsilon:
            return self.env.action_space.sample()
        state_tensor = torch.tensor(state, dtype=torch.float32).to(self.device).unsqueeze(0)
        with torch.no_grad():
            return torch.argmax(self.q_network(state_tensor)).item()

    def store_experience(self, state, action, reward, next_state, done):
        """Almacena experiencias en el Replay Buffer."""
        if done:
            next_state = np.zeros_like(state)  # Si el episodio termina, next_state es un array de ceros
        self.memory.append((state, action, reward, next_state, done))

    def train(self, num_episodes=1000):
        episode_rewards = []

        for _ in range(num_episodes):
            state = self.env.reset(seed=42)
            done = False
            total_reward = 0

            while not done:
                action = self.policy(state)
                next_state, reward, done, info = self.env.step(action)

                self.store_experience(state, action, reward, next_state, done)
                self.learn_from_experience()

                state = next_state
                total_reward += reward

                # Actualiza la red objetivo cada `update_target` pasos
                self.steps += 1
                if self.steps % self.update_target == 0:
                    self.target_network.load_state_dict(self.q_network.state_dict())

            # Decaimiento de epsilon para mejorar exploración-explotación
            self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)
            episode_rewards.append(total_reward)

        return episode_rewards

    def learn_from_experience(self):
        """Entrena la red neuronal usando experiencias de Replay Buffer."""
        if len(self.memory) < self.batch_size:
            return

        batch = random.sample(self.memory, self.batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)

        # Se convierten listas en numpy arrays uniformes
        states = np.vstack(states)
        next_states = np.vstack(next_states)

        # Convertimos a tensores de PyTorch
        states = torch.tensor(states, dtype=torch.float32).to(self.device)
        actions = torch.tensor(actions, dtype=torch.int64).to(self.device)
        rewards = torch.tensor(rewards, dtype=torch.float32).to(self.device)
        next_states = torch.tensor(next_states, dtype=torch.float32).to(self.device)
        dones = torch.tensor(dones, dtype=torch.float32).to(self.device)

        # Calcular valores Q actuales y los valores target usando la red objetivo
        q_values = self.q_network(states).gather(1, actions.unsqueeze(1)).squeeze(1)
        next_q_values = self.target_network(next_states).max(1)[0].detach()
        target_q_values = rewards + (self.gamma * next_q_values * (1 - dones))

        # Backpropagation
        loss = self.loss_fn(q_values, target_q_values)
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()