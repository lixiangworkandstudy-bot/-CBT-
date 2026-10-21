"""Bounded local bridge. No ROS imports or device writes in the default dry-run."""
import argparse
import json
import math
import os
import threading
import time
from pathlib import Path
from urllib.parse import urlparse, urlencode
from urllib.request import urlopen


class Lease:
    """Expire commands independently of HTTP; only one predeclared stationary cue."""
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.until = 0
        self.angular = 0.0
        self.lock = threading.Lock()

    def update(self, message):
        with self.lock:
            self.angular = 0.0; self.until = 0
            if message.get("cue") != "celebrate" or message.get("state") != "completed":
                return
            lease = message.get("lease_ms", 0)
            angular = message.get("angular_z", 0)
            if (isinstance(lease, bool) or isinstance(angular, bool) or
                not isinstance(lease, (int, float)) or not isinstance(angular, (int, float)) or
                not math.isfinite(lease) or not math.isfinite(angular) or
                not 0 < lease <= 150 or abs(angular) > .12 or message.get("linear_x") != 0):
                return
            self.until = self.clock() + lease/1000
            self.angular = float(angular)

    def velocity(self):
        with self.lock:
            return (0.0, self.angular) if self.clock() < self.until else (0.0, 0.0)


def parser():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--session', required=True, help='session ID from browser URL')
    p.add_argument('--mode', choices=['turtlesim','vbot'], default='turtlesim')
    p.add_argument('--base-url', default='http://127.0.0.1:8787')
    p.add_argument('--execute', action='store_true', help='explicitly publish ROS messages')
    p.add_argument('--confirm-motion', action='store_true', help='adult confirms cleared test area and physical E-stop readiness')
    p.add_argument('--duration', type=float, default=60, help='bounded run, 1 to 120 seconds')
    return p


def validate(a):
    if not math.isfinite(a.duration) or not 1 <= a.duration <= 120:
        raise ValueError('duration must be finite and within [1,120] seconds')
    u=urlparse(a.base_url)
    if u.scheme != 'http' or u.hostname not in ('127.0.0.1','localhost') or u.path not in ('','/') or u.username or u.query or u.fragment:
        raise ValueError('Only a local loopback HTTP app is supported')
    if a.execute and a.mode == 'vbot':
        if not a.confirm_motion: raise ValueError('VBOT requires --confirm-motion')
        if os.environ.get('ROS_DOMAIN_ID') != '178': raise ValueError('VBOT requires ROS_DOMAIN_ID=178')
        if os.environ.get('ROS_LOCALHOST_ONLY') != '1': raise ValueError('VBOT requires ROS_LOCALHOST_ONLY=1')
        if os.environ.get('RMW_IMPLEMENTATION') != 'rmw_fastrtps_cpp': raise ValueError('VBOT board bridge requires rmw_fastrtps_cpp; verify official runtime')
        if not Path('/opt/vita/aorta/ros/local_setup.bash').exists():
            raise ValueError('VBOT execution is restricted to the documented board runtime')


def main():
    p=parser(); a=p.parse_args()
    try: validate(a)
    except ValueError as e: p.error(str(e))
    mode=a.mode if a.execute else 'dry-run'
    url=a.base_url.rstrip('/')+'/api/robot?'+urlencode({'id':a.session,'mode':mode})
    lease=Lease(); stop=threading.Event()
    def receive():
        while not stop.is_set():
            try:
                with urlopen(url, timeout=.1) as r:
                    msg=json.load(r)
                lease.update(msg)
            except Exception:
                lease.update({})
            stop.wait(.04)
    thread=threading.Thread(target=receive,daemon=True);thread.start()
    node=pub=None
    started=time.monotonic()
    try:
        if a.execute:
            import rclpy
            from rclpy.node import Node
            from geometry_msgs.msg import Twist
            rclpy.init();node=Node('manman_companion_bridge')
            topic='/turtle1/cmd_vel' if a.mode=='turtlesim' else '/vel_cmd'
            pub=node.create_publisher(Twist,topic,10)
            def publish():
                vx,wz=lease.velocity();t=Twist();t.linear.x=vx;t.angular.z=wz;pub.publish(t)
            node.create_timer(.05,publish)
            print(json.dumps({'mode':a.mode,'topic':topic,'rate_hz':20,'duration_s':a.duration}),flush=True)
            while time.monotonic()-started<a.duration:
                rclpy.spin_once(node,timeout_sec=.05)
        else:
            print('DRY RUN: no ROS imports, no device writes',flush=True)
            while time.monotonic()-started<a.duration:
                print(json.dumps({'mode':'dry-run','velocity':lease.velocity()}),flush=True)
                stop.wait(.25)
    except KeyboardInterrupt:
        pass
    finally:
        stop.set();lease.update({});thread.join(timeout=.5)
        if node:
            # Zero commands are best-effort; cannot replace hardware E-stop.
            try:
                for _ in range(5):
                    pub.publish(Twist());time.sleep(.02)
            finally:
                node.destroy_node();rclpy.shutdown()
        print('bridge stopped; zero command requested',flush=True)


if __name__=='__main__': main()
