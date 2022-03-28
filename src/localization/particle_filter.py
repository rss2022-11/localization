#!/usr/bin/env python2

import rospy
from sensor_model import SensorModel
from motion_model import MotionModel

from sensor_msgs.msg import LaserScan
from nav_msgs.msg import Odometry
from geometry_msgs.msg import PoseWithCovarianceStamped, Transform

import numpy as np
import quaternion
import math

class ParticleFilter:

    def __init__(self):
        ###
        # IMPORTANT: Below are parameters to tweak or to change between simulation/real robot
        
        # Starting value. Can raise this later
        self.MAX_PARTICLES = 200
        
        self.transform_topic = "/base_link_pf" # for sim
        # self.transform_topic = "/base_link" # for actual car 

        ###
        

        # Get parameters
        self.particle_filter_frame = \
                rospy.get_param("~particle_filter_frame")

        # Initialize publishers/subscribers
        #
        #  *Important Note #1:* It is critical for your particle
        #     filter to obtain the following topic names from the
        #     parameters for the autograder to work correctly. Note
        #     that while the Odometry message contains both a pose and
        #     a twist component, you will only be provided with the
        #     twist component, so you should rely only on that
        #     information, and *not* use the pose component.
        scan_topic = rospy.get_param("~scan_topic", "/scan")
        odom_topic = rospy.get_param("~odom_topic", "/odom")
        self.laser_sub = rospy.Subscriber(scan_topic, LaserScan,
                                          self.lidar_callback,
                                          queue_size=1)
        self.odom_sub = rospy.Subscriber(odom_topic, Odometry,
                                          self.odom_callback,
                                          queue_size=1)

        #  *Important Note #2:* You must respond to pose
        #     initialization requests sent to the /initialpose
        #     topic. You can test that this works properly using the
        #     "Pose Estimate" feature in RViz, which publishes to
        #     /initialpose.
        self.pose_sub = rospy.Subscriber("/initialpose", PoseWithCovarianceStamped,
                                          self.initialize_particles, queue_size=1)

        #  *Important Note #3:* You must publish your pose estimate to
        #     the following topic. In particular, you must use the
        #     pose field of the Odometry message. You do not need to
        #     provide the twist part of the Odometry message. The
        #     odometry you publish here should be with respect to the
        #     "/map" frame.
        self.odom_pub = rospy.Publisher("/pf/pose/odom", Odometry, queue_size=1)
        self.particle_pub = rospy.Publisher("/pf/pose/particles", PoseArray, queue_size=1)
        self.transform_pub = rospy.Publisher(self.transform_topic, Transform, queue_size=1)
        
        # Initialize the models
        self.motion_model = MotionModel()
        self.sensor_model = SensorModel()
        self.particles = np.zeros((200, 3))
        self.proposed_particles = np.zeros((200, 3))

        self.weights = np.ones(self.MAX_PARTICLES) / float(self.MAX_PARTICLES)

        # Implement the MCL algorithm
        # using the sensor model and the motion model
        
        # Make sure you include some way to initialize
        # your particles, ideally with some sort
        # of interactive interface in rviz
        #
        # Publish a transformation frame between the map
        # and the particle_filter_frame.
    
    def initialize_particles(self, pose):
        # get clicked point from rostopic /initialpose
        # generate spread of particles around clicked points
        self.particles[:, 0] = pose.position.x + np.random.normal(loc=0.0, scale=0.5, size=self.MAX_PARTICLES)
        self.particles[:, 1] = pose.position.y + np.random.normal(loc=0.0, scale=0.5, size=self.MAX_PARTICLES)
        self.particles[:, 2] = np.as_euler_angles(pose.orientation) + np.random.normal(loc=0.0, scale=0.4,
                                                                                      size=self.MAX_PARTICLES)

    def particle_to_pose(self, particle):
        pose = Pose()
        pose.position.x = particle[0]
        pose.position.y = particle[1]
        pose.orientation = np.from_euler_angles(particle[2])
        return pose

    def publish_particles(self):
        p = PoseArray()
        p.poses = np.map(self.particles, self.particle_to_pose)
        self.particle_pub.publish(p)

    def lidar_callback(self, msg):
        # get the laser scan data and then feed the data into the sensor model evaluate function
        observation = msg.ranges
        self.weights = self.sensor_model.evaluate(self.particles, observation)

    def odom_callback(self, msg):
        x = msg.twist.linear.x
        y = msg.twist.linear.y
        theta = msg.twist.angular.z
        odometry = [x, y, theta]
        self.proposed_particles = self.motion_model.evaluate(self.particles, odometry)
        # motion model is updated much more often than sesor_model, so we call MCL after updated motion model
        self.MCL()

    def MCL(self):
        # using weights and proposed particles, update particles
        self.particles = np.random.choice(self.proposed_particles, size=self.MAX_PARTICLES, p=self.weights)
        self.publish_transform()
        
    def publish_transform(self):
        transform = Transform()
        x_mean = np.mean(self.particles(:,0))
        y_mean = np.mean(self.particles(:,1))
        
        angular_mean = np.arctan2(np.sum(np.sin(self.particles(:,2))), np.sum(np.cos(self.particles(:,2))))
        transform.translation = [x_mean, y_mean, 0]
        transform.rotation = np.quaternion_from_euler([0, 0, angular_mean])
        self.transform_pub.publish()


if __name__ == "__main__":
    rospy.init_node("particle_filter")
    pf = ParticleFilter()
    rospy.spin()
