import gym
from gym import error, spaces, utils
from gym.utils import seeding
#
import cityflow
import pandas as pd
import os
import numpy as np
import json
import math


class CityflowGymEnv(gym.Env):
    metadata = {'render.modes': ['human']}

    def __init__(self, config):
        self.eng = cityflow.Engine(config['cityflow_config_file'], thread_num=config['thread_num'])

        self.config = config
        self.num_step = config['num_step']
        self.state_size = config['state_size']
        self.lane_phase_info = config['lane_phase_info']  # "intersection_1_1"

        self.intersection_id = list(self.lane_phase_info.keys())[0]
        self.start_lane = self.lane_phase_info[self.intersection_id]['start_lane']
        self.phase_list = self.lane_phase_info[self.intersection_id]["phase"]
        self.phase_startLane_mapping = self.lane_phase_info[self.intersection_id]["phase_startLane_mapping"]

        self.current_phase = self.phase_list[0]
        self.current_phase_time = 0
        self.yellow_time = 5
        self.state_store_i = 0
        self.time_span = config['time_span']
        self.state_time_span = config['state_time_span']
        self.num_span_1 = 0
        self.num_span_2 = 0
        self.state_size_single = len(self.start_lane)

        self.phase_log = []

        self.count = np.zeros([8, self.time_span])
        self.accum_s = np.zeros([self.state_size_single, self.state_time_span])

    def step(self, next_phase):
        if self.current_phase == next_phase:
            self.current_phase_time += 1
        else:
            self.current_phase = next_phase
            self.current_phase_time = 1

        self.eng.set_tl_phase(self.intersection_id, self.current_phase)  # set phase of traffic light
        self.eng.next_step()
        self.phase_log.append(self.current_phase)

        return self.get_state(), self.get_reward()  # return next_state and reward

    def get_state(self):
        state = {}
        state['lane_vehicle_count'] = self.eng.get_lane_vehicle_count()  # {lane_id: lane_count, ...}
        state['start_lane_vehicle_count'] = {lane: self.eng.get_lane_vehicle_count()[lane] for lane in self.start_lane}
        state[
            'lane_waiting_vehicle_count'] = self.eng.get_lane_waiting_vehicle_count()  # {lane_id: lane_waiting_count, ...}
        state['lane_vehicles'] = self.eng.get_lane_vehicles()  # {lane_id: [vehicle1_id, vehicle2_id, ...], ...}
        state['vehicle_speed'] = self.eng.get_vehicle_speed()  # {vehicle_id: vehicle_speed, ...}
        state['vehicle_distance'] = self.eng.get_vehicle_distance()  # {vehicle_id: distance, ...}
        state['current_time'] = self.eng.get_current_time()
        state['current_phase'] = self.current_phase
        state['current_phase_time'] = self.current_phase_time

        return_state = np.array(list(state['start_lane_vehicle_count'].values()) + [state['current_phase']])
        return_state = np.reshape(return_state, [1, self.state_size])

        return return_state

    def get_reward(self):
        mystate = self.get_state()
        # reward function
        lane_vehicle_count = mystate[0][0:8]
        vehicle_velocity = self.eng.get_vehicle_speed()
        # reward = sum(list(vehicle_velocity.values())) / sum(lane_vehicle_count)
        reward = -max(lane_vehicle_count)
        # reward_sig = 2 / ((1 + math.exp(-1 * reward)))
        return reward

    def get_score(self):
        lane_waiting_vehicle_count = self.eng.get_lane_waiting_vehicle_count()
        reward = max(list(lane_waiting_vehicle_count.values()))
        metric = 1 / ((1 + math.exp(-1 * reward)) * self.config["num_step"])
        return reward

    def reset(self):
        self.eng.reset()

    def render(self, mode='human', close=False):
        ...
