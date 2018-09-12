from collections import deque

import gym
import numpy as np
import time
import random
from random_batch_deque import RandomBatchDeque

import tensorflow as tf
from tensorflow import keras
import h5py


class DQN():

    def __init__(self, state_size, action_size):
        self.sess = tf.Session()
        self.state_size = state_size
        self.action_size = action_size
        self.memory = deque(maxlen=2000)
        self.gamma = 0.99    # discount rate
        self.epsilon = 1.0  # exploration rate
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.995
        self.learning_rate = 0.00025
        self.rho = 0.95
        self.model = self.generate_model()
        self.queue = tf.FIFOQueue(capacity=100, dtypes=(tf.int8, tf.int8))

    def remember(self, state, action, reward, done):
        self.memory.append((state, action, reward, done))

    def act(self, state):
        if np.random.rand() <= self.epsilon:
            return random.randrange(self.action_size)
        state = tf.slice(state, [0, 0, 0, 0], [4, 105, 80, 1])
        act_values = self.model.predict(state)
        return np.argmax(act_values[0])  # returns action

    def replay(self, batch_size):

        merged = tf.summary.merge_all()
        writer = tf.summary.FileWriter('.')
        writer.add_graph(tf.get_default_graph())

        replay_start_t = int(round(time.time() * 1000))
        minibatch = random.sample(self.memory, batch_size)
        print("Replay1:" + str(int(round(time.time() * 1000)) - replay_start_t), end=",", flush=True)
        #minibatch = self.queue.dequeue(batch_size=batch_size)

        for state, action, reward, done in minibatch:
            target = reward
            print("Replay2:" + str(int(round(time.time() * 1000)) - replay_start_t), end=",", flush=True)
            if not done:
                states_to_be_predicted = tf.slice(state, [1, 0, 0, 0], [4, 105, 80, 1])
                print("Replay3:" + str(int(round(time.time() * 1000)) - replay_start_t), end=",", flush=True)
                #states_to_be_predicted = state[1:5].reshape(4, 1, 105, 80)
                target = reward + self.gamma * np.amax(self.model.predict(states_to_be_predicted, steps=1)[0])
                print("Replay4:" + str(int(round(time.time() * 1000)) - replay_start_t), end=",", flush=True)
            state_f = tf.slice(state, [0, 0, 0, 0], [4, 105, 80, 1])
            print("Replay5:" + str(int(round(time.time() * 1000)) - replay_start_t), end=",", flush=True)
            target_f = self.model.predict(state_f, steps=1)
            print("Replay6:" + str(int(round(time.time() * 1000)) - replay_start_t), end=",", flush=True)
            target_f[0][action] = target
            print("Replay7:" + str(int(round(time.time() * 1000)) - replay_start_t), end=",", flush=True)
            target_f = tf.constant(target_f, dtype=tf.int8)
            print("Replay8:" + str(int(round(time.time() * 1000)) - replay_start_t), end=",", flush=True)

            self.queue.enqueue((state_f, target_f))
            print("Replay9:" + str(int(round(time.time() * 1000)) - replay_start_t), end=",", flush=True)

        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

        print("ReplayE:" + str(int(round(time.time() * 1000)) - replay_start_t), flush=True)

    def replay_train(self):
        state_f, target_f = self.queue.dequeue()
        self.model.fit(state_f, target_f, epochs=1, verbose=0, steps_per_epoch=1)

    def generate_model(self):

        with tf.name_scope('training_part'):

            input_layer = keras.layers.Input(shape=self.state_size, batch_size=4, name='input_frames')

            normalized = keras.layers.Lambda(lambda x: x / 255.0)(input_layer)

            conv_layer_1 = keras.layers.Conv2D(16, 8, 8, activation="relu", data_format="channels_last")(normalized)
            conv_layer_2 = keras.layers.Conv2D(32, 4, 4, activation="relu")(conv_layer_1)

            conv_flattened = keras.layers.Flatten()(conv_layer_2)

            hidden = keras.layers.Dense(256, activation="relu")(conv_flattened)

            output = keras.layers.Dense(self.action_size)(hidden)

            model = keras.models.Model(inputs=input_layer, outputs=output)

            optimizer = keras.optimizers.RMSprop(lr=self.learning_rate, rho=self.rho, epsilon=self.epsilon)
        model.compile(optimizer, loss='mse')

        return model

    def load(self, name):
        self.model.load_weights(name)

    def save(self, name):
        self.model.save_weights(name)

def to_grayscale(img):
    return np.mean(img, axis=2).astype(np.uint8)


def downsample(img):
    return img[::2, ::2]


def preprocess(img):
    return to_grayscale(downsample(img))


def transform_reward(reward):
    return np.sign(reward)


def train(episodes):
    #env = gym.make('CartPole-v0')
    #env = gym.make('Breakout-v0')
    #env = gym.make('BeamRider-v0')
    env = gym.make('BreakoutDeterministic-v4')

    env._max_episode_steps = None
    state_size = preprocess(env.reset()).shape + (1,)
    action_size = env.action_space.n
    agent = DQN(state_size, action_size)

    done = False
    batch_size = 32

    #agent.load("./breakoutDeterministicV4.h5")
    try:
        for e in range(episodes):
            episode_start_t = int(round(time.time() * 1000))
            state = preprocess(env.reset())
            action = None

            for time_t in range(100000):

                frame_collector = list()
                #reward_collector = list()
                if time_t == 0:
                    frame_collector.append(state)
                else:
                    action = agent.act(state)
                    next_state, reward, done, _ = env.step(action)
                    reward = transform_reward(reward)
                    next_state = preprocess(next_state)
                    state.append(next_state)

                    agent.remember(tf.constant(np.array(state).reshape(5, 105, 80, 1), dtype=tf.int8),
                                   action, reward, done)
                    #agent.queue.enqueue((tf.constant(np.array(state).reshape(5, 1, 105, 80), dtype=tf.int8),
                    #                     action, reward, tf.constant(done, dtype=tf.int8)))

                    frame_collector.append(next_state)
                for frame in range(3):
                    next_state, reward, done, _ = env.step(0)   #TODO: Check if 0 is really "not moving anywhere"
                    frame_collector.append(preprocess(next_state))
                    #reward_collector.append(transform_reward(reward))

                state = frame_collector.copy()

                #env.render()

                if done:
                    # print the score and break out of the loop
                    print("episode: {}/{}, score: {}"
                          .format(e, episodes, time_t))
                    break
                if len(agent.memory) > batch_size:
                    agent.replay(batch_size)

            print("Episode took " + str(int(round(time.time() * 1000)) - episode_start_t))

        agent.save("./breakoutDeterministicV4.h5")
    except KeyboardInterrupt:
        agent.save("./breakoutDeterministicV4.h5")


train(50000)
