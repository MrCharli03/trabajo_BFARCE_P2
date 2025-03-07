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

    def train(self, num_episodes=5000):  # ELIMINADO target_policy
        episode_rewards = []

        for _ in range(num_episodes):
            episode, total_reward = self.generate_episode()
            episode_rewards.append(total_reward)

            states, actions, rewards = zip(*episode)
            G = 0
            visited = set()
            max_delta = 0  # Para registrar el mayor cambio en Q

            for t in reversed(range(len(episode))):
                state, action, reward = states[t], actions[t], rewards[t]
                G = self.gamma * G + reward

                if (state, action) not in visited:
                    visited.add((state, action))
                    old_Q = self.Q[state][action]  # Valor Q antes de actualizar
                    self.returns[(state, action)].append(G)
                    self.Q[state][action] = np.mean(self.returns[(state, action)])

                    # Calculamos cuánto cambió el valor Q
                    max_delta = max(max_delta, abs(old_Q - self.Q[state][action]))

                    # Actualización de la política ε-soft
                    best_action = np.argmax(self.Q[state])
                    for a in range(self.env.action_space.n):
                        if a == best_action:
                            self.policy[state][a] = 1 - self.epsilon + (self.epsilon / self.env.action_space.n)
                        else:
                            self.policy[state][a] = self.epsilon / self.env.action_space.n

            self.deltas.append(max_delta)  # Guardamos el cambio máximo de Q en este episodio

        return self.Q, episode_rewards, self.deltas

class MonteCarloOffPolicy:
    def __init__(self, env, gamma=1.0, epsilon=0.5, min_epsilon=0.05, epsilon_decay=0.9995):
        self.env = env
        self.gamma = gamma
        self.epsilon = epsilon
        self.min_epsilon = min_epsilon
        self.epsilon_decay = epsilon_decay
        self.Q = defaultdict(lambda: np.zeros(env.action_space.n))
        self.C = defaultdict(lambda: np.zeros(env.action_space.n))  # Ponderación de importancia acumulada
        self.deltas = []  
        self.episode_rewards = []

    def generate_episode(self, behavior_policy):
        """ Genera un episodio siguiendo la política de comportamiento """
        episode = []
        state = self.env.reset()[0]
        done = False
        total_reward = 0
        while not done:
            action = np.random.choice(range(self.env.action_space.n), p=behavior_policy[state])
            next_state, reward, done, truncated, _ = self.env.step(action)
            done = done or truncated
            episode.append((state, action, reward))
            state = next_state
            total_reward += reward
        return episode, total_reward

    def train(self, num_episodes=5000, target_policy=None):
        """ Entrena la política objetivo con muestreo de importancia ponderado """
        
        if target_policy is None:
            target_policy = defaultdict(lambda: np.ones(self.env.action_space.n) * 0.05)
            for state in self.Q:
                best_action = np.argmax(self.Q[state])
                target_policy[state][best_action] = 0.95  

        # Política de comportamiento más cercana a la política objetivo
        behavior_policy = defaultdict(lambda: np.ones(self.env.action_space.n) * 0.1)  # Más exploración al inicio
        
        for state in self.Q:
            if state not in target_policy:  # Asegurar que target_policy[state] está definido
                target_policy[state] = np.ones(self.env.action_space.n) / self.env.action_space.n  

            best_action = np.argmax(target_policy[state])  
            behavior_policy[state] = np.ones(self.env.action_space.n) * 0.05  # Exploración mínima
            behavior_policy[state][best_action] = 0.95  # Favorecer la mejor acción

            # 🔹 **NORMALIZAR las probabilidades para que sumen 1**
            behavior_policy[state] /= np.sum(behavior_policy[state])  
  

        for episode_idx in range(num_episodes):
            episode, total_reward = self.generate_episode(behavior_policy)
            self.episode_rewards.append(total_reward)

            states, actions, rewards = zip(*episode)
            G = 0  
            W = 1  
            max_delta = 0  

            for t in reversed(range(len(episode))):
                state, action, reward = states[t], actions[t], rewards[t]
                G = self.gamma * G + reward  

                old_Q = self.Q[state][action]  

                self.C[state][action] += W
                self.Q[state][action] += (W / self.C[state][action]) * (G - self.Q[state][action])

                max_delta = max(max_delta, abs(old_Q - self.Q[state][action]))

                if action != np.argmax(target_policy[state]):
                    break  

                behavior_prob = behavior_policy[state][action]  
                target_prob = 1 if action == np.argmax(target_policy[state]) else 0

                if behavior_prob > 0:
                    W *= target_prob / behavior_prob
                else:
                    break  

                W = np.clip(W, 1e-5, 1e5)  # Evita que W sea demasiado grande o pequeño

            self.deltas.append(max_delta)  

            if episode_idx % 100 == 0:  # Reducir `epsilon` menos agresivamente
                self.epsilon = max(self.min_epsilon, self.epsilon * self.epsilon_decay)

        return self.Q, self.episode_rewards, self.deltas

