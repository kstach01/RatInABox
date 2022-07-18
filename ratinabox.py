import scipy
from scipy import stats
import numpy as np
import matplotlib
from matplotlib import pyplot as plt

verbose = False

"""ENVIRONMENT"""


class Environment:
    """Environment class: defines the Environment in which the Agent lives. 
    This class needs no other classes to initialise it. It exists independently of any Agents or Neurons. 

    A default parameters dictionary (with descriptions) can be found in __init__()

    List of functions...
        ...that you might use:
            • add_wall()
            • plot_environment()
        ...that you probably won't directly use:
            • sample_positions()
            • discretise_environment()
            • get_vectors_between___accounting_for_environment()
            • get_distances_between___accounting_for_environment()
            • check_if_position_is_in_environment()
            • check_wall_collisions()
            • vectors_from_walls()
            • apply_boundary_conditions()
    """

    def __init__(self, params={}):
        """Initialise Environment, takes as input a parameter dictionary. Any values not provided by the params dictionary are taken from a default dictionary.

        Args:
            params (dict, optional). Defaults to {}, which uses default_params defined below.
        """
        default_params = {
            "dimensionality": "2D",  # 1D or 2D environment
            "boundary_conditions": "solid",  # solid vs periodic
            "scale": 1,  # scale of environment (in metres)
            "aspect": 1,  # x/y aspect ratio for the (rectangular) 2D environment
            "dx": 0.01,  # discretises the environment (for plotting purposes only)
        }

        default_params.update(params)
        self.params = default_params
        update_class_params(self, self.params)

        if self.dimensionality == "1D":
            self.extent = np.array([0, self.scale])
            self.centre = np.array([self.scale / 2, self.scale / 2])

        self.walls = np.array([])
        if self.dimensionality == "2D":
            if self.boundary_conditions != "periodic":
                self.walls = np.array(
                    [
                        [[0, 0], [0, self.scale]],
                        [[0, self.scale], [self.aspect * self.scale, self.scale]],
                        [
                            [self.aspect * self.scale, self.scale],
                            [self.aspect * self.scale, 0],
                        ],
                        [[self.aspect * self.scale, 0], [0, 0]],
                    ]
                )
            self.centre = np.array([self.aspect * self.scale / 2, self.scale / 2])
            self.extent = np.array([0, self.aspect * self.scale, 0, self.scale])
        self.params["extent"] = self.extent
        self.params["centre"] = self.centre

        # save some prediscretised coords (useful for plotting rate maps later)
        self.discrete_coords = self.discretise_environment(dx=self.dx)
        self.flattened_discrete_coords = self.discrete_coords.reshape(
            -1, self.discrete_coords.shape[-1]
        )

        if verbose is True:
            print(
                f"\nAn Environment has been initialised with parameters: {self.params}. Use Env.add_wall() to add a wall into the Environment. Plot Environment using Env.plot_environment()."
            )

        return

    def add_wall(self, wall):
        """Add a wall to the (2D) environment.
        Extends self.walls array to include one new wall. 
        Args:
            wall (np.array): 2x2 array [[x1,y1],[x2,y2]]
        """
        assert self.dimensionality == "2D", "can only add walls into a 2D environment"
        wall = np.expand_dims(np.array(wall), axis=0)
        if len(self.walls) == 0:
            self.walls = wall
        else:
            self.walls = np.concatenate((self.walls, wall), axis=0)
        return

    def plot_environment(self, fig=None, ax=None, height=1):
        """Plots the environment, dark grey lines show the walls
        Args:        
            fig,ax: the fig and ax to plot on (can be None)
            height: if 1D, how many line plots will be stacked (5.5mm per line)
        Returns:
            fig, ax: the environment figures, can be used for further downstream plotting.
        """

        if self.dimensionality == "1D":
            extent = self.extent
            fig, ax = plt.subplots(
                figsize=(3 * (extent[1] - extent[0]), height * (5.5 / 25))
            )
            ax.set_xlim(left=extent[0], right=extent[1])
            ax.spines["left"].set_color("none")
            ax.spines["right"].set_color("none")
            ax.spines["bottom"].set_position("zero")
            ax.spines["top"].set_color("none")
            ax.set_yticks([])
            ax.set_xticks([extent[0], extent[1]])
            ax.set_xlabel("Position / m")

        if self.dimensionality == "2D":
            extent, walls = self.extent, self.walls
            if fig is None and ax is None:
                fig, ax = plt.subplots(
                    figsize=(3 * (extent[1] - extent[0]), 3 * (extent[3] - extent[2]))
                )
            background = matplotlib.patches.Rectangle(
                (extent[0], extent[2]),
                extent[1],
                extent[3],
                facecolor="lightgrey",
                zorder=-1,
            )
            ax.add_patch(background)
            for wall in walls:
                ax.plot(
                    [wall[0][0], wall[1][0]],
                    [wall[0][1], wall[1][1]],
                    color="grey",
                    linewidth=4,
                )
            ax.set_aspect("equal")
            ax.grid(False)
            ax.axis("off")
            ax.set_xlim(left=extent[0] - 0.03, right=extent[1] + 0.03)
            ax.set_ylim(bottom=extent[2] - 0.03, top=extent[3] + 0.03)
        return fig, ax

    def sample_positions(self, n=10, method="uniform_jitter"):
        """Scatters 'n' locations across the environment which can act as, for example, the centres of gaussian place fields, or as a random starting position. 
        If method == "uniform" an evenly spaced grid of locations is returned.  If method == "uniform_jitter" these locations are jittered slightly (i.e. random but span the space). Note; if n doesn't uniformly divide the size (i.e. n is not a square number in a square environment) then the largest number that can be scattered uniformly are found, the remaining are randomly placed. 
        Args:
            n (int): number of features 
            method: "uniform", "uniform_jittered" or "random" for how points are distributed
            true_random: if True, just randomly scatters point
        Returns:
            array: (n x dimensionality) of positions 
        """
        if self.dimensionality == "1D":
            if method == "random":
                positions = np.random.uniform(
                    self.extent[0], self.extent[1], size=(n, 1)
                )
            elif method[:7] == "uniform":
                dx = self.scale / n
                positions = np.arange(0 + dx / 2, self.scale, dx).reshape(-1, 1)
                if method[7:] == "_jitter":
                    positions += np.random.uniform(
                        -0.45 * dx, 0.45 * dx, positions.shape
                    )
            return positions

        elif self.dimensionality == "2D":
            if method == "random":
                positions = np.random.uniform(size=(n, 2))
                positions[:, 0] *= self.extent[1] - self.extent[0]
                positions[:, 1] *= self.extent[3] - self.extent[2]
            elif method[:7] == "uniform":
                ex = self.extent
                area = (ex[1] - ex[0]) * (ex[3] - ex[2])
                delta = np.sqrt(area / n)
                x = np.arange(ex[0] + delta / 2, ex[1] - delta / 2 + 1e-6, delta)
                y = np.arange(ex[2] + delta / 2, ex[3] - delta / 2 + 1e-6, delta)
                positions = np.array(np.meshgrid(x, y)).reshape(2, -1).T
                n_uniformly_distributed = positions.shape[0]
                if method[7:] == "_jitter":
                    positions += np.random.uniform(
                        -0.45 * delta, 0.45 * delta, positions.shape
                    )
                n_remaining = n - n_uniformly_distributed
                if n_remaining > 0:
                    positions_remaining = self.sample_positions(
                        n=n_remaining, method="random"
                    )
                    positions = np.vstack((positions, positions_remaining))
            return positions

    def discretise_environment(self, dx=None):
        """Discretises the environment, for plotting purposes.
        Returns an array of positions spanning the environment 
        Important: this discretisation is not used for geometry or firing rate calculations which are precise and fundamentally continuous. Its typically used if you want to, say, display the receptive field of a neuron so you want to calculate its firing rate at all points across the environment and plot those. 
        Args:
            dx (float): discretisation distance
        Returns:
            array: an (Ny x Mx x 2) array of position coordinates or (Nx x 1) for 1D
        """  # returns a 2D array of locations discretised by dx
        if dx is None:
            dx = self.dx
        [minx, maxx] = list(self.extent[:2])
        self.x_array = np.arange(minx + dx / 2, maxx, dx)
        discrete_coords = self.x_array.reshape(-1, 1)
        if self.dimensionality == "2D":
            [miny, maxy] = list(self.extent[2:])
            self.y_array = np.arange(miny + dx / 2, maxy, dx)[::-1]
            x_mesh, y_mesh = np.meshgrid(self.x_array, self.y_array)
            coordinate_mesh = np.array([x_mesh, y_mesh])
            discrete_coords = np.swapaxes(np.swapaxes(coordinate_mesh, 0, 1), 1, 2)
        return discrete_coords

    def get_vectors_between___accounting_for_environment(
        self, pos1=None, pos2=None, line_segments=None
    ):
        """Takes two position arrays and returns an array of pair-wise vectors from pos1's to pos2's, taking into account boundary conditions. Unlike the global function "get_vectors_between()' (which this calls) this additionally accounts for environment boundary conditions such that if two positions fall on either sides of the boundary AND boundary cons are periodic then the returned shortest-vector actually goes around the loop, not across the environment)... 
            pos1 (array): N x dimensionality array of poisitions
            pos2 (array): M x dimensionality array of positions
            line_segments: if you have already calculated line segments from pos1 to pos2 pass this here for quicker evaluation
        Returns:
            N x M x dimensionality array of pairwise vectors 
        """
        vectors = get_vectors_between(pos1=pos1, pos2=pos2, line_segments=line_segments)
        if self.boundary_conditions == "periodic":
            flip = np.abs(vectors) > (self.scale / 2)
            vectors[flip] = -np.sign(vectors[flip]) * (
                self.scale - np.abs(vectors[flip])
            )
        return vectors

    def get_distances_between___accounting_for_environment(
        self, pos1, pos2, wall_geometry="euclidean"
    ):
        """Takes two position arrays and returns the array of pair-wise distances between points, taking into account walls and boundary conditions. Unlike the global function get_distances_between() (which this one, at times, calls) this additionally accounts for the boundaries AND walls in the environment. 
        
        For example, geodesic geometry estimates distance by shortest walk...line_of_sight geometry distance is euclidean but if there is a wall in between two positions (i.e. no line of sight) then the returned distance is "very high"...if boundary conditions are periodic distance is via the shortest possible route, which may or may not go around the back. euclidean geometry essentially ignores walls when calculating distances between two points.
        Allowed geometries, typically passed from the neurons class, are "euclidean", "geodesic" or "line_of_sight"
        Args:
            pos1 (array): N x dimensionality array of poisitions
            pos2 (array): M x dimensionality array of positions
            wall_geometry: how the distance calculation handles walls in the env (can be "euclidean", "line_of_sight" or "geodesic")
        Returns:
            N x M array of pairwise distances 
        """

        line_segments = get_line_segments_between(pos1=pos1, pos2=pos2)
        vectors = self.get_vectors_between___accounting_for_environment(
            pos1=None, pos2=None, line_segments=line_segments
        )

        # shorthand
        walls = self.walls
        dimensionality = self.dimensionality
        boundary_conditions = self.boundary_conditions

        if dimensionality == "1D":
            distances = get_distances_between(vectors=vectors)

        if dimensionality == "2D":
            if wall_geometry == "euclidean":
                distances = get_distances_between(vectors=vectors)

            if wall_geometry == "line_of_sight":
                assert (
                    boundary_conditions == "solid"
                ), "line of sight geometry not available for periodic boundary conditions"
                # if a wall obstructs line-of-sight between two positions, distance is set to 1000
                internal_walls = walls[
                    4:
                ]  # only the internal walls (not room walls) are worth checking
                line_segments_ = line_segments.reshape(-1, *line_segments.shape[-2:])
                wall_obstructs_view_of_cell = vector_intercepts(
                    line_segments_, internal_walls, return_collisions=True
                )
                wall_obstructs_view_of_cell = wall_obstructs_view_of_cell.sum(
                    axis=-1
                )  # sum over walls axis as we don't care which wall it collided with
                wall_obstructs_view_of_cell = wall_obstructs_view_of_cell != 0
                wall_obstructs_view_of_cell = wall_obstructs_view_of_cell.reshape(
                    line_segments.shape[:2]
                )
                distances = get_distances_between(vectors=vectors)
                distances[wall_obstructs_view_of_cell == True] = 1000

            if wall_geometry == "geodesic":
                assert (
                    boundary_conditions == "solid"
                ), "line of sight geometry not available for periodic boundary conditions"
                assert (
                    len(walls) <= 5
                ), "unfortunately geodesic geomtry is only defined in closed rooms with one additional wall (efficient geometry calculations withh more than 1 wall are super hard I have discovered!) "
                distances = get_distances_between(vectors=vectors)
                if len(walls) == 4:
                    pass
                else:
                    wall = walls[4]
                    via_wall_distances = []
                    for part_of_wall in wall:
                        wall_edge = np.expand_dims(part_of_wall, axis=0)
                        if self.check_if_position_is_in_environment(part_of_wall):
                            distances_via_part_of_wall = get_distances_between(
                                pos1, wall_edge
                            ) + get_distances_between(wall_edge, pos2)
                            via_wall_distances.append(distances_via_part_of_wall)
                    via_wall_distances = np.array(via_wall_distances)
                    line_segments_ = line_segments.reshape(
                        -1, *line_segments.shape[-2:]
                    )
                    wall_obstructs_view_of_cell = vector_intercepts(
                        line_segments_,
                        np.expand_dims(wall, axis=0),
                        return_collisions=True,
                    )
                    wall_obstructs_view_of_cell = wall_obstructs_view_of_cell.reshape(
                        line_segments.shape[:2]
                    )
                    flattened_distances = distances.reshape(-1)
                    flattened_wall_obstructs_view_of_cell = wall_obstructs_view_of_cell.reshape(
                        -1
                    )
                    flattened_distances[
                        flattened_wall_obstructs_view_of_cell
                    ] = np.amin(via_wall_distances, axis=0).reshape(-1)[
                        flattened_wall_obstructs_view_of_cell
                    ]
                    distances = flattened_distances.reshape(distances.shape)

        return distances

    def check_if_position_is_in_environment(self, pos):
        """Returns True if pos is INside the environment
        Points EXACTLY on the edge of the environment are NOT classed as being inside the environment. This is relevant in geodesic geometry calculations since routes past the edge of a wall connection with the edge of an environmnet are not valid routes.
        Args:
            pos (array): np.array([x,y])
        Returns:
            bool: True if pos is inside environment.
        """
        pos = np.array(pos).reshape(-1)
        if self.dimensionality == "2D":
            if (
                (pos[0] > self.extent[0])
                and (pos[0] < self.extent[1])
                and (pos[1] > self.extent[2])
                and (pos[1] < self.extent[3])
            ):
                return True
            else:
                return False
        elif self.dimensionality == "1D":
            if (pos[0] > self.extent[0]) and (pos[0] < self.extent[1]):
                return True
            else:
                return False

    def check_wall_collisions(self, proposed_step):
        """Given proposed step [current_pos, next_pos] it returns two lists 
        1. a list of all the walls in the environment #shape=(N_walls,2,2)
        2. a boolean list of whether the step directly crosses (collides with) any of these walls  #shape=(N_walls,)
        Args:
            proposed_step (array): The proposed step. np.array( [ [x_current, y_current] , [x_next, y_next] ] )
        Returns:
            tuple: (1,2)
        """
        if self.dimensionality == "1D":
            # no walls in 1D to collide with
            return (None, None)
        elif self.dimensionality == "2D":
            if (self.walls is None) or (len(self.walls) == 0):
                # no walls to collide with
                return (None, None)
            elif self.walls is not None:
                walls = self.walls
                wall_collisions = vector_intercepts(
                    walls, proposed_step, return_collisions=True
                ).reshape(-1)
                return (walls, wall_collisions)

    def vectors_from_walls(self, pos):
        """Given a position, pos, it returns a list of the vectors of shortest distance from all the walls to current_pos #shape=(N_walls,2)
        Args:
            proposed_step (array): The position np.array([x,y])
        Returns:
            vector array: np.array(shape=(N_walls,2))
        """
        walls_to_pos_vectors = shortest_vectors_from_points_to_lines(pos, self.walls)[0]
        return walls_to_pos_vectors

    def apply_boundary_conditions(self, pos):
        """Performs a boundary condition check. If pos is OUTside the environment and the boundary conditions are solid then a different position, safely located 1cm within the environmnt, is returne3d. If pos is OUTside the environment but boundary conditions are periodic its position is looped to the other side of the environment appropriately.
        Args:
            pos (np.array): 1 or 2 dimensional position
        returns new_pos
        """
        if self.check_if_position_is_in_environment(pos) is False:
            if self.dimensionality == "1D":
                if self.boundary_conditions == "periodic":
                    pos = pos % self.extent[1]
                if self.boundary_conditions == "solid":
                    pos = min(max(pos, self.extent[0] + 0.01), self.extent[1] - 0.01)
                    pos = np.reshape(pos, (-1))
            if self.dimensionality == "2D":
                if self.boundary_conditions == "periodic":
                    pos[0] = pos[0] % self.extent[1]
                    pos[1] = pos[1] % self.extent[3]
                if self.boundary_conditions == "solid":
                    # in theory this wont be used as wall bouncing catches it earlier on
                    pos[0] = min(
                        max(pos[0], self.extent[0] + 0.01), self.extent[1] - 0.01
                    )
                    pos[1] = min(
                        max(pos[1], self.extent[2] + 0.01), self.extent[3] - 0.01
                    )
        return pos


"""AGENT"""


class Agent:
    """This class defines an Agent which moves around the Environment. Specifically this class handles the movement policy and communicates with the Environment class to ensure the Agent's movement obeys boundaries and walls etc. 
    
    Must be initialised with the Environment in which it lives and a params dictionary containing other specifics about the  with a params dictionary which must contain key parameters required for the motion model. The most important function "update(dt)" updates the positio/velocity of the agent along in time by dt.

    A default parameters dictionary (with descriptions) can be fount in __init__()

    List of functions:
        • update()
        • import_trajectory()
        • plot_trajectory()
        • animate_trajectory()
        • plot_position_heatmap()
        • plot_histogram_of_speeds()
        • plot_histogram_of_rotational_velocities()
    """

    def __init__(self, Environment, params={}):
        """Initialise Agent, takes as input a parameter dictionary. Any values not provided by the params dictionary are taken from a default dictionary below.

        Args:
            params (dict, optional). Defaults to {}.
        """
        default_params = {
            "dt": 0.01,
            # Speed params (leave empty if you are importing trajectory data)
            # These defaults are fit to match data from Sargolini et al. (2016)
            "speed_coherence_time": 0.7,  # time over which speed decoheres
            "speed_mean": 0.08,  # mean of speed
            "speed_std": 0.08,  # std of speed (meaningless in 2D where speed ~rayleigh)
            "rotational_velocity_coherence_time": 0.08,  # time over which speed decoheres
            "rotational_velocity_std": 120 * (np.pi / 180),  # std of rotational speed
            # wall following parameter
            "thigmotaxis": 0.5,  # tendency for agents to linger near walls [0 = not at all, 1 = max]
        }
        self.Environment = Environment
        default_params.update(params)
        self.params = default_params
        update_class_params(self, self.params)

        # initialise history dataframes
        self.history = {}
        self.history["t"] = []
        self.history["pos"] = []
        self.history["vel"] = []
        self.history["rot_vel"] = []

        # time and runID
        self.t = 0
        self.distance_travelled = 0
        self.average_measured_speed = max(self.speed_mean, self.speed_std)
        self.use_imported_trajectory = False

        # motion model stufff
        self.walls_repel = True  # over ride to switch of wall repulsion
        self.wall_repel_distance = 0.10

        # initialise starting positions and velocity
        if self.Environment.dimensionality == "2D":
            self.pos = self.Environment.sample_positions(n=1, method="random")[0]
            direction = np.random.uniform(0, 2 * np.pi)
            self.velocity = self.speed_std * np.array(
                [np.cos(direction), np.sin(direction)]
            )
            self.rotational_velocity = 0

        if self.Environment.dimensionality == "1D":
            self.pos = self.Environment.sample_positions(n=1, method="random")[0]
            self.velocity = np.array([self.speed_mean])

        if verbose is True:
            print(
                f"\nAn Agent has been successfully initialised with the following parameters {self.params}. Use Ag.update() to move the Agent. Positions and velocities are saved into the Agent.history dictionary. Import external trajectory data using Ag.import_trajectory(). Plot trajectory using Ag.plot_trajectory(). Other plotting functions are available."
            )
        return

    def update(self, dt=None, drift_velocity=None, drift_to_random_strength_ratio=1):
        """Movement policy update. 
            In principle this does a very simple thing: 
            • updates time by dt
            • updates velocity (speed and direction) according to a movement policy
            • updates position along the velocity direction 
            In reality it's a complex function as the policy requires checking for immediate or upcoming collisions with all walls at each step as well as handling boundary conditions.
            Specifically the full loop looks like this:
            1) Update time by dt
            2) Update velocity for the next time step. In 2D this is done by varying the agents heading direction and speed according to ornstein-uhlenbeck processes. In 1D, simply the velocity is varied according to ornstein-uhlenbeck. This includes, if turned on, being repelled by the walls.
            3) Propose a new position (x_new =? x_old + velocity.dt)
            3.1) Check if this step collides with any walls (and act accordingly)
            3.2) Check you distance and direction from walls and be repelled by them is necessary
            4) Check position is still within maze and handle boundary conditions appropriately 
            6) Store new position and time in history data frame
        """
        if dt == None:
            dt = self.dt
        self.dt = dt
        self.t += dt

        if self.use_imported_trajectory == False:  # use random motion model
            if self.Environment.dimensionality == "2D":
                # UPDATE VELOCITY there are a number of contributing factors
                # 1 Stochastically update the direction
                direction = get_angle(self.velocity)
                self.rotational_velocity += ornstein_uhlenbeck(
                    dt=dt,
                    x=self.rotational_velocity,
                    drift=0,
                    noise_scale=self.rotational_velocity_std,
                    coherence_time=self.rotational_velocity_coherence_time,
                )
                dtheta = self.rotational_velocity * dt
                self.velocity = rotate(self.velocity, dtheta)

                # 2 Stochastically update the speed
                speed = np.linalg.norm(self.velocity)
                normal_variable = rayleigh_to_normal(speed, sigma=self.speed_mean)
                new_normal_variable = normal_variable + ornstein_uhlenbeck(
                    dt=dt,
                    x=normal_variable,
                    drift=0,
                    noise_scale=1,
                    coherence_time=self.speed_coherence_time,
                )
                speed_new = normal_to_rayleigh(
                    new_normal_variable, sigma=self.speed_mean
                )
                self.velocity = (speed_new / speed) * self.velocity

                # Deterministically drift velocity towards the drift_velocity which has been passed into the update function
                if drift_velocity is not None:
                    self.velocity += ornstein_uhlenbeck(
                        dt=dt,
                        x=self.velocity,
                        drift=drift_velocity,
                        noise_scale=0,
                        coherence_time=self.speed_coherence_time
                        / drift_to_random_strength_ratio,
                    )  # <--- this controls how "powerful" this signal is

                # Deterministically drift the velocity away from any nearby walls
                if (self.walls_repel == True) and (len(self.Environment.walls > 0)):
                    vectors_from_walls = self.Environment.vectors_from_walls(
                        self.pos
                    )  # shape=(N_walls,2)
                    if len(self.Environment.walls) > 0:
                        distance_to_walls = np.linalg.norm(vectors_from_walls, axis=-1)
                        normalised_vectors_from_walls = (
                            vectors_from_walls
                            / np.expand_dims(distance_to_walls, axis=-1)
                        )
                        x, d, v = (
                            distance_to_walls,
                            self.wall_repel_distance,
                            self.speed_mean,
                        )

                        # Wall repulsion and wall following works as follows. When an agent is near the wall, the acceleration and velocity of a hypothetical spring mass tied to a line self.wall_repel_distance away from the wall is calculated. The spring constant is calibrateed so taht if if starts with the Agent.speed_mean it will ~~just~~ not hit the wall. Now, either the acceleration can be used to update the velocity and guide the agent away from the wall OR the counteracting velocity can be used to update the agents position and shift it away from the wall. Both result in repulsive motion away from the wall. The difference is that the latter (and not the former) does not update the agents velocity vector to reflect this, in which case it continues to walk (unsuccessfully) in the same direction barging into the wall and 'following' it. The thigmotaxis parameter allows us to divvy up which of these two dominate. If thigmotaxis is low the acceleration-gives-velocity-update is most dominant and the agent will not linger near the wall. If thigmotaxis is high the velocity-gives-position-update is most dominant and the agent will linger near the wall.

                        # Spring acceletation model: in this case this is done by applying an acceleration whenever the agent is near to a wall. this acceleration matches that of a spring with spring constant 3x that of a spring which would, if the agent arrived head on at v = self.speed_mean, turn around exactly at the wall. this is solved by letting d2x/dt2 = -k.x where k = v**2/d**2 (v=seld.speed_mean, d = self.wall_repel_distance)
                        spring_constant = v ** 2 / d ** 2
                        wall_accelerations = np.piecewise(
                            x=x,
                            condlist=[(x <= d), (x > d),],
                            funclist=[
                                lambda x: spring_constant * (d - x),
                                lambda x: 0,
                            ],
                        )
                        wall_acceleration_vecs = (
                            np.expand_dims(wall_accelerations, axis=-1)
                            * normalised_vectors_from_walls
                        )
                        wall_acceleration = wall_acceleration_vecs.sum(axis=0)
                        dv = wall_acceleration * dt
                        self.velocity += 3 * ((1 - self.thigmotaxis) ** 2) * dv

                        # Conveyor belt drift model. Instead of a spring model this is like a converyor belt model. when < wall_repel_distance from the wall the agents position is updated as though it were on a conveyor belt which moves at the speed of spring mass attached to the wall with starting velocity 5*self.speed_mean. This has a similar effect effect  as the spring model above in that the agent moves away from the wall BUT, crucially the update is made directly to the agents positin, not it's speed, so the next time step will not reflect this update. As a result the agent which is walking into the wall will continue to barge hopelessly into the wall causing it the "hug" close to the wall.
                        wall_speeds = np.piecewise(
                            x=x,
                            condlist=[(x <= d), (x > d),],
                            funclist=[
                                lambda x: v * (1 - np.sqrt(1 - (d - x) ** 2 / d ** 2)),
                                lambda x: 0,
                            ],
                        )
                        wall_speed_vecs = (
                            np.expand_dims(wall_speeds, axis=-1)
                            * normalised_vectors_from_walls
                        )
                        wall_speed = wall_speed_vecs.sum(axis=0)
                        dx = wall_speed * dt
                        self.pos += 6 * (self.thigmotaxis ** 2) * dx

                # proposed position update
                proposed_new_pos = self.pos + self.velocity * dt
                proposed_step = np.array([self.pos, proposed_new_pos])
                wall_check = self.Environment.check_wall_collisions(proposed_step)
                walls = wall_check[0]  # shape=(N_walls,2,2)
                wall_collisions = wall_check[1]  # shape=(N_walls,)

                if (wall_collisions is None) or (True not in wall_collisions):
                    # it is safe to move to the new position
                    self.pos = self.pos + self.velocity * dt

                # Bounce off walls you collide with
                elif True in wall_collisions:
                    colliding_wall = walls[np.argwhere(wall_collisions == True)[0][0]]
                    self.velocity = wall_bounce(self.velocity, colliding_wall)
                    self.velocity = (
                        0.5 * self.speed_mean / (np.linalg.norm(self.velocity))
                    ) * self.velocity
                    self.pos += self.velocity * dt

                # handles instances when agent leaves environmnet
                if (
                    self.Environment.check_if_position_is_in_environment(self.pos)
                    is False
                ):
                    self.pos = self.Environment.apply_boundary_conditions(self.pos)

                # calculate the velocity of the step that, after all that, was taken.
                if len(self.history["vel"]) >= 1:
                    last_pos = np.array(self.history["pos"][-1])
                    shift = self.Environment.get_vectors_between___accounting_for_environment(
                        pos1=self.pos, pos2=last_pos
                    )
                    save_velocity = shift.reshape(-1) / self.dt  # accounts for periodic
                else:
                    save_velocity = self.velocity

            elif self.Environment.dimensionality == "1D":
                self.pos = self.pos + dt * self.velocity
                if (
                    self.Environment.check_if_position_is_in_environment(self.pos)
                    is False
                ):
                    if self.Environment.boundary_conditions == "solid":
                        self.velocity *= -1
                    self.pos = self.Environment.apply_boundary_conditions(self.pos)

                self.velocity += ornstein_uhlenbeck(
                    dt=dt,
                    x=self.velocity,
                    drift=self.speed_mean,
                    noise_scale=self.speed_std,
                    coherence_time=self.speed_coherence_time,
                )
                save_velocity = self.velocity

        elif self.use_imported_trajectory == True:
            # use an imported trajectory to
            if self.Environment.dimensionality == "2D":
                interp_time = self.t % max(self.t_interp)
                pos = self.pos_interp(interp_time)
                ex = self.Environment.extent
                self.pos = np.array(
                    [min(max(pos[0], ex[0]), ex[1]), min(max(pos[1], ex[2]), ex[3])]
                )

                # calculate velocity and rotational velocity
                if len(self.history["vel"]) >= 1:
                    last_pos = np.array(self.history["pos"][-1])
                    shift = self.Environment.get_vectors_between___accounting_for_environment(
                        pos1=self.pos, pos2=last_pos
                    )
                    self.velocity = shift.reshape(-1) / self.dt  # accounts for periodic
                else:
                    self.velocity = np.array([0, 0])
                save_velocity = self.velocity

                angle_now = get_angle(self.velocity)
                if len(self.history["vel"]) >= 1:
                    angle_before = get_angle(self.history["vel"][-1])
                else:
                    angle_before = angle_now
                if abs(angle_now - angle_before) > np.pi:
                    if angle_now > angle_before:
                        angle_now -= 2 * np.pi
                    elif angle_now < angle_before:
                        angle_before -= 2 * np.pi
                self.rotational_velocity = (angle_now - angle_before) / self.dt

            if self.Environment.dimensionality == "1D":
                interp_time = self.t % max(self.t_interp)
                pos = self.pos_interp(interp_time)
                ex = self.Environment.extent
                self.pos = np.array([min(max(pos, ex[0]), ex[1])])
                if len(self.history["vel"]) >= 1:
                    self.velocity = (self.pos - self.history["pos"][-1]) / self.dt
                else:
                    self.velocity = np.array([0])
                save_velocity = self.velocity

        if len(self.history["pos"]) >= 1:
            self.distance_travelled += np.linalg.norm(
                self.pos - self.history["pos"][-1]
            )
            tau_speed = 10
            self.average_measured_speed = (
                1 - dt / tau_speed
            ) * self.average_measured_speed + (dt / tau_speed) * np.linalg.norm(
                save_velocity
            )

        # write to history
        self.history["t"].append(self.t)
        self.history["pos"].append(list(self.pos))
        self.history["vel"].append(list(save_velocity))
        if self.Environment.dimensionality == "2D":
            self.history["rot_vel"].append(self.rotational_velocity)

        return self.pos

    def import_trajectory(self, times=None, positions=None, dataset=None):
        """Import trajectory data into the agent by passing a list or array of timestamps and a list or array of positions. These will used for moting rather than the random motion model. The data is interpolated using cubic splines. This means imported data can be low resolution and smoothly upsampled (aka "augmented" with artificial data). 
        
        Note after importing trajectory data you still need to run a simulation using the Agent.update(dt=dt) function. Each update moves the agent by a time dt along its imported trajectory. If the simulation is run for longer than the time availble in the imported trajectory, it loops back to the start. Imported times are shifted so that time[0] = 0.

        Args:
            times (array-like): list or array of time stamps 
            positions (_type_): list or array of positions 
            dataset: if `sargolini' will load `sargolini' trajectory data from './data/sargolini.npz' (Sargolini et al. 2006). Else you can pass a path to a .npz file which must contain time and trajectory data under keys 't' and 'pos'
        """
        from scipy.interpolate import interp1d

        assert (
            self.Environment.boundary_conditions == "solid"
        ), "Only solid boundary conditions are supported"

        if dataset is not None:
            import ratinabox
            import os

            dataset = os.path.join(
                os.path.join(
                    os.path.abspath(os.path.join(ratinabox.__file__, os.pardir)), "data"
                ),
                dataset + ".npz",
            )
            # data = np.load(dataset)
            try:
                data = np.load(dataset)
            except FileNotFoundError:
                print(
                    f"IMPORT FAILED. No datafile found at {dataset}. Please try a different one. For now the default inbuilt random policy will be used."
                )
                return
            times = data["t"]
            positions = data["pos"]
            print(f"Successfully imported dataset from {dataset}")
        else:
            times, positions = np.array(times), np.array(positions)
            print(f"Successfully imported dataset from arrays passed")

        assert len(positions) == len(
            times
        ), "time and position arrays must have same length"

        times = times - min(times)
        self.use_imported_trajectory = True

        ex = self.Environment.extent

        if self.Environment.dimensionality == "2D":
            positions = positions.reshape(-1, 2)
            if (
                (max(positions[:, 0]) > ex[1])
                or (min(positions[:, 0]) < ex[0])
                or (max(positions[:, 1]) > ex[3])
                or (min(positions[:, 1]) < ex[2])
            ):
                print(
                    f"WARNING: the size of the trajectory is significantly larger than the environment you are using. Environment extent is [minx,maxx,miny,maxy]=[{ex[0]:.1f},{ex[1]:.1f},{ex[2]:.1f},{ex[3]:.1f}], whereas extreme coords are [{min(positions[:,0]):.1f},{max(positions[:,0]):.1f},{min(positions[:,1]):.1f},{max(positions[:,1]):.1f}]. Recommended to use larger environment."
                )
            self.t_interp = times
            self.pos_interp = interp1d(
                times, positions, axis=0, kind="cubic", fill_value="extrapolate"
            )

        if self.Environment.dimensionality == "1D":
            positions = positions.reshape(-1, 1)
            if (max(positions) > ex[1]) or (min(positions) < ex[0]):
                print(
                    f"WARNING: the size of the trajectory is significantly larger than the environment you are using. Environment extent is [minx,maxx]=[{ex[0]:.1f},{ex[1]:.1f}], whereas extreme coords are [{min(positions[:,0]):.1f},{max(positions[:,0]):.1f}]. Recommended to use larger environment."
                )
            self.t_interp = times
            self.pos_interp = interp1d(
                times, positions, axis=0, kind="cubic", fill_value="extrapolate"
            )

        return

    def plot_trajectory(
        self,
        t_start=0,
        t_end=None,
        fig=None,
        ax=None,
        decay_point_size=False,
        plot_agent=True,
        xlim=None,
    ):

        """Plots the trajectory between t_start (seconds) and t_end (defaulting to the last time available)
        Args: 
            • t_start: start time in seconds 
            • t_end: end time in seconds (default = self.history["t"][-1])
            • fig, ax: the fig, ax to plot on top of, optional, if not provided used self.Environment.plot_Environment(). This can be used to plot trajectory on top of receptive fields etc. 
            • decay_point_size: decay trajectory point size over time (recent times = largest)
            • plot_agent: dedicated point show agent current position
            • xlim: In 1D, force the xlim to be a certain time (useful if animating this function)

        Returns:
            fig, ax
        """
        dt = self.dt
        approx_speed = self.average_measured_speed
        scatter_distance = 0.02  # on average how far betwen scatter points
        t, pos = np.array(self.history["t"]), np.array(self.history["pos"])
        if t_end == None:
            t_end = t[-1]
        startid = np.argmin(np.abs(t - (t_start)))
        endid = np.argmin(np.abs(t - (t_end)))
        if self.Environment.dimensionality == "2D":
            skiprate = max(1, int(scatter_distance / (approx_speed * dt)))
            trajectory = pos[startid:endid, :][::skiprate]
        if self.Environment.dimensionality == "1D":
            skiprate = max(1, int(scatter_distance / (approx_speed * dt)))
            trajectory = pos[startid:endid][::skiprate]
        time = t[startid:endid][::skiprate]

        if self.Environment.dimensionality == "2D":
            if fig is None and ax is None:
                fig, ax = self.Environment.plot_environment()
            s = 15 * np.ones_like(time)
            if decay_point_size == True:
                s = 15 * np.exp((time - time[-1]) / 10)
                s[(time[-1] - time) > 15] *= 0
            c = ["C0"] * len(time)
            if plot_agent == True:
                s[-1] = 40
                c[-1] = "r"
            ax.scatter(
                trajectory[:, 0],
                trajectory[:, 1],
                s=s,
                alpha=0.7,
                zorder=2,
                c=c,
                linewidth=0,
            )
        if self.Environment.dimensionality == "1D":
            if fig is None and ax is None:
                fig, ax = plt.subplots(figsize=(4, 2))
            ax.scatter(time / 60, trajectory, alpha=0.7, linewidth=0)
            ax.spines["left"].set_position(("data", t_start / 60))
            ax.set_xlabel("Time / min")
            ax.set_ylabel("Position / m")
            ax.set_xlim([t_start / 60, t_end / 60])
            if xlim is not None:
                ax.set_xlim(right=xlim)

            ax.set_ylim(bottom=0, top=self.Environment.extent[1])
            ax.spines["right"].set_color(None)
            ax.spines["top"].set_color(None)
            ax.set_xticks([t_start / 60, t_end / 60])
            ex = self.Environment.extent
            ax.set_yticks([ex[1]])

        return fig, ax

    def animate_trajectory(self, t_start=None, t_end=None, speed_up=1):
        """Returns an animation (anim) of the trajectory, 20fps. 
        Should be saved using comand like 
        anim.save("./where_to_save/animations.gif",dpi=300)

        Args:
            t_start: Agent time at which to start animation
            t_end (_type_, optional): _description_. Defaults to None.
            speed_up: #times real speed animation should come out at 

        Returns:
            animation
        """

        if t_start == None:
            t_start = self.history["t"][0]
        if t_end == None:
            t_end = self.history["t"][-1]

        def animate(i, fig, ax, t_start, t_max, speed_up):
            t = self.history["t"]
            # t_start = t[np.argmin(np.abs(np.array(t) - t_start))]
            # print(t_start)
            t_end = t_start + (i + 1) * speed_up * 40e-3
            ax.clear()
            if self.Environment.dimensionality == "2D":
                fig, ax = self.Environment.plot_environment(fig=fig, ax=ax)
                xlim = None
            if self.Environment.dimensionality == "1D":
                xlim = t_max
            fig, ax = self.plot_trajectory(
                t_start=t_start,
                t_end=t_end,
                fig=fig,
                ax=ax,
                decay_point_size=True,
                xlim=xlim,
            )
            plt.close()
            return

        fig, ax = self.plot_trajectory(0, 10 * self.dt)
        anim = matplotlib.animation.FuncAnimation(
            fig,
            animate,
            interval=40,
            frames=int((t_end - t_start) / (40e-3 * speed_up)),
            blit=False,
            fargs=(fig, ax, t_start, t_end, speed_up),
        )
        return anim

    def plot_position_heatmap(self, dx=None, weights=None, fig=None, ax=None):
        """Plots a heatmap of postions the agent has been in. vmin is always set to zero, so the darkest colormap color (if seen) represents locations which have never been visited 
        Args:
            dx (float, optional): The heatmap bin size. Defaults to 5cm in 2D or 1cm in 1D.
        """
        if self.Environment.dimensionality == "1D":
            if dx is None:
                dx = 0.01
            pos = np.array(self.history["pos"])
            ex = self.Environment.extent
            if fig is None and ax is None:
                fig, ax = self.Environment.plot_environment(height=1)
            heatmap, centres = bin_data_for_histogramming(data=pos, extent=ex, dx=dx)
            # maybe do smoothing?
            ax.plot(centres, heatmap)
            ax.fill_between(centres, 0, heatmap, alpha=0.3)
            ax.set_ylim(top=np.max(heatmap) * 1.2)
            return fig, ax

        elif self.Environment.dimensionality == "2D":
            if dx is None:
                dx = 0.05
            pos = np.array(self.history["pos"])
            ex = self.Environment.extent
            heatmap = bin_data_for_histogramming(data=pos, extent=ex, dx=dx)
            if fig == None and ax == None:
                fig, ax = self.Environment.plot_environment()
            vmin = 0
            vmax = np.max(heatmap)
            ax.imshow(heatmap, extent=ex, interpolation="bicubic", vmin=vmin, vmax=vmax)
        return fig, ax

    def plot_histogram_of_speeds(
        self, fig=None, ax=None, color="C1", return_data=False
    ):
        """Plots a histogram of the observed speeds of the agent. 
        args:
            fig, ax: not required. the ax object to be drawn onto.  
            color: optional. the color.
        Returns:
            fig, ax: the figure
        """
        velocities = np.array(self.history["vel"])
        speeds = np.linalg.norm(velocities, axis=1)
        # exclude speeds above 3sigma
        mu, std = np.mean(speeds), np.std(speeds)
        speeds = speeds[speeds < mu + 3 * std]
        if (fig is None) and (ax is None):
            fig, ax = plt.subplots()
        n, bins, patches = ax.hist(
            speeds, bins=np.linspace(0, 1.2, 100), color=color, alpha=0.8, density=True
        )
        ax.set_xlabel(r"Speed  / $ms^{-1}$")
        ax.set_yticks([])
        ax.set_xlim(left=0, right=8 * std)
        ax.spines["left"].set_color(None)
        ax.spines["right"].set_color(None)
        ax.spines["top"].set_color(None)

        if return_data == True:
            return fig, ax, n, bins, patches
        else:
            return fig, ax

    def plot_histogram_of_rotational_velocities(
        self, fig=None, ax=None, color="C1", return_data=False
    ):
        """Plots a histogram of the observed speeds of the agent. 
        args:
            fig, ax: not required. the ax object to be drawn onto.  
            color: optional. the color.
        Returns:
            fig, ax: the figure
        """
        rot_vels = np.array(self.history["rot_vel"]) * 180 / np.pi
        # exclude rotational velocities above/below 3sigma
        mu, std = np.mean(rot_vels), np.std(rot_vels)
        rot_vels = rot_vels[rot_vels < mu + 3 * std]
        rot_vels = rot_vels[rot_vels > mu - 3 * std]
        if (fig is None) and (ax is None):
            fig, ax = plt.subplots()
        n, bins, patches = ax.hist(
            rot_vels,
            bins=np.linspace(-2000, 2000, 100),
            color=color,
            alpha=0.8,
            density=False,
        )
        ax.set_yticks([])
        ax.set_xlim(-5 * std, 5 * std)
        ax.spines["left"].set_color(None)
        ax.spines["right"].set_color(None)
        ax.spines["top"].set_color(None)
        ax.set_xlabel(r"Rotational velocity / $^{\circ} s^{-1}$")
        if return_data == True:
            return fig, ax, n, bins, patches
        return fig, ax


"""NEURONS"""
"""Parent Class"""


class Neurons:
    """The Neuron class defines a population of Neurons. All Neurons have firing rates which depend explicity on (that is, they "encode") the state of the Agent. As the Agent moves the firing rate of the cells adjust accordingly. 

    All Neuron classes must be initalised with the Agent (to whom these cells belong) since the Agent determines teh firingrates through its position and velocity. The Agent class will itself contain the Environment. Both the Agent (position/velocity) and the Environment (geometry, walls etc.) determine the firing rates. Optionally (but likely) an input dictionary 'params' specifying other params will be given.
    
    This is a generic Parent class. We provide several SubClasses of it. These include: 
    • PlaceCells()
    • GridCells()
    • BoundaryVectorCells()
    • VelocityCells()
    • HeadDirectionCells()
    • SpeedCells()
    • FeedForwardLayer()

    The unique function in each child classes is get_state(). Whenever Neurons.update() is called Neurons.get_state() is then called to calculate and returns the firing rate of the cells at the current moment in time. This is then saved. In order to make your own Neuron subclass you will need to write a class with the following mandatory structure: 

    MyNeuronClass(Neurons):
        def __init__(self, 
                     Agent,
                     params={}): #<-- do not change these 

            default_params = {'a_default_param":3.14159}
            
            default_params.update(params)
            self.params = default_params
            super().__init__(self.params)
        
        def get_state(self,
                      evaluate_at='agent',
                      **kwargs) #<-- do not change these 
            
            firingrate = .....
            ###
                Insert here code which calculates the firing rate.
                This may work differently depending on what you set evaluate_at as. For example, evaluate_at == 'agent' should means that the position or velocity (or whatever determines the firing rate) will by evaluated using the agents current state. You might also like to have an option like evaluate_at == "all" (all positions across an environment are tested simultaneously - plot_rate_map() tries to call this, for example) or evaluate_at == "last" (in a feedforward layer just look at the last firing rate saved in the input layers saves time over recalculating them.). **kwargs allows you to pass position or velocity in manually.  

                By default, the Neurons.update() calls Neurons.get_state() raw. So write the default behaviour of get_state to be what you want it to do in the main training loop. 
            ###

            return firingrate 
            
    As we have written them, Neuron subclasses which have well defined analytic receptive fields (PlaceCells, GridCells but not VelocityCells etc.) can also be queried for any arbitrary pos/velocity (i.e. not just the Agents current state) by passing these in directly to the function "get_state(evaluate_at='all') or get_state(evaluate_at=None, pos=my_array_of_positons)". This calculation is vectorised and relatively fast, returning an array of firing rates one for each position. It is what is used when you try Neuron.plot_rate_map(). 
    

    List of key functions...
        ..that you're likely to use: 
            • update()
            • plot_rate_timeseries()
            • plot_rate_map()
        ...that you might not use but could be useful:
            • save_to_history()
            • boundary_vector_preference_function()   
    """

    def __init__(self, Agent, params={}):
        """Initialise Neurons(), takes as input a parameter dictionary. Any values not provided by the params dictionary are taken from a default dictionary below.

        Args:
            params (dict, optional). Defaults to {}.
        
        Typically you will not actually initialise a Neurons() class, instead you will initialised by one of it's subclasses. 
        """
        default_params = {
            "n": 10,
            "name": "Neurons",
            "color": None,  # just for plotting
        }
        self.Agent = Agent
        default_params.update(params)
        self.params = default_params
        update_class_params(self, self.params)

        self.firingrate = np.zeros(self.n)
        self.history = {}
        self.history["t"] = []
        self.history["firingrate"] = []
        self.history["spikes"] = []

        if verbose is True:
            print(
                f"\nA Neurons() class has been initialised with parameters f{self.params}. Use Neurons.update() to update the firing rate of the Neurons to correspond with the Agent.Firing rates and spikes are saved into the Agent.history dictionary. Plot a timeseries of the rate using Neurons.plot_rate_timeseries(). Plot a rate map of the Neurons using Neurons.plot_rate_map()."
            )

    def update(self):
        firingrate = self.get_state()
        self.firingrate = firingrate.reshape(-1)
        self.save_to_history()
        return

    def plot_rate_timeseries(
        self,
        t_start=0,
        t_end=None,
        chosen_neurons="all",
        spikes=True,
        fig=None,
        ax=None,
        xlim=None,
    ):
        """Plots a timeseries of the firing rate of the neurons between t_start and t_end

        Args:
            • t_start (int, optional): _description_. Defaults to 0.
            • t_end (int, optional): _description_. Defaults to 60.
            • chosen_neurons: Which neurons to plot. string "10" or 10 will plot ten of them, "all" will plot all of them, "12rand" will plot 12 random ones. A list like [1,4,5] will plot cells indexed 1, 4 and 5. Defaults to "all".
            chosen_neurons (str, optional): Which neurons to plot. string "10" will plot 10 of them, "all" will plot all of them, a list like [1,4,5] will plot cells indexed 1, 4 and 5. Defaults to "10".
            • plot_spikes (bool, optional): If True, scatters exact spike times underneath each curve of firing rate. Defaults to True.
            the below params I just added for help with animations
            • fig, ax: the figure, axis to plot on (can be None)
            xlim: fix xlim of plot irrespective of how much time you're plotting 
        Returns:
            fig, ax
        """
        t = np.array(self.history["t"])
        # times to plot
        if t_end is None:
            t_end = t[-1]
        startid = np.argmin(np.abs(t - (t_start)))
        endid = np.argmin(np.abs(t - (t_end)))
        rate_timeseries = np.array(self.history["firingrate"])
        spike_data = np.array(self.history["spikes"])
        t = t[startid:endid]
        rate_timeseries = rate_timeseries[startid:endid]
        spike_data = spike_data[startid:endid]

        # neurons to plot
        chosen_neurons = self.return_list_of_neurons(chosen_neurons)

        firingrates = rate_timeseries[:, chosen_neurons].T
        fig, ax = mountain_plot(
            X=t / 60,
            NbyX=firingrates,
            color=self.color,
            xlabel="Time / min",
            ylabel="Neurons",
            xlim=None,
            fig=fig,
            ax=ax,
        )

        if spikes == True:
            for i in range(len(chosen_neurons)):
                time_when_spiked = t[spike_data[:, chosen_neurons[i]]] / 60
                h = (i + 1 - 0.1) * np.ones_like(time_when_spiked)
                ax.scatter(
                    time_when_spiked, h, color=(self.color or 'C1'), alpha=0.5, s=2, linewidth=0
                )

        ax.set_xticks([t_start / 60, t_end / 60])
        if xlim is not None:
            ax.set_xlim(right=xlim / 60)
            ax.set_xticks([0, xlim / 60])

        return fig, ax

    def plot_rate_map(
        self,
        chosen_neurons="all",
        method="analytic",
        spikes=False,
        fig=None,
        ax=None,
        shape=None,
        **kwargs,
    ):
        """Plots rate maps of neuronal firing rates across the environment
        Args:
            •chosen_neurons: Which neurons to plot. string "10" will plot 10 of them, "all" will plot all of them, a list like [1,4,5] will plot cells indexed 1, 4 and 5. Defaults to "10".
            
            • method: "analytic" "history" "neither": which method to use. If "analytic" (default) tries to calculate rate map by evaluating firing rate at all positions across the environment (note this isn't always well defined. in which case...). If "history", plots ratemap by a weighting a histogram of positions visited by the firingrate observed at that position. If "neither" (or anything else), then neither. 

            • spikes: True or False. Whether to display the occurence of spikes. If False (default) no spikes are shown. If True both ratemap and spikes are shown.

            • shape is the shape of the multiplanlle figure, must be compatible with chosen neurons

            • kwargs are sent to get_state and can be ignore if you don't need to use them
        
        Returns:
            fig, ax 
        """
        if method == "analytic":
            try:
                rate_maps = self.get_state(evaluate_at="all", **kwargs)
            except Exception as e:
                print(
                    "It was not possible to get the rate map by evaluating the firing rate at all positions across the Environment. This is probably because the Neuron class does not support, or it does not have an analytic receptive field. Instead, plotting rate map by weighted position histogram method. Here is the error:"
                )
                print("Error: ", e)
                print("yeet")
                method = "history"
        if method == "history":
            rate_timeseries = np.array(self.history["firingrate"]).T
            if len(rate_timeseries) == 0:
                print("No historical data with which to calculate ratemap.")
                return None, None
        if spikes is True:
            spike_data = self.history["spikes"]
            if len(spike_data) == 0:
                print("No spikes to plot")
                spikes = False
            else:
                spike_data = np.array(spike_data).T

        if self.color == None:
            coloralpha = None
        else:
            coloralpha = list(matplotlib.colors.to_rgba(self.color))
            coloralpha[-1] = 0.5

        chosen_neurons = self.return_list_of_neurons(chosen_neurons=chosen_neurons)

        if self.Agent.Environment.dimensionality == "2D":

            if fig is None and ax is None:
                if shape is None:
                    Nx, Ny = 1, len(chosen_neurons)
                else:
                    Nx, Ny = shape[0], shape[1]
                fig, ax = plt.subplots(
                    Nx, Ny, figsize=(3 * Ny, 3 * Nx), facecolor=coloralpha,
                )
            if not hasattr(ax, "__len__"):
                ax = np.array([ax])

            for (i, ax_) in enumerate(ax.flatten()):
                self.Agent.Environment.plot_environment(fig, ax_)

                if method == "analytic":
                    rate_map = rate_maps[chosen_neurons[i], :].reshape(
                        self.Agent.Environment.discrete_coords.shape[:2]
                    )
                    im = ax_.imshow(rate_map, extent=self.Agent.Environment.extent)
                if method == "history":
                    ex = self.Agent.Environment.extent
                    pos = np.array(self.Agent.history["pos"])
                    rate_timeseries_ = rate_timeseries[chosen_neurons[i], :]
                    rate_map = bin_data_for_histogramming(
                        data=pos, extent=ex, dx=0.05, weights=rate_timeseries_
                    )
                    im = ax_.imshow(rate_map, extent=ex, interpolation="bicubic")
                if spikes is True:
                    pos = np.array(self.Agent.history["pos"])
                    pos_where_spiked = pos[spike_data[chosen_neurons[i], :]]
                    ax_.scatter(
                        pos_where_spiked[:, 0],
                        pos_where_spiked[:, 1],
                        s=2,
                        linewidth=0,
                        alpha=0.7,
                    )
            return fig, ax

        if self.Agent.Environment.dimensionality == "1D":
            if method == "analytic":
                rate_maps = rate_maps[chosen_neurons, :]
                x = self.Agent.Environment.flattened_discrete_coords[:, 0]
            if method == "history":
                ex = self.Agent.Environment.extent
                pos = np.array(self.Agent.history["pos"])[:, 0]
                rate_maps = []
                for neuron_id in chosen_neurons:
                    rate_map, x = bin_data_for_histogramming(
                        data=pos,
                        extent=ex,
                        dx=0.01,
                        weights=rate_timeseries[neuron_id, :],
                    )
                    x, rate_map = interpolate_and_smooth(x, rate_map, sigma=0.03)
                    rate_maps.append(rate_map)
                rate_maps = np.array(rate_maps)

            if fig is None and ax is None:
                fig, ax = self.Agent.Environment.plot_environment(
                    height=len(chosen_neurons)
                )

            if method != "neither":
                fig, ax = mountain_plot(
                    X=x, NbyX=rate_maps, color=self.color, fig=fig, ax=ax,
                )

            if spikes is True:
                for i in range(len(chosen_neurons)):
                    pos = np.array(self.Agent.history["pos"])[:, 0]
                    pos_where_spiked = pos[spike_data[chosen_neurons[i]]]
                    h = (i + 1 - 0.1) * np.ones_like(pos_where_spiked)
                    ax.scatter(
                        pos_where_spiked,
                        h,
                        color=(self.color or 'C1'),
                        alpha=0.5,
                        s=2,
                        linewidth=0,
                    )
            ax.set_xlabel("Position / m")
            ax.set_ylabel("Neurons")

        return fig, ax

    def save_to_history(self):
        cell_spikes = np.random.uniform(0, 1, size=(self.n,)) < (
            self.Agent.dt * self.firingrate
        )
        self.history["t"].append(self.Agent.t)
        self.history["firingrate"].append(list(self.firingrate))
        self.history["spikes"].append(list(cell_spikes))

    def animate_rate_timeseries(self, t_end=None, chosen_neurons="all", speed_up=1):
        """Returns an animation (anim) of the firing rates, 25fps. 
        Should be saved using comand like 
        anim.save("./where_to_save/animations.gif",dpi=300)

        Args:
            • t_end (_type_, optional): _description_. Defaults to None.
            • chosen_neurons: Which neurons to plot. string "10" or 10 will plot ten of them, "all" will plot all of them, "12rand" will plot 12 random ones. A list like [1,4,5] will plot cells indexed 1, 4 and 5. Defaults to "all".

            • speed_up: #times real speed animation should come out at. 

        Returns:
            animation
        """

        if t_end == None:
            t_end = self.history["t"][-1]

        def animate(i, fig, ax, chosen_neurons, t_max, speed_up):
            t = self.history["t"]
            t_start = t[0]
            t_end = t[0] + (i + 1) * speed_up * 50e-3
            ax.clear()
            fig, ax = self.plot_rate_timeseries(
                t_start=t_start,
                t_end=t_end,
                chosen_neurons=chosen_neurons,
                plot_spikes=True,
                fig=fig,
                ax=ax,
                xlim=t_max,
            )
            plt.close()
            return

        fig, ax = self.plot_rate_timeseries(
            t_start=0,
            t_end=10 * self.Agent.dt,
            chosen_neurons=chosen_neurons,
            xlim=t_end,
        )
        anim = matplotlib.animation.FuncAnimation(
            fig,
            animate,
            interval=50,
            frames=int(t_end / 50e-3),
            blit=False,
            fargs=(fig, ax, chosen_neurons, t_end, speed_up),
        )
        return anim

    def return_list_of_neurons(self, chosen_neurons="all"):
        """Returns a list of indices corresponding to neurons. 

        Args:
            which (_type_, optional): _description_. Defaults to "all".
                • "all": all neurons
                • "15" or 15:  15 neurons even spread from index 0 to n
                • "15rand": 15 randomly selected neurons
                • [4,8,23,15]: this list is returned (convertde to integers in case)
                • np.array([[4,8,23,15]]): the list [4,8,23,15] is returned 
        """
        if type(chosen_neurons) is str:
            if chosen_neurons == "all":
                chosen_neurons = np.arange(self.n)
            elif chosen_neurons.isdigit():
                chosen_neurons = np.linspace(0, self.n - 1, int(chosen_neurons)).astype(
                    int
                )
            elif chosen_neuron[-4:] == "rand":
                chosen_neurons = int(chosen_neurons[:-4])
                chosen_neurons = np.random.choice(
                    np.arange(self.n), size=chosen_neurons, replace=False
                )
        if type(chosen_neurons) is int:
            chosen_neurons = np.linspace(0, self.n - 1, chosen_neurons)
        if type(chosen_neurons) is list:
            chosen_neurons = list(np.array(chosen_neurons).astype(int))
            pass
        if type(chosen_neurons) is np.ndarray:
            chosen_neurons = list(chosen_neurons.astype(int))

        return chosen_neurons


"""Specific subclasses """


class PlaceCells(Neurons):
    """The PlaceCells class defines a population of PlaceCells. This class is a subclass of Neurons() and inherits it properties/plotting functions.  

    Must be initialised with an Agent and a 'params' dictionary. 

    PlaceCells defines a set of 'n' place cells scattered across the environment. The firing rate is a functions of the distance from the Agent to the place cell centres. This function (params['description'])can be:
        • gaussian (default)
        • gaussian_threshold
        • diff_of_gaussians
        • top_hat
        • one_hot
    
    List of functions: 
        • get_state()
        • plot_place_cell_locations()
    """

    def __init__(self, Agent, params={}):
        """Initialise PlaceCells(), takes as input a parameter dictionary. Any values not provided by the params dictionary are taken from a default dictionary below.

        Args:
            params (dict, optional). Defaults to {}.
        """
        default_params = {
            "n": 10,
            "name": "PlaceCells",
            "description": "gaussian",
            "widths": 0.20,
            "place_cell_centres": None,  # if given this will overwrite 'n',
            "wall_geometry": "geodesic",
            "min_fr": 0,
            "max_fr": 1,
            "name": "PlaceCells",
        }
        self.Agent = Agent
        default_params.update(params)
        self.params = default_params
        super().__init__(Agent, self.params)

        if self.place_cell_centres is None:
            self.place_cell_centres = self.Agent.Environment.sample_positions(
                n=self.n, method="uniform_jitter"
            )
        else:
            self.n = self.place_cell_centres.shape[0]
        self.place_cell_widths = self.widths * np.ones(self.n)

        if verbose is True:
            print(
                f"PlaceCells successfully initialised. You can see where they are centred at using PlaceCells.plot_place_cell_locations()"
            )
        return

    def get_state(self, evaluate_at="agent", **kwargs):
        """Returns the firing rate of the place cells.
        By default position is taken from the Agent and used to calculate firinf rates. This can also by passed directly (evaluate_at=None, pos=pass_array_of_positions) or ou can use all the positions in the environment (evaluate_at="all").

        Returns:
            firingrates: an array of firing rates 
        """
        if evaluate_at == "agent":
            pos = self.Agent.pos
        elif evaluate_at == "all":
            pos = self.Agent.Environment.flattened_discrete_coords
        else:
            pos = kwargs["pos"]
        pos = np.array(pos)

        # place cell fr's depend only on how far the agent is from cell centres (and their widths)
        dist = self.Agent.Environment.get_distances_between___accounting_for_environment(
            self.place_cell_centres, pos, wall_geometry=self.wall_geometry
        )  # distances to place cell centres
        widths = np.expand_dims(self.place_cell_widths, axis=-1)

        if self.description == "gaussian":
            firingrate = np.exp(-(dist ** 2) / (2 * (widths ** 2)))
        if self.description == "gaussian_threshold":
            firingrate = np.maximum(
                np.exp(-(dist ** 2) / (2 * (widths ** 2))) - np.exp(-1 / 2), 0,
            ) / (1 - np.exp(-1 / 2))
        if self.description == "diff_of_gaussians":
            ratio = 1.5
            firingrate = np.exp(-(dist ** 2) / (2 * (widths ** 2))) - (
                1 / ratio ** 2
            ) * np.exp(-(dist ** 2) / (2 * ((ratio * widths) ** 2)))
            firingrate *= ratio ** 2 / (ratio ** 2 - 1)
        if self.description == "one_hot":
            closest_centres = np.argmin(np.abs(dist), axis=0)
            firingrate = np.eye(self.n)[closest_centres].T
        if self.description == "top_hat":
            firingrate = 1 * (dist < self.widths)

        firingrate = (
            firingrate * (self.max_fr - self.min_fr) + self.min_fr
        )  # scales from being between [0,1] to [min_fr, max_fr]
        return firingrate

    def plot_place_cell_locations(self):
        fig, ax = self.Agent.Environment.plot_environment()
        place_cell_centres = self.place_cell_centres
        ax.scatter(
            place_cell_centres[:, 0],
            place_cell_centres[:, 1],
            c="C1",
            marker="x",
            s=15,
            zorder=2,
        )
        return fig, ax


class GridCells(Neurons):
    """The GridCells class defines a population of GridCells. This class is a subclass of Neurons() and inherits it properties/plotting functions.  

    Must be initialised with an Agent and a 'params' dictionary. 

    GridCells defines a set of 'n' grid cells with random orientations, grid scales and offsets (these can be set non-randomly of coursse). Grids are modelled as the rectified sum of three cosine waves at 60 degrees to each other. 

    List of functions: 
        • get_state()
    """

    def __init__(self, Agent, params={}):
        """Initialise GridCells(), takes as input a parameter dictionary. Any values not provided by the params dictionary are taken from a default dictionary below.

        Args:
            params (dict, optional). Defaults to {}."""

        default_params = {
            "n": 10,
            "gridscale": 0.45,
            "random_orientations": True,
            "random_gridscales": True,
            "min_fr": 0,
            "max_fr": 1,
            "name": "GridCells",
        }
        self.Agent = Agent
        default_params.update(params)
        self.params = default_params
        super().__init__(Agent, self.params)

        # Initialise grid cells
        assert (
            self.Agent.Environment.dimensionality == "2D"
        ), "grid cells only available in 2D"
        self.phase_offsets = np.random.uniform(0, self.gridscale, size=(self.n, 2))
        w = []
        for i in range(self.n):
            w1 = np.array([1, 0])
            if self.random_orientations == True:
                w1 = rotate(w1, np.random.uniform(0, 2 * np.pi))
            w2 = rotate(w1, np.pi / 3)
            w3 = rotate(w1, 2 * np.pi / 3)
            w.append(np.array([w1, w2, w3]))
        self.w = np.array(w)
        if self.random_gridscales == True:
            self.gridscales = np.random.uniform(
                2 * self.gridscale / 3, 1.5 * self.gridscale, size=self.n
            )
        if verbose is True:
            print(
                "GridCells successfully initialised. You can also manually set their gridscale (GridCells.gridscales), offsets (GridCells.phase_offset) and orientations (GridCells.w1, GridCells.w2,GridCells.w3 give the cosine vectors)"
            )
        return

    def get_state(self, evaluate_at="agent", **kwargs):
        """Returns the firing rate of the grid cells.
        By default position is taken from the Agent and used to calculate firing rates. This can also by passed directly (evaluate_at=None, pos=pass_array_of_positions) or ou can use all the positions in the environment (evaluate_at="all").

        Returns:
            firingrates: an array of firing rates 
        """
        if evaluate_at == "agent":
            pos = self.Agent.pos
        elif evaluate_at == "all":
            pos = self.Agent.Environment.flattened_discrete_coords
        else:
            pos = kwargs["pos"]
        pos = np.array(pos)
        pos = pos.reshape(-1, pos.shape[-1])

        # grid cells are modelled as the thresholded sum of three cosines all at 60 degree offsets
        # vectors to grids cells "centred" at their (random) phase offsets
        vecs = get_vectors_between(self.phase_offsets, pos)  # shape = (N_cells,N_pos,2)
        w1 = np.tile(np.expand_dims(self.w[:, 0, :], axis=1), reps=(1, pos.shape[0], 1))
        w2 = np.tile(np.expand_dims(self.w[:, 1, :], axis=1), reps=(1, pos.shape[0], 1))
        w3 = np.tile(np.expand_dims(self.w[:, 2, :], axis=1), reps=(1, pos.shape[0], 1))
        gridscales = np.tile(
            np.expand_dims(self.gridscales, axis=1), reps=(1, pos.shape[0])
        )
        phi_1 = ((2 * np.pi) / gridscales) * (vecs * w1).sum(axis=-1)
        phi_2 = ((2 * np.pi) / gridscales) * (vecs * w2).sum(axis=-1)
        phi_3 = ((2 * np.pi) / gridscales) * (vecs * w3).sum(axis=-1)
        firingrate = 0.5 * ((np.cos(phi_1) + np.cos(phi_2) + np.cos(phi_3)))
        firingrate[firingrate < 0] = 0

        firingrate = (
            firingrate * (self.max_fr - self.min_fr) + self.min_fr
        )  # scales from being between [0,1] to [min_fr, max_fr]
        return firingrate


class BoundaryVectorCells(Neurons):
    """The BoundaryVectorCells class defines a population of Boundary Vector Cells. This class is a subclass of Neurons() and inherits it properties/plotting functions.  

    Must be initialised with an Agent and a 'params' dictionary.  

    BoundaryVectorCells defines a set of 'n' BVCs cells with random orientations preferences, distance preferences  (these can be set non-randomly of course). We use the model described firstly by Hartley et al. (2000) and more recently de Cothi and Barry (2000).

    BVCs can have allocentric (mec,subiculum) OR egocentric (ppc, retrosplenial cortex) reference frames.

    List of functions: 
        • get_state()
        • boundary_vector_preference_function()
    """

    def __init__(self, Agent, params={}):
        """Initialise BoundaryVectorCells(), takes as input a parameter dictionary. Any values not provided by the params dictionary are taken from a default dictionary below.

        Args:
            params (dict, optional). Defaults to {}."""

        default_params = {
            "n": 10,
            "reference_frame": "allocentric",
            "prefered_wall_distance_mean": 0.15,
            "angle_spread_degrees": 11.25,
            "xi": 0.08,  # as in de cothi and barry 2020
            "beta": 12,
            "min_fr": 0,
            "max_fr": 1,
            "name": "BoundaryVectorCells",
        }
        self.Agent = Agent
        default_params.update(params)
        self.params = default_params
        super().__init__(Agent, self.params)

        assert (
            self.Agent.Environment.dimensionality == "2D"
        ), "boundary cells only possible in 2D"
        assert (
            self.Agent.Environment.boundary_conditions == "solid"
        ), "boundary cells only possible with solid boundary conditions"
        xi = self.xi
        beta = self.beta
        test_direction = np.array([1, 0])
        test_directions = [test_direction]
        test_angles = [0]
        self.n_test_angles = 360
        self.dtheta = 2 * np.pi / self.n_test_angles
        for i in range(self.n_test_angles - 1):
            test_direction_ = rotate(test_direction, 2 * np.pi * i / 360)
            test_directions.append(test_direction_)
            test_angles.append(2 * np.pi * i / 360)
        self.test_directions = np.array(test_directions)
        self.test_angles = np.array(test_angles)
        self.sigma_angles = np.array(
            [(self.angle_spread_degrees / 360) * 2 * np.pi] * self.n
        )
        self.tuning_angles = np.random.uniform(0, 2 * np.pi, size=self.n)
        self.tuning_distances = np.random.rayleigh(
            scale=self.prefered_wall_distance_mean, size=self.n,
        )
        self.sigma_distances = self.tuning_distances / beta + xi

        # calculate normalising constants for BVS firing rates in the current environment. Any extra walls you add from here onwards you add will likely push the firingrate up further.
        locs = self.Agent.Environment.discretise_environment(dx=0.04)
        locs = locs.reshape(-1, locs.shape[-1])
        self.cell_fr_norm = np.ones(self.n)
        self.cell_fr_norm = np.max(self.get_state(evaluate_at=None, pos=locs), axis=1)

        if verbose is True:
            print(
                "BoundaryVectorCells (BVCs) successfully initialised. You can also manually set their orientation preferences (BVCs.tuning_angles, BVCs.sigma_angles), distance preferences (BVCs.tuning_distances, BVCs.sigma_distances)."
            )
        return

    def get_state(self, evaluate_at="agent", **kwargs):
        """Here we implement the same type if boundary vector cells as de Cothi et al. (2020), who follow Barry & Burgess, (2007). See equations there. 
    
        The way I do this is a little complex. I will describe how it works from a single position (but remember this can be called in a vectorised manner from an arary of positons in parallel)
            1. An array of normalised "test vectors" span, in all directions at 1 degree increments, from the position
            2. These define an array of line segments stretching from [pos, pos+test vector]
            3. Where these line segments collide with all walls in the environment is established, this uses the function "vector_intercepts()"
            4. This pays attention to only consider the first (closest) wall forawrd along a line segment. Walls behind other walls are "shaded" by closer walls. Its a little complex to do this and requires the function "boundary_vector_preference_function()"
            5. Now that, for every test direction, the closest wall is established it is simple a process of finding the response of the neuron to that wall at that angle (multiple of two gaussians, see de Cothi (2020)) and then summing over all the test angles. 
        
        We also apply a check in the middle to rotate teh reference frame into that of the head direction of the agent iff self.reference_frame='egocentric'.

        By default position is taken from the Agent and used to calculate firing rates. This can also by passed directly (evaluate_at=None, pos=pass_array_of_positions) or ou can use all the positions in the environment (evaluate_at="all").
        """
        if evaluate_at == "agent":
            pos = self.Agent.pos
        elif evaluate_at == "all":
            pos = self.Agent.Environment.flattened_discrete_coords
        else:
            pos = kwargs["pos"]
        pos = np.array(pos)

        N_cells = self.n
        pos = pos.reshape(-1, pos.shape[-1])  # (N_pos,2)
        N_pos = pos.shape[0]
        N_test = self.test_angles.shape[0]
        pos_line_segments = np.tile(
            np.expand_dims(np.expand_dims(pos, axis=1), axis=1), reps=(1, N_test, 2, 1)
        )  # (N_pos,N_test,2,2)
        test_directions_tiled = np.tile(
            np.expand_dims(self.test_directions, axis=0), reps=(N_pos, 1, 1)
        )  # (N_pos,N_test,2)
        pos_line_segments[:, :, 1, :] += test_directions_tiled  # (N_pos,N_test,2,2)
        pos_line_segments = pos_line_segments.reshape(-1, 2, 2)  # (N_pos x N_test,2,2)
        walls = self.Agent.Environment.walls  # (N_walls,2,2)
        N_walls = walls.shape[0]
        pos_lineseg_wall_intercepts = vector_intercepts(
            pos_line_segments, walls
        )  # (N_pos x N_test,N_walls,2)
        pos_lineseg_wall_intercepts = pos_lineseg_wall_intercepts.reshape(
            (N_pos, N_test, N_walls, 2)
        )  # (N_pos,N_test,N_walls,2)
        dist_to_walls = pos_lineseg_wall_intercepts[
            :, :, :, 0
        ]  # (N_pos,N_test,N_walls)
        first_wall_for_each_direction = self.boundary_vector_preference_function(
            pos_lineseg_wall_intercepts
        )  # (N_pos,N_test,N_walls)
        first_wall_for_each_direction_id = np.expand_dims(
            np.argmax(first_wall_for_each_direction, axis=-1), axis=-1
        )  # (N_pos,N_test,1)
        dist_to_first_wall = np.take_along_axis(
            dist_to_walls, first_wall_for_each_direction_id, axis=-1
        ).reshape(
            (N_pos, N_test)
        )  # (N_pos,N_test)
        # reshape everything to have shape (N_cell,N_pos,N_test)

        test_angles = np.tile(
            np.expand_dims(np.expand_dims(self.test_angles, axis=0), axis=0),
            reps=(N_cells, N_pos, 1),
        )  # (N_cell,N_pos,N_test)

        # if egocentric references frame shift angle into coordinate from of heading direction of agent
        if self.reference_frame == "egocentric":
            if evaluate_at == "agent":
                vel = self.Agent.pos
            else:
                vel = kwargs["vel"]
            vel = np.array(vel)
            head_direction_angle = get_angle(vel)
            test_angles = test_angles - head_direction_angle

        tuning_angles = np.tile(
            np.expand_dims(np.expand_dims(self.tuning_angles, axis=-1), axis=-1),
            reps=(1, N_pos, N_test),
        )  # (N_cell,N_pos,N_test)
        sigma_angles = np.tile(
            np.expand_dims(
                np.expand_dims(np.array(self.sigma_angles), axis=-1), axis=-1,
            ),
            reps=(1, N_pos, N_test),
        )  # (N_cell,N_pos,N_test)
        tuning_distances = np.tile(
            np.expand_dims(np.expand_dims(self.tuning_distances, axis=-1), axis=-1),
            reps=(1, N_pos, N_test),
        )  # (N_cell,N_pos,N_test)
        sigma_distances = np.tile(
            np.expand_dims(np.expand_dims(self.sigma_distances, axis=-1), axis=-1),
            reps=(1, N_pos, N_test),
        )  # (N_cell,N_pos,N_test)
        dist_to_first_wall = np.tile(
            np.expand_dims(dist_to_first_wall, axis=0), reps=(N_cells, 1, 1)
        )  # (N_cell,N_pos,N_test)

        g = gaussian(
            dist_to_first_wall, tuning_distances, sigma_distances, norm=1
        ) * von_mises(
            test_angles, tuning_angles, sigma_angles, norm=1
        )  # (N_cell,N_pos,N_test)

        firingrate = g.sum(axis=-1)  # (N_cell,N_pos)
        firingrate = firingrate / np.expand_dims(self.cell_fr_norm, axis=-1)
        firingrate = (
            firingrate * (self.max_fr - self.min_fr) + self.min_fr
        )  # scales from being between [0,1] to [min_fr, max_fr]
        return firingrate

    def boundary_vector_preference_function(self, x):
        """This is a random function needed to efficiently produce boundary vector cells. x is any array of final dimension shape shape[-1]=2. As I use it here x has the form of the output of vector_intercepts. I.e. each point gives shape[-1]=2 lambda values (lam1,lam2) for where a pair of line segments intercept. This function gives a preference for each pair. Preference is -1 if lam1<0 (the collision occurs behind the first point) and if lam2>1 or lam2<0 (the collision occurs ahead of the first point but not on the second line segment). If neither of these are true it's 1/x (i.e. it prefers collisions which are closest).

        Args:
            x (array): shape=(any_shape...,2)

        Returns:
            the preferece values: shape=(any_shape)
        """
        assert x.shape[-1] == 2
        pref = np.piecewise(
            x=x,
            condlist=(x[..., 0] > 0, x[..., 0] < 0, x[..., 1] < 0, x[..., 1] > 1,),
            funclist=(1 / x[x[..., 0] > 0], -1, -1, -1,),
        )
        return pref[..., 0]

    def plot_BVC_receptive_field(self, chosen_neurons="all"):
        """Plots the receptive field (in polar corrdinates) of the BVC cells. For allocentric BVCs "up" in this plot == "North", for egocentric BVCs, up == the head direction of the animals

        Args:
            chosen_neurons: Which neurons to plot. Can be int, list, array or "all". Defaults to "all".

        Returns:
            fig, ax
        """

        if chosen_neurons == "all":
            chosen_neurons = np.arange(self.n)
        if type(chosen_neurons) is str:
            if chosen_neurons.isdigit():
                chosen_neurons = np.linspace(0, self.n - 1, int(chosen_neurons)).astype(
                    int
                )

        fig, ax = plt.subplots(
            1,
            len(chosen_neurons),
            figsize=(3 * len(chosen_neurons), 3 * 1),
            subplot_kw={"projection": "polar"},
        )

        r = np.linspace(0, self.Agent.Environment.scale, 100)
        theta = np.linspace(0, 2 * np.pi, 360)
        [theta_meshgrid, r_meshgrid] = np.meshgrid(theta, r)

        def bvc_rf(theta, r, mu_r=0.5, sigma_r=0.2, mu_theta=0.5, sigma_theta=0.1):
            theta = pi_domain(theta)
            return gaussian(r, mu_r, sigma_r) * von_mises(theta, mu_theta, sigma_theta)

        for i, n in enumerate(chosen_neurons):
            mu_r = self.tuning_distances[n]
            sigma_r = self.sigma_angles[n]
            mu_theta = self.tuning_angles[n]
            sigma_theta = self.sigma_angles[n]
            receptive_field = bvc_rf(
                theta_meshgrid, r_meshgrid, mu_r, sigma_r, mu_theta, sigma_theta
            )
            ax[i].pcolormesh(
                theta, r, receptive_field, edgecolors="face", shading="nearest"
            )
            ax[i].set_xticks([])
            ax[i].set_yticks([])

        return fig, ax


class VelocityCells(Neurons):
    """The VelocityCells class defines a population of Velocity cells. This class is a subclass of Neurons() and inherits it properties/plotting functions.  

    Must be initialised with an Agent and a 'params' dictionary. 

    VelocityCells defines a set of 'dim x 2' velocity cells. Encoding the East, West (and North and South) velocities in 1D (2D). The velocities are scaled according to the expected velocity of he agent (max firing rate acheive when velocity = mean + std)

    List of functions: 
        • get_state()
    """

    def __init__(self, Agent, params={}):
        """Initialise VelocityCells(), takes as input a parameter dictionary. Any values not provided by the params dictionary are taken from a default dictionary below.
        Args:
            params (dict, optional). Defaults to {}."""
        default_params = {
            "min_fr": 0,
            "max_fr": 1,
            "name": "VelocityCells",
        }
        self.Agent = Agent
        default_params.update(params)
        self.params = default_params
        super().__init__(Agent, self.params)

        if self.Agent.Environment.dimensionality == "2D":
            self.n = 4  # one up, one down, one left, one right
        if self.Agent.Environment.dimensionality == "1D":
            self.n = 2  # one left, one right
        self.params["n"] = self.n
        self.one_sigma_speed = self.Agent.speed_mean + self.Agent.speed_std

        if verbose is True:
            print(
                f"VelocityCells successfully initialised. Your environment is {self.Agent.Environment.dimensionality} therefore you have {self.n} velocity cells"
            )
        return

    def get_state(self, evaluate_at="agent", **kwargs):
        """In 2D 4 velocity cells report, respectively, the thresholded leftward, rightward, upward and downwards velocity. By default velocity is taken from the agent but this can also be passed as a kwarg 'vel'"""
        if evaluate_at == "agent":
            vel = self.Agent.history["vel"][-1]
        else:
            try:
                vel = np.array(kwargs["vel"])
            except KeyError:
                vel = np.zeros_like(self.Agent.velocity)

        if self.Agent.Environment.dimensionality == "1D":
            vleft_fr = max(0, vel[0]) / self.one_sigma_speed
            vright_fr = max(0, -vel[0]) / self.one_sigma_speed
            firingrate = np.array([vleft_fr, vright_fr])
        if self.Agent.Environment.dimensionality == "2D":
            vleft_fr = max(0, vel[0]) / self.one_sigma_speed
            vright_fr = max(0, -vel[0]) / self.one_sigma_speed
            vup_fr = max(0, vel[1]) / self.one_sigma_speed
            vdown_fr = max(0, -vel[1]) / self.one_sigma_speed
            firingrate = np.array([vleft_fr, vright_fr, vup_fr, vdown_fr])

        firingrate = (
            firingrate * (self.max_fr - self.min_fr) + self.min_fr
        )  # scales from being between [0,1] to [min_fr, max_fr]

        return firingrate


class HeadDirectionCells(Neurons):
    """The HeadDirectionCells class defines a population of head direction cells. This class is a subclass of Neurons() and inherits it properties/plotting functions.  

    Must be initialised with an Agent and a 'params' dictionary. 

    HeadDirectionCells defines a set of 'dim x 2' velocity cells. Encoding the East, West (and North and South) heading directions in 1D (2D). The firing rates are scaled such that when agent travels due east/west/north,south the firing rate is  = [mfr,0,0,0]/[0,mfr,0,0]/[0,0,mfr,0]/[0,0,0,mfr] (mfr = max_fr)

    List of functions: 
        • get_state()
        """

    def __init__(self, Agent, params={}):
        """Initialise HeadDirectionCells(), takes as input a parameter dictionary. Any values not provided by the params dictionary are taken from a default dictionary below.
        Args:
            params (dict, optional). Defaults to {}."""
        default_params = {
            "min_fr": 0,
            "max_fr": 1,
            "name": "HeadDirectionCells",
        }
        self.Agent = Agent
        for key in params.keys():
            default_params[key] = params[key]
        self.params = default_params
        super().__init__(Agent, self.params)

        if self.Agent.Environment.dimensionality == "2D":
            self.n = 4  # one up, one down, one left, one right
        if self.Agent.Environment.dimensionality == "1D":
            self.n = 2  # one left, one right
        if verbose is True:
            print(
                f"HeadDirectionCells successfully initialised. Your environment is {self.Agent.Environment.dimensionality} therefore you have {self.n} head direction cells"
            )

    def get_state(self, evaluate_at="agent", **kwargs):
        """In 2D 4 head direction cells report the head direction of the animal. For example a population vector of [1,0,0,0] implies due-east motion. By default velocity (which determines head direction) is taken from the agent but this can also be passed as a kwarg 'vel'"""

        if evaluate_at == "agent":
            vel = self.Agent.history["vel"][-1]
        else:
            vel = np.array(kwargs["vel"])

        if self.Agent.Environment.dimensionality == "1D":
            hdleft_fr = max(0, np.sign(vel[0]))
            hdright_fr = max(0, -np.sign(vel[0]))
            firingrate = np.array([hdleft_fr, hdright_fr])
        if self.Agent.Environment.dimensionality == "2D":
            vel = vel / np.linalg.norm(vel)
            hdleft_fr = max(0, vel[0])
            hdright_fr = max(0, -vel[0])
            hdup_fr = max(0, vel[1])
            hddown_fr = max(0, -vel[1])
            firingrate = np.array([hdleft_fr, hdright_fr, hdup_fr, hddown_fr])

        firingrate = (
            firingrate * (self.max_fr - self.min_fr) + self.min_fr
        )  # scales from being between [0,1] to [min_fr, max_fr]

        return firingrate


class SpeedCell(Neurons):
    """The SpeedCell class defines a single speed cell. This class is a subclass of Neurons() and inherits it properties/plotting functions.  

    Must be initialised with an Agent and a 'params' dictionary. 

    The firing rate is scaled according to the expected velocity of the agent (max firing rate acheive when velocity = mean + std)

    List of functions: 
        • get_state()
        """

    def __init__(self, Agent, params={}):
        """Initialise SpeedCell(), takes as input a parameter dictionary, 'params'. Any values not provided by the params dictionary are taken from a default dictionary below.
        Args:
            params (dict, optional). Defaults to {}."""
        default_params = {
            "min_fr": 0,
            "max_fr": 1,
            "name": "SpeedCell",
        }
        self.Agent = Agent
        for key in params.keys():
            default_params[key] = params[key]
        self.params = default_params
        super().__init__(Agent, self.params)
        self.n = 1
        self.one_sigma_speed = self.Agent.speed_mean + self.Agent.speed_std

        if verbose is True:
            print(
                f"SpeedCell successfully initialised. The speed of the agent is encoded linearly by the firing rate of this cell. Speed = 0 --> min firing rate of of {self.min_fr}. Speed = mean + 1std (here {self.one_sigma_speed} --> max firing rate of {self.max_fr}."
            )

    def get_state(self, evaluate_at="agent", **kwargs):
        """Returns the firing rate of the speed cell. By default velocity (which determines speed) is taken from the agent but this can also be passed as a kwarg 'vel'

        Args:
            evaluate_at (str, optional): _description_. Defaults to 'agent'.

        Returns:
            firingrate: np.array([firingrate])
        """
        if evaluate_at == "agent":
            vel = self.Agent.history["vel"][-1]
        else:
            vel = np.array(kwargs["vel"])

        speed = np.linalg.norm(vel)
        firingrate = np.array([speed / self.one_sigma_speed])
        firingrate = (
            firingrate * (self.max_fr - self.min_fr) + self.min_fr
        )  # scales from being between [0,1] to [min_fr, max_fr]
        return firingrate


class FeedForwardLayer(Neurons):
    """The FeedForwardLayer class defines a layer of Neurons() whos firing rates are an activated linear combination of dopwnstream input layers. This class is a subclass of Neurons() and inherits it properties/plotting functions.  

    Must be initialised with an Agent and a 'params' dictionary. 
    Input params dictionary must  contain a list of input_layers which feed into these Neurons. This list looks like [Neurons1, Neurons2,...] where each is a Neurons() class. 

    Currently supported activations include 'sigmoid' (paramterised by max_fr, min_fr, mid_x, width), 'relu' (gain, threshold) and 'linear' specified with the "activation_params" dictionary in the inout params dictionary. See also activate() for full details. 

    Check that the input layers are all named differently. 
    List of functions: 
        • get_state()
        • add_input()
        """

    def __init__(self, Agent, params={}):
        default_params = {
            "n": 10,
            "input_layers": [],  # a list of input layers
            "min_fr": 0,
            "max_fr": 1,
            "activation_params": {
                "activation": "sigmoid",
                "max_fr": 1,
                "min_fr": 0,
                "mid_x": 1,
                "width_x": 2,
            },
            "name": "FeedForwardLayer",
            "weight_init_scale": 0.1,
        }
        self.Agent = Agent
        default_params.update(params)
        self.params = default_params
        super().__init__(Agent, self.params)

        self.inputs = {}
        for input_layer in self.input_layers:
            self.add_input(input_layer)

        if verbose is True:
            print(
                f"FeedForwardLayer initialised with {len(self.inputs.keys())} layers ({self.inputs.keys()}). To add another layer use FeedForwardLayer.add_input_layer().\nTo set the weights manual edit them by changing self.inputs['key']['W']"
            )

    def add_input(self, input_layer):
        """Adds an input layer to the class. Each input layer is stored in a dictionary of self.inputs. Each has an associated matrix of weights which are initialised randomly. 

        Note the inputs are stored in a dictionary. The keys are taken to be the name of each layer passed (input_layer.name). Make sure you set this correctly (and uniquely). 

        Args:
            input_layer_name (_type_): key (the name of the layer)
            input_layer (_type_): the layer intself. Must be a Neurons() class object (e.g. can be PlaceCells(), etc...). 
        """
        n_in = input_layer.n
        input_layer_name = input_layer.name
        w = np.random.normal(
            loc=0, scale=self.weight_init_scale / np.sqrt(n_in), size=(self.n, n_in)
        )
        I = np.zeros(n_in)
        if input_layer_name in self.inputs.keys():
            print(
                f"There already exists a layer called {input_layer_name}. Overwriting it now."
            )
        self.inputs[input_layer_name] = {}
        self.inputs[input_layer_name]["layer"] = input_layer
        self.inputs[input_layer_name]["w"] = w
        self.inputs[input_layer_name]["w_init"] = w.copy()
        self.inputs[input_layer_name]["I"] = I

    def get_state(self, evaluate_at="last", **kwargs):
        """Returns the firing rate of the feedforward layer cells. By default this layer uses the last saved firingrate from its input layers. Alternatively evaluate_at and kwargs can be set to be anything else which will just be passed to the input layer for evaluation. 
        Once the firing rate of the inout layers is established these are multiplied by the weight matrices and then activated to obtain the firing rate of this FeedForwardLayer.

        Args:
            evaluate_at (str, optional). Defaults to 'last'.
        Returns:
            firingrate: array of firing rates 
        """

        if evaluate_at == "last":
            for key in self.inputs.keys():
                self.inputs[key]["I"] = self.inputs[key]["layer"].firingrate
        else:  # kick the can down the road let the input layer decide how to evaluate the firing rates
            for key in self.inputs.keys():
                self.inputs[key]["I"] = self.inputs[key]["layer"].get_state(
                    evaluate_at, **kwargs
                )

        V = []
        for key in self.inputs.keys():
            w = self.inputs[key]["w"]
            I = self.inputs[key]["I"]
            V.append(np.matmul(w, I))
        V = np.sum(np.array(V), axis=0)
        firingrate = activate(V, other_args=self.activation_params)
        firingrate_prime = activate(
            V, other_args=self.activation_params, deriv=True
        )  # you might find this vairable useful for your training rule

        return firingrate


"""OTHER USEFUL FUNCTIONS"""
"""Geometry functions"""


def get_perpendicular(a=None):
    """Given 2-vector, a, returns its perpendicular
    Args:
        a (array, optional): 2-vector direction. Defaults to None.
    Returns:
        array: perpendicular to a
    """
    b = np.empty_like(a)
    b[0] = -a[1]
    b[1] = a[0]
    return b


def vector_intercepts(vector_list_a, vector_list_b, return_collisions=False):
    """
    Each element of vector_list_a gives a line segment of the form [[x_a_0,y_a_0],[x_a_1,y_a_1]], or, in vector notation [p_a_0,p_a_1] (same goes for vector vector_list_b). Thus
        vector_list_A.shape = (N_a,2,2)
        vector_list_B.shape = (N_b,2,2)
    where N_a is the number of vectors defined in vector_list_a

    Each line segments define an (infinite) line, parameterised by line_a = p_a_0 + l_a.(p_a_1-p_a_0). We want to find the intersection between these lines in terms of the parameters l_a and l_b. Iff l_a and l_b are BOTH between 0 and 1 then the line segments intersect. Thus the goal is to return an array, I,  of shape 
        I.shape = (N_a,N_b,2)
    where, if I[n_a,n_b][0] and I[n_a,n_b][1] are both between 0 and 1 then it means line segments vector_list_a[n_a] and vector_list_b[n_b] intersect. 

    To do this we consider solving the equation line_a = line_b. The solution to this is:
        l_a = dot((p_b_0 - p_a_0) , (p_b_1 - p_b_0)_p) / dot((p_a_1 - p_a_0) , (p_b_1 - p_b_0)_p)
        l_b = dot((p_a_0 - p_b_0) , (p_a_1 - p_a_0)_p) / dot((p_b_1 - p_b_0) , (p_a_1 - p_a_0)_p)
    where "_p" denotes the perpendicular (in two-D [x,y]_p = [-y,x]). Using notation
        l_a = dot(d0,sb_p) / dot(sa,sb_p)
        l_b = dot(-d0,sa_p) / dot(sb,sa_p)
    for 
        d0 = p_b_0 - p_a_0
        sa = p_a_1 - p_a_0 
        sb = p_b_1 - p_b_0
    We will calculate these first.

    If return_collisions == True, the list of intercepts is used to assess whether each pair of segments actually collide (True) or not (False) and this bollean array (shape = (N_a,N_b)) is returned instead.
    """
    assert (vector_list_a.shape[-2:] == (2, 2)) and (
        vector_list_b.shape[-2:] == (2, 2)
    ), "vector_list_a and vector_list_b must be shape (_,2,2), _ is optional"
    vector_list_a = vector_list_a.reshape(-1, 2, 2)
    vector_list_b = vector_list_b.reshape(-1, 2, 2)
    vector_list_a = vector_list_a + np.random.normal(
        scale=1e-6, size=vector_list_a.shape
    )
    vector_list_b = vector_list_b + np.random.normal(
        scale=1e-6, size=vector_list_b.shape
    )

    N_a = vector_list_a.shape[0]
    N_b = vector_list_b.shape[0]

    d0 = np.expand_dims(vector_list_b[:, 0, :], axis=0) - np.expand_dims(
        vector_list_a[:, 0, :], axis=1
    )  # d0.shape = (N_a,N_b,2)
    sa = vector_list_a[:, 1, :] - vector_list_a[:, 0, :]  # sa.shape = (N_a,2)
    sb = vector_list_b[:, 1, :] - vector_list_b[:, 0, :]  # sb.shape = (N_b,2)
    sa_p = np.flip(sa.copy(), axis=1)
    sa_p[:, 0] = -sa_p[:, 0]  # sa_p.shape = (N_a,2)
    sb_p = np.flip(sb.copy(), axis=1)
    sb_p[:, 0] = -sb_p[:, 0]  # sb.shape = (N_b,2)

    """Now we can go ahead and solve for the line segments
    since d0 has shape (N_a,N_b,2) in order to perform the dot product we must first reshape sa (etc.) by tiling to shape (N_a,N_b,2)
    """
    sa = np.tile(np.expand_dims(sa, axis=1), reps=(1, N_b, 1))  # sa.shape = (N_a,N_b,2)
    sb = np.tile(np.expand_dims(sb, axis=0), reps=(N_a, 1, 1))  # sb.shape = (N_a,N_b,2)
    sa_p = np.tile(
        np.expand_dims(sa_p, axis=1), reps=(1, N_b, 1)
    )  # sa.shape = (N_a,N_b,2)
    sb_p = np.tile(
        np.expand_dims(sb_p, axis=0), reps=(N_a, 1, 1)
    )  # sb.shape = (N_a,N_b,2)
    """The dot product can now be performed by broadcast multiplying the arraays then summing over the last axis"""
    l_a = (d0 * sb_p).sum(axis=-1) / (sa * sb_p).sum(axis=-1)  # la.shape=(N_a,N_b)
    l_b = (-d0 * sa_p).sum(axis=-1) / (sb * sa_p).sum(axis=-1)  # la.shape=(N_a,N_b)

    intercepts = np.stack((l_a, l_b), axis=-1)
    if return_collisions == True:
        direct_collision = (
            (intercepts[:, :, 0] > 0)
            * (intercepts[:, :, 0] < 1)
            * (intercepts[:, :, 1] > 0)
            * (intercepts[:, :, 1] < 1)
        )
        return direct_collision
    else:
        return intercepts


def shortest_vectors_from_points_to_lines(positions, vectors):
    """
    Takes a list of positions and a list of vectors (line segments) and returns the pairwise  vectors of shortest distance FROM the vector segments TO the positions. 
    Suppose we have a list of N_p positions and a list of N_v line segments (or vectors). Each position is a point like [x_p,y_p], or p_p as a vector. Each vector is defined by two points [[x_v_0,y_v_0],[x_v_1,y_v_1]], or [p_v_0,p_v_1]. Thus 
        positions.shape = (N_p,2)
        vectors.shape = (N_v,2,2)
    
    Each vector defines an infinite line, parameterised by line_v = p_v_0 + l_v . (p_v_1 - p_v_0). We want to solve for the l_v defining the point on the line with the shortest distance to p_p. This is given by:
        l_v = dot((p_p-p_v_0),(p_v_1-p_v_0)/dot((p_v_1-p_v_0),(p_v_1-p_v_0)). 
    Or, using a diferrent notation
        l_v = dot(d,s)/dot(s,s)
    where 
        d = p_p-p_v_0 
        s = p_v_1-p_v_0"""
    assert (positions.shape[-1] == 2) and (
        vectors.shape[-2:] == (2, 2)
    ), "positions and vectors must have shapes (_,2) and (_,2,2) respectively. _ is optional"
    positions = positions.reshape(-1, 2)
    vectors = vectors.reshape(-1, 2, 2)
    positions = positions + np.random.normal(scale=1e-6, size=positions.shape)
    vectors = vectors + np.random.normal(scale=1e-6, size=vectors.shape)

    N_p = positions.shape[0]
    N_v = vectors.shape[0]

    d = np.expand_dims(positions, axis=1) - np.expand_dims(
        vectors[:, 0, :], axis=0
    )  # d.shape = (N_p,N_v,2)
    s = vectors[:, 1, :] - vectors[:, 0, :]  # vectors.shape = (N_v,2)

    """in order to do the dot product we must reshaope s to be d's shape."""
    s_ = np.tile(
        np.expand_dims(s.copy(), axis=0), reps=(N_p, 1, 1)
    )  # s_.shape = (N_p,N_v,2)
    """now do the dot product by broadcast multiplying the arraays then summing over the last axis"""

    l_v = (d * s).sum(axis=-1) / (s * s).sum(axis=-1)  # l_v.shape = (N_p,N_v)

    """
    Now we can actually find the vector of shortest distance from the line segments to the points which is given by the size of the perpendicular
        perp = p_p - (p_v_0 + l_v.s_)
    
    But notice that if l_v > 1 then the perpendicular drops onto a part of the line which doesn't exist. In fact the shortest distance is to the point on the line segment where l_v = 1. Likewise for l_v < 0. To fix this we should limit l_v to be between 1 and 0
    """
    l_v[l_v > 1] = 1
    l_v[l_v < 0] = 0

    """we must reshape p_p and p_v_0 to be shape (N_p,N_v,2), also reshape l_v to be shape (N_p, N_v,1) so we can broadcast multiply it wist s_"""
    p_p = np.tile(
        np.expand_dims(positions, axis=1), reps=(1, N_v, 1)
    )  # p_p.shape = (N_p,N_v,2)
    p_v_0 = np.tile(
        np.expand_dims(vectors[:, 0, :], axis=0), reps=(N_p, 1, 1)
    )  # p_v_0.shape = (N_p,N_v,2)
    l_v = np.expand_dims(l_v, axis=-1)

    perp = p_p - (p_v_0 + l_v * s_)  # perp.shape = (N_p,N_v,2)

    return perp


def get_line_segments_between(pos1, pos2):
    """Takes two position arrays and returns the array of pair-wise line segments between positions in each array (from pos1 to pos2).
    Args:
        pos1 (array): (N x dimensionality) array of positions
        pos2 (array): (M x dimensionality) array of positions
    Returns:
        (N x M x 2 x dimensionality) array of vectors from pos1's to pos2's"""

    pos1_ = pos1.reshape(-1, 1, pos1.shape[-1])
    pos2_ = pos2.reshape(1, -1, pos2.shape[-1])
    pos1 = np.repeat(pos1_, pos2_.shape[1], axis=1)
    pos2 = np.repeat(pos2_, pos1_.shape[0], axis=0)
    lines = np.stack((pos1, pos2), axis=-2)
    return lines


def get_vectors_between(pos1=None, pos2=None, line_segments=None):
    """Takes two position arrays and returns the array of pair-wise vectors between positions in each array (from pos1 to pos2).
    Args:
        pos1 (array): (N x dimensionality) array of positions
        pos2 (array): (M x dimensionality) array of positions
        line_segments: if you already have th el line segments, just pass these 
    Returns:
            (N x M x dimensionality) array of vectors from pos1's to pos2's"""
    if line_segments is None:
        line_segments = get_line_segments_between(pos1, pos2)
    vectors = line_segments[..., 0, :] - line_segments[..., 1, :]
    return vectors


def get_distances_between(pos1=None, pos2=None, vectors=None):
    """Takes two position arrays and returns the array of pair-wise euclidean distances between positions in each array (from pos1 to pos2).
    Args:
        pos1 (array): (N x dimensionality) array of positions
        pos2 (array): (M x dimensionality) array of positions
        vectors: if you already have the pair-wise vectors between pos1 and pos2, just pass these 
    Returns:
            (N x M) array of distances from pos1's to pos2's"""
    if vectors is None:
        vectors = get_vectors_between(pos1, pos2)
    distances = np.linalg.norm(vectors, axis=-1)
    return distances


def get_angle(segment):
    """Given a 'segment' (either 2x2 start and end positions or 2x1 direction bearing) 
         returns the 'angle' of this segment modulo 2pi
    Args:
        segment (array): The segment, (2,2) or (2,) array 
    Returns:
        float: angle of segment
    """
    segment = np.array(segment)
    eps = 1e-6
    if segment.shape == (2,):
        return np.mod(np.arctan2(segment[1], (segment[0] + eps)), 2 * np.pi)
    elif segment.shape == (2, 2):
        return np.mod(
            np.arctan2(
                (segment[1][1] - segment[0][1]), (segment[1][0] - segment[0][0] + eps)
            ),
            2 * np.pi,
        )


def rotate(vector, theta):
    """rotates a vector shape (2,) by angle theta. 
    Args:
        vector (array): the 2d vector
        theta (flaot): the rotation angle
    """
    R = np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])
    vector_new = np.matmul(R, vector)
    return vector_new


def wall_bounce(current_velocity, wall):
    """Given current direction and wall returns a new direction which is the result of reflecting off that wall 
    Args:
        current_direction (array): the current direction vector
        wall (array): start and end coordinates of the wall
    Returns:
        array: new direction
    """
    wall_perp = get_perpendicular(wall[1] - wall[0])
    if np.dot(wall_perp, current_velocity) <= 0:
        wall_perp = (
            -wall_perp
        )  # it is now the get_perpendicular with smallest angle to dir
    wall_par = wall[1] - wall[0]
    if np.dot(wall_par, current_velocity) <= 0:
        wall_par = -wall_par  # it is now the parallel with smallest angle to dir
    wall_par, wall_perp = (
        wall_par / np.linalg.norm(wall_par),
        wall_perp / np.linalg.norm(wall_perp),
    )  # normalise
    new_velocity = wall_par * np.dot(current_velocity, wall_par) - wall_perp * np.dot(
        current_velocity, wall_perp
    )

    return new_velocity


def pi_domain(x):
    """Converts x (in radians) to be on domain [-pi,pi]
    Args: x (flat or array): angles
    Returns:x: angles recast onto [-pi,pi] domain
    """
    x = np.array(x)
    x_ = x.reshape(-1)
    x_ = x_ % (2 * np.pi)
    x_[x_ > np.pi] = -2 * np.pi + x_[x_ > np.pi]
    x = x_.reshape(x.shape)
    return x


"""Stochastic-assistance functions"""


def ornstein_uhlenbeck(dt, x, drift=0.0, noise_scale=0.2, coherence_time=5.0):
    """An ornstein uhlenbeck process in x.
    x can be multidimensional 
    Args:
        dt: update time step
        x: the stochastic variable being updated
        drift (float, or same type as x, optional): [description]. Defaults to 0.
        noise_scale (float, or same type as v, optional): Magnitude of deviations from drift. Defaults to 0.16 (16 cm s^-1).
        coherence_time (float, optional): Effectively over what time scale you expect x to change directions. Defaults to 5.

    Returns:
        dv (same type as v); the required update ot the velocity
    """
    x = np.array(x)
    drift = drift * np.ones_like(x)
    noise_scale = noise_scale * np.ones_like(x)
    coherence_time = coherence_time * np.ones_like(x)
    sigma = np.sqrt((2 * noise_scale ** 2) / (coherence_time * dt))
    theta = 1 / coherence_time
    dx = theta * (drift - x) * dt + sigma * np.random.normal(size=x.shape, scale=dt)
    return dx


def interpolate_and_smooth(x, y, sigma=None):
    """Interpolates with cublic spline x and y to 10x resolution then smooths these with a gaussian kernel of width sigma. Currently this only works for 1-dimensional x.
    Args:
        x 
        y 
        sigma 
    Returns (x_new,y_new)
    """
    from scipy.ndimage.filters import gaussian_filter1d
    from scipy.interpolate import interp1d

    y_cubic = interp1d(x, y, kind="cubic")
    x_new = np.arange(x[0], x[-1], (x[1] - x[0]) / 10)
    y_interpolated = y_cubic(x_new)
    if sigma is not None:
        y_smoothed = gaussian_filter1d(
            y_interpolated, sigma=sigma / (x_new[1] - x_new[0])
        )
        return x_new, y_smoothed
    else:
        return x_new, y_interpolated


def normal_to_rayleigh(x, sigma=1):
    """Converts a normally distributed variable (mean 0, var 1) to a rayleigh distributed variable (sigma)
    """
    x = scipy.stats.norm.cdf(x)  # norm to uniform)
    x = sigma * np.sqrt(-2 * np.log(1 - x))  # uniform to rayleigh
    return x


def rayleigh_to_normal(x, sigma=1):
    """Converts a rayleigh distributed variable (sigma) to a normally distributed variable (mean 0, var 1)
    """
    if x <= 0:
        x = 1e-6
    if x >= 1:
        x = 1 - 1e-6
    x = 1 - np.exp(-(x ** 2) / (2 * sigma ** 2))  # rayleigh to uniform
    x = scipy.stats.norm.ppf(x)  # uniform to normal
    return x


"""Plotting functions"""


def bin_data_for_histogramming(data, extent, dx, weights=None):
    """Bins data ready for plotting. So for example if the data is 1D the extent is broken up into bins (leftmost edge = extent[0], rightmost edge = extent[1]) and then data is histogrammed into these bins. weights weights the histogramming process so the contribution of each data point to a bin count is the weight, not 1. 

    Args:
        data (array): (2,N) for 2D or (N,) for 1D)
        extent (_type_): _description_
        dx (_type_): _description_
        weights (_type_, optional): _description_. Defaults to None.

    Returns:
        (heatmap,bin_centres): if 1D
        (heatmap): if 2D
    """
    if len(extent) == 2:  # dimensionality = "1D"
        bins = np.arange(extent[0], extent[1] + dx, dx)
        heatmap, xedges = np.histogram(data, bins=bins, weights=weights)
        centres = (xedges[1:] + xedges[:-1]) / 2
        return (heatmap, centres)

    elif len(extent) == 4:  # dimensionality = "2D"
        bins_x = np.arange(extent[0], extent[1] + dx, dx)
        bins_y = np.arange(extent[2], extent[3] + dx, dx)
        heatmap, xedges, yedges = np.histogram2d(
            data[:, 0], data[:, 1], bins=[bins_x, bins_y], weights=weights
        )
        heatmap = heatmap.T[::-1, :]
        return heatmap


def mountain_plot(
    X, NbyX, color="C0", xlabel="", ylabel="", xlim=None, fig=None, ax=None,
):
    """Make a mountain plot. NbyX is an N by X array of all the plots to display. The nth plot is shown at height n, line are scaled so the maximum value across all of them is 0.7, then they are all seperated by 1 (sot they don't overlap)

    Args:
        X: independent variable to go on X axis 
        NbyX: dependent variables to go on y axis
        color: plot color. Defaults to "C0".
        xlabel (str, optional): x axis label. Defaults to "".
        ylabel (str, optional): y axis label. Defaults to "".
        xlim (_type_, optional): fix xlim to this is desired. Defaults to None.
        fig (_type_, optional): fig to plot over if desired. Defaults to None.
        ax (_type_, optional): ax to plot on if desider. Defaults to None.

    Returns:
        fig, ax: _description_
    """
    c = color or "C1"
    c = np.array(matplotlib.colors.to_rgb(c))
    fc = 0.3 * c + (1 - 0.3) * np.array([1, 1, 1])  # convert rgb+alpha to rgb

    NbyX = 0.7 * NbyX / np.max(np.abs(NbyX))
    if fig is None and ax is None:
        fig, ax = plt.subplots(
            figsize=(4, len(NbyX) * 5.5 / 25)
        )  # ~6mm gap between lines
    for i in range(len(NbyX)):
        ax.plot(X, NbyX[i] + i + 1, c=c)
        ax.fill_between(X, NbyX[i] + i + 1, i + 1, facecolor=fc)
    ax.spines["left"].set_bounds(1, len(NbyX))
    ax.spines["bottom"].set_position(("outward", 1))
    ax.spines["left"].set_position(("outward", 1))
    ax.set_yticks([1, len(NbyX)])
    ax.set_ylim(1 - 0.5, len(NbyX) + 1)
    ax.set_xticks(np.arange(max(X + 0.1)))
    ax.spines["left"].set_color(None)
    ax.spines["right"].set_color(None)
    ax.spines["top"].set_color(None)
    ax.set_yticks([])
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_ylim()
    if xlim is not None:
        ax.set_xlim(right=xlim)

    return fig, ax


"""Other"""


def update_class_params(Class, params: dict):
    """Updates parameters from a dictionary. 
    All parameters found in params will be updated to new value
    Args:
        params (dict): dictionary of parameters to change
        initialise (bool, optional): [description]. Defaults to False.
    """
    for key, value in params.items():
        setattr(Class, key, value)


def gaussian(x, mu, sigma, norm=None):
    """Gaussian function. x, mu and sigma can be any shape as long as they are all the same (or strictly, all broadcastable) 
    Args:
        x: input
        mu ; mean
        sigma; standard deviation
        norm: if provided the maximum value will be the norm
    Returns gaussian(x;mu,sigma)
    """
    g = -((x - mu) ** 2)
    g = g / (2 * sigma ** 2)
    g = np.exp(g)
    norm = norm or (1 / (np.sqrt(2 * np.pi * sigma ** 2)))
    g = g * norm
    return g


def von_mises(theta, mu, sigma, norm=None):
    """Von Mises function. theta, mu and sigma can be any shape as long as they are all the same (or strictly, all broadcastable). sigma is the standard deviation (in radians) which is converted to the von mises spread parameter, kappa = 1 / sigma^2 (note this approximation is only true for small, sigma << 2pi, spreads). All quantities must be given in radians. 
    Args:
        x: input
        mu ; mean
        sigma; standard deviation
        norm: if provided the maximum (i.e. in the centre) value will be the norm
    Returns von_mises(x;mu,sigma)
    """
    kappa = 1 / (sigma ** 2)
    v = np.exp(kappa * np.cos(theta - mu))
    norm = norm or (np.exp(kappa) / (2 * np.pi * scipy.special.i0(kappa)))
    norm = norm / np.exp(kappa)
    v = v * norm
    return v


def activate(x, activation="sigmoid", deriv=False, other_args={}):
    """Activation function function

    Args:
        x (the input (vector))
        activation: which type of fucntion to use (this is overwritten by 'activation' key in other_args)
        deriv (bool, optional): Whether it return f(x) or df(x)/dx. Defaults to False.
        other_args: Dictionary of parameters including other_args["activation"] = str for what type of activation (sigmoid, linear) and other params e.g. sigmoid midpoi n, max firing rate... 

    Returns:
        f(x) or df(x)/dx : array same as x
    """
    try:
        name = other_args["activation"]
    except KeyError:
        name = activation

    if name == "linear":
        if deriv == False:
            return x
        elif deriv == True:
            return np.ones(x.shape)

    if name == "sigmoid":
        # default sigmoid parameters set so that
        # max_f = max firing rate = 1
        # mid_x = middle point on domain = 1
        # width_x = distance from 5percent_x to 95percent_x = 1
        other_args_default = {"max_fr": 1, "min_fr": 0, "mid_x": 1, "width_x": 1}
        other_args_default.update(other_args)
        other_args = other_args_default
        max_fr, min_fr, width_x, mid_x = (
            other_args["max_fr"],
            other_args["min_fr"],
            other_args["width_x"],
            other_args["mid_x"],
        )
        beta = np.log((1 - 0.05) / 0.05) / (0.5 * width_x)  # sigmoid width
        if deriv == False:
            exp = np.exp(-beta * (x - mid_x))
            return ((max_fr - min_fr) / (1 + np.exp(-beta * (x - mid_x)))) + min_fr
        elif deriv == True:
            f = activate(x, deriv=False, other_args=other_args)
            return beta * (f - min_fr) * (1 - (f - min_fr) / (max_fr - min_fr))

    if name == "relu":
        other_args_default = {"gain": 1, "threshold": 0}
        for key in other_args.keys():
            other_args_default[key] = other_args[key]
        other_args = other_args_default
        if deriv == False:
            return other_args["gain"] * np.maximum(0, x - other_args["threshold"])
        elif deriv == True:
            return other_args["gain"] * ((x - other_args["threshold"]) > 0)
