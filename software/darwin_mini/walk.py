from pypot.primitive import LoopPrimitive
from .trajectory import FootstepTrajectory
from .ik import darwin_ik
from numpy import rad2deg


class WalkStraight(LoopPrimitive):
    def __init__(self, robot, distance, step_duration, frequency=50):
        LoopPrimitive.__init__(self, robot, frequency)

        self.distance_left = distance
        self.step_duration = step_duration

    def setup(self):
        self.step_length = 0.1
        self.step_height = 0.01
        self.pelvis_height = 0.098
        self.swing_side = 'r'
        self.x_stable = 0.
        self.x_swing_start = 0.
        self.current_step = 0
        self.current_step_length = self.get_current_step_length()
        self.current_trajectory = self.create_footstep_trajectory(
            self.current_step_length, self.x_stable, self.x_swing_start, self.swing_side)
        self.motors = dict([(m.name, self.get_mockup_motor(m)) for m in self.robot.motors])
        print('\n*** Start step {} ***'.format(self.current_step + 1))

    def update(self):
        t = self.elapsed_time
        # print(t)
        step = t // self.step_duration
        t = t % self.step_duration
        done = False
        if step > self.current_step:
            self.current_step = step
            done = self.start_next_step()
        if not done:
            pos = self.current_trajectory(t)
            q = darwin_ik(pos)
            self.goto_position(q)

    def get_current_step_length(self):
        next_step_max_length = self.step_length if self.current_step > 0 else 0.5 * self.step_length
        if 2 * self.distance_left > next_step_max_length:
            current_step_length = next_step_max_length
        else:
            current_step_length = 2 * self.distance_left
        return current_step_length

    def create_footstep_trajectory(self, step_length, x_stable, x_swing_start, swing_side):
        return FootstepTrajectory(step_length, self.step_height, x_stable, x_swing_start,
                                  self.pelvis_height, swing_side, self.step_duration)

    def start_next_step(self):
        self.swing_side = 'l' if self.swing_side == 'r' else 'r'
        next_swing_start = self.x_stable
        self.x_stable = self.x_swing_start + self.current_step_length
        self.x_swing_start = next_swing_start
        # the pelvis only moves half of the footstep length
        self.distance_left = max(0, self.distance_left - 0.5 * self.current_step_length)
        if self.distance_left < 1e-6:
            # We have arrived.  Join feet.
            self.current_step_length = self.x_stable - self.x_swing_start
            if self.current_step_length < 1e-6:
                print('Done!')
                self.stop()
                return True
        else:
            self.current_step_length = self.get_current_step_length()
            self.current_trajectory = self.create_footstep_trajectory(
                self.current_step_length, self.x_stable, self.x_swing_start, self.swing_side)
        print('\n*** Start step {} ***'.format(self.current_step + 1))
        return False

    def goto_position(self, qs):
        for name, q in qs.items():
            m = self.motors[name]
            m.goal_position = rad2deg(q)
