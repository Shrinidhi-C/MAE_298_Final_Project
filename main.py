#!/usr/bin/python
import gym
import numpy as np
from time import sleep
from cartpole_util import CartPoleEnv
from system_dynamics import linearized_model_control, linearized_model_estimate
from system_estimate import KF_estimate, EKF_estimate
from linear_quadratic_regulator import lqr
import argparse
import os
import scipy.io as sio

def main():
    # env = gym.make('CartPole-v0').env
    noise = 1e-2
    env = CartPoleEnv(noise) 
    # set random seed
    env.seed(1)

    # # x, xdot, theta, thetadot
    x = env.reset()
    x_0 = np.copy(x).reshape(4,1) # this is observed without error

    # linearized model for lqr controller
    F = linearized_model_control(env)
    A, B, H = linearized_model_estimate(env)

    """ lqr controller """
    # control design parameters
    C = np.array([
        [1,  0, 0,  0,   0],
        [0,  0, 0,  0,   0],
        [0,  0, 1,  0,   0],
        [0,  0, 0,  0,   0],
        [0,  0, 0,  0,   1],
      ])
    c = np.array([0, 0, 0, 0, 0]).T
    T = 500
    # construct controller
    controller = lqr(T, F, C, c)

    # get parameters from command line
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--estimator', '-est', type=str, default='KF')
    parser.add_argument('--store', action='store_true')
    parser.add_argument('--v_x_est', '-xest',type=float, default=1e-1)
    parser.add_argument('--v_xdot_est', '-vest',type=float, default=1e-1)
    parser.add_argument('--v_theta_est', '-west',type=float, default=1e-1)
    parser.add_argument('--v_thetadot_est','-aest', type=float, default=1e-1)
    parser.add_argument('--frames', '-n', type=int, default=500)
    args = parser.parse_args()
    # print(args.estimator == "EKF")
    """ State estimator """
    # contruct state estimator
    # Q = np.zeros((4, 4)) # assume that there are no process error
    Q = np.array([[args.v_x_est, 0,               0,                0],
                  [0,            args.v_xdot_est, 0,                0],
                  [0,            0,               args.v_theta_est, 0],
                  [0,            0,               0,                args.v_thetadot_est]])

    # assume that R is known from datasheet of sensors which are accurate
    R = np.array([[2e-4, 0],
                  [0,    2e-4]])
    
    # assume accurate initial variance of states
    P_0 = np.copy(Q) 
    if args.estimator == "KF":
        estimator = KF_estimate(env, A, B, H, x_0, R, P_0, Q)
    elif args.estimator == "EKF":
        estimator = EKF_estimate(env, A, B, H, x_0, R, P_0, Q)

    frame = 0
    done = False

    X = []
    Est_X = []
    U = []
    TH = []
    Est_TH = []
    time = []
    # save for mat file
    mat_data = {}
    states_actual = []
    estimated_states = []
    inputs = []
    measurements = []
    states_actual.append(x)

    while 1:
        # calculate input value
        if frame is 0:
            ut = controller.input_design(x)
        else:
            ut = controller.input_design(estimate_x)
            # ut = controller.input_design(x)
        # ut = controller.input_design(x)
        # execute the force in simulated environment
        x = env.execute(ut)
        # get measurement of states
        y = env.sensor_measurement(x)

        estimate_x = estimator.state_estimate(ut[0,0], y)
        print("estimated x", estimate_x)
        print("actual x", x)
        
        # for plotting
        X.append(x[0])
        Est_X.append(estimate_x[0,0])
        TH.append(x[2])
        Est_TH.append(estimate_x[2,0])
        U.append(ut)

        # saving for mat file
        states_actual.append(x) 
        estimated_states.append(estimate_x)
        measurements.append(y)

        frame += 1
        time.append(frame*env.tau)
        env.render()
        # sleep(2)
        if frame > args.frames:
            break

    if args.store:
        if not(os.path.exists('data')):
            os.makedirs('data')
        mat_data["time"] = time
        mat_data["states_act"] = states_actual
        mat_data["state_meas"] = measurements
        mat_data["estimated_states"] = estimated_states
        mat_data["inputs"] = U
        logdir = './data/' + args.estimator + '_' + str(args.frames) + '.mat'
        sio.savemat(logdir, mat_data)


if __name__ == "__main__":
    main()
