# -*- coding: utf-8 -*-
"""
Author: Esteban Becerra, Carlos Cruzado, Anastasiya Ruzhytska Email: esteban.becerraf@um.es carlos.cruzadoe1@um.es anastasiya.r.r@um.es Date: 2025/02/24
"""

#@title Importación de librerias

import gymnasium as gym
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict

import numpy as np
from collections import defaultdict

class MonteCarloOnPolicy:
    def __init__(self, env, gamma=1.0, epsilon=0.1):
        self.env = env
        self.gamma = gamma
        self.epsilon = epsilon
        self.Q = defaultdict(lambda: np.zeros(env.action_space.n))
        self.returns = defaultdict(list)
        self.policy = defaultdict(lambda: np.ones(env.action_space.n) / env.action_space.n)
        self.deltas = []  # Para guardar la magnitud de los cambios en Q

    def generate_episode(self):
        episode = []
        state = self.env.reset()[0]  # Gymnasium devuelve (obs, info)
        done = False
        total_reward = 0
        while not done:
            action = np.random.choice(range(self.env.action_space.n), p=self.policy[state])
            next_state, reward, done, truncated, info = self.env.step(action)
            done = done or truncated
            episode.append((state, action, reward))
            state = next_state
            total_reward += reward
        return episode, total_reward

    def train(self, target_policy, num_episodes=5000):
      episode_rewards = []

      # Asegurar que target_policy es un defaultdict con valores por defecto
      target_policy = defaultdict(lambda: np.ones(self.env.action_space.n) / self.env.action_space.n, target_policy)

      # Política de comportamiento (exploratoria uniforme)
      behavior_policy = defaultdict(lambda: np.ones(self.env.action_space.n) / self.env.action_space.n)

      for _ in range(num_episodes):
          episode, total_reward = self.generate_episode(behavior_policy)
          episode_rewards.append(total_reward)

          states, actions, rewards = zip(*episode)
          G = 0
          W = 1
          max_delta = 0  # Para registrar el mayor cambio en Q

          for t in reversed(range(len(episode))):
              state, action, reward = states[t], actions[t], rewards[t]
              G = self.gamma * G + reward

              old_Q = self.Q[state][action]  # Valor Q antes de actualizar

              self.C[state][action] += W
              self.Q[state][action] += (W / self.C[state][action]) * (G - self.Q[state][action])

              # Guardamos el cambio máximo en Q
              max_delta = max(max_delta, abs(old_Q - self.Q[state][action]))

              # Comprobamos que target_policy[state] existe y aplicamos criterio de corte
              optimal_action = np.argmax(target_policy[state])  # Ya garantizado que `state` existe
              if action != optimal_action:
                  break  # Si la acción no es óptima en la target policy, cortamos

              # Actualizamos el peso de importancia
              W *= 1.0 / behavior_policy[state][action]

              # Evitar explosión de W
              if W > 1e6:
                  break

          self.deltas.append(max_delta)  # Guardar el delta de este episodio

      return self.Q, episode_rewards, self.deltas

import numpy as np
from collections import defaultdict

class MonteCarloOffPolicy:
    def __init__(self, env, gamma=1.0):
        self.env = env
        self.gamma = gamma
        self.Q = defaultdict(lambda: np.zeros(env.action_space.n))
        self.C = defaultdict(lambda: np.zeros(env.action_space.n))  # Para ponderación de importancia
        self.deltas = []  # Para guardar los cambios máximos en Q

    def generate_episode(self, behavior_policy):
        episode = []
        state = self.env.reset()[0]
        done = False
        total_reward = 0
        while not done:
            action = np.random.choice(range(self.env.action_space.n), p=behavior_policy[state])
            next_state, reward, done, truncated, info = self.env.step(action)
            done = done or truncated
            episode.append((state, action, reward))
            state = next_state
            total_reward += reward
        return episode, total_reward

    def train(self, target_policy, num_episodes=5000):
        episode_rewards = []

        # Política de comportamiento (exploratoria uniforme)
        behavior_policy = defaultdict(lambda: np.ones(self.env.action_space.n) / self.env.action_space.n)

        for _ in range(num_episodes):
            episode, total_reward = self.generate_episode(behavior_policy)
            episode_rewards.append(total_reward)

            states, actions, rewards = zip(*episode)
            G = 0
            W = 1
            max_delta = 0  # Para registrar el mayor cambio en Q

            for t in reversed(range(len(episode))):
                state, action, reward = states[t], actions[t], rewards[t]
                G = self.gamma * G + reward

                old_Q = self.Q[state][action]  # Valor Q antes de actualizar

                self.C[state][action] += W
                self.Q[state][action] += (W / self.C[state][action]) * (G - self.Q[state][action])

                # Guardamos el cambio máximo en Q
                max_delta = max(max_delta, abs(old_Q - self.Q[state][action]))

                # Comprobamos que target_policy[state] existe
                if state in target_policy:
                    optimal_action = np.argmax(target_policy[state])
                    if action != optimal_action:
                        break  # Si no coincide con la acción óptima, se detiene
                else:
                    break

                # Actualizamos el peso
                W *= 1.0 / behavior_policy[state][action]

            self.deltas.append(max_delta)  # Guardar el delta de este episodio

        return self.Q, episode_rewards, self.deltas
