#!/usr/bin/python3
import rclpy
from rclpy.node import Node
import numpy as np
from std_msgs.msg import Float64MultiArray
from rclpy import qos
import time
import sys

class TrajectoryPublisher(Node):
    def __init__(self):
        super().__init__('trajectory_publisher')
        self.J1, self.J2, self.J3, self.J4 = None, None, None, None  # Initialize the joint values
        self.Jc1, self.Jc2, self.Jc3, self.Jc4 = 0.0, 0.0, 0.0, 0.0  # Current angles initialized to 0.0
        self.gripper, self.gripper_sub = 0.0, 0.0  # Initialize gripper joints
        self.new_input = False
        self.trajectory_in_progress = False

        self.create_subscription(Float64MultiArray, 'trajectory_inputs', self.input_callback, 10)
        self.create_subscription(Float64MultiArray, 'current_angle_topic', self.angle_callback, 10)
        self.publisher = self.create_publisher(Float64MultiArray, '/forward_position_controller/commands', qos_profile=qos.qos_profile_parameter_events)
        
        # Timer to check for new inputs and execute trajectory
        self.create_timer(0.1, self.check_and_execute_trajectory)

    def input_callback(self, msg):
        new_J1, new_J2, new_J3, new_J4 = msg.data[:4]
        # Initialize the first time or when a new input comes
        if (self.J1 is None) or (new_J1 != self.J1 or new_J2 != self.J2 or 
            new_J3 != self.J3 or new_J4 != self.J4):
            self.J1, self.J2, self.J3, self.J4 = new_J1, new_J2, new_J3, new_J4
            self.new_input = True

    def angle_callback(self, angle):
        self.Jc1, self.Jc2, self.Jc3, self.Jc4 = angle.data[:4]

    def check_and_execute_trajectory(self):
        if self.new_input and not self.trajectory_in_progress:
            self.ask_gripper_state()
            self.execute_trajectory()
            self.new_input = False

    def ask_gripper_state(self):
        while True:
            gripper_state = input("Do you want the gripper to be open or closed? (open/closed): ").lower()
            if gripper_state in ['open', 'closed']:
                if gripper_state == 'open':
                    self.gripper = self.gripper_sub = 0.019
                else:
                    self.gripper = self.gripper_sub = 0.007
                break
            else:
                print("Invalid input. Please enter 'open' or 'closed'.")

    def execute_trajectory(self):
        self.trajectory_in_progress = True
        joint = Float64MultiArray()
        joint.data = [0.0, 0.0, 0.0, 0.0, self.gripper, self.gripper_sub]
        
        TIME = 4  # Total time
        STEP_TIME = 0.05  # Time per step 50ms
        STEPS = int(TIME / STEP_TIME)  # Number of steps
        
        delta_J1 = (self.J1 - self.Jc1) / STEPS
        delta_J2 = (self.J2 - self.Jc2) / STEPS
        delta_J3 = (self.J3 - self.Jc3) / STEPS
        delta_J4 = (self.J4 - self.Jc4) / STEPS

        # Set initial gripper position
        print("---------SETTING GRIPPER------------")
        initial_joint = Float64MultiArray()
        initial_joint.data = [self.Jc1, self.Jc2, self.Jc3, self.Jc4, self.gripper, self.gripper_sub]
        self.publisher.publish(initial_joint)
        time.sleep(1)  # Wait for gripper to set

        print("---------STARTING TRAJECTORY------------")
        for i in range(STEPS):
            joint.data[0] = self.Jc1 + delta_J1 * (i + 1)
            joint.data[1] = self.Jc2 + delta_J2 * (i + 1)
            joint.data[2] = self.Jc3 + delta_J3 * (i + 1)
            joint.data[3] = self.Jc4 + delta_J4 * (i + 1)
            joint.data[4] = self.gripper
            joint.data[5] = self.gripper_sub
            self.publisher.publish(joint)
            time.sleep(STEP_TIME)

        # Update the current angles to the last position of the trajectory
        self.Jc1, self.Jc2, self.Jc3, self.Jc4 = self.J1, self.J2, self.J3, self.J4
        self.trajectory_in_progress = False

def main(args=None):
    rclpy.init(args=args)
    trajectory_publisher = TrajectoryPublisher()
    rclpy.spin(trajectory_publisher)
    trajectory_publisher.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()