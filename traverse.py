"""
Rover Traverse Optimization using NSGA-II Multi-Objective Optimization.

This module implements optimal path planning for a lunar rover traversing
from a landing site to an ice deposit target. The NSGA-II algorithm
simultaneously minimizes three objectives:
    1. Total path distance (energy consumption proxy)
    2. Cumulative hazard exposure
    3. Maximum shadow fraction along the path

The resulting Pareto front allows mission planners to select paths that
best balance these competing objectives.
"""

import numpy as np
from pymoo.core.problem import Problem
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.optimize import minimize

from . import config


# =============================================================================
# COST SURFACE GENERATION
# =============================================================================

def build_cost_surfaces(slope, hazard_map, illumination_frac, pixel_size):
    """
    Create cost grids for multi-objective traverse optimization.

    Generates three distinct cost surfaces representing the energy,
    safety, and illumination penalties for each pixel in the terrain.
    Pixels with slope > 20° are marked as impassable (cost = 1e6).

    Parameters
    ----------
    slope : np.ndarray
        2-D array of terrain slope values in degrees.
    hazard_map : np.ndarray
        2-D array of hazard severity values (0 = safe, 1 = dangerous).
    illumination_frac : np.ndarray
        2-D array of time-averaged illumination fraction (0–1).
    pixel_size : float
        Ground sampling distance in meters per pixel.

    Returns
    -------
    dict
        Dictionary with keys:
            - 'energy_cost' : np.ndarray — slope-dependent locomotion cost
            - 'safety_cost' : np.ndarray — hazard-weighted traversal cost
            - 'shadow_cost' : np.ndarray — shadow-weighted traversal cost
    """
    # Energy cost: slope-dependent locomotion model
    # Cost scales with tan(slope) to capture increased power on steep terrain
    slope_rad = np.deg2rad(np.clip(slope, 0, 89))
    energy_cost = pixel_size * (1.0 + np.tan(slope_rad))

    # Safety cost: hazard map scaled by pixel size
    safety_cost = hazard_map * pixel_size

    # Shadow cost: penalizes traversal through unilluminated regions
    shadow_cost = (1.0 - illumination_frac) * pixel_size * 2.0

    # Mark impassable terrain (slope > 20°)
    impassable = slope > config.ROVER_MAX_SLOPE
    energy_cost[impassable] = 1e6
    safety_cost[impassable] = 1e6
    shadow_cost[impassable] = 1e6

    return {
        'energy_cost': energy_cost,
        'safety_cost': safety_cost,
        'shadow_cost': shadow_cost,
    }


# =============================================================================
# NSGA-II PROBLEM DEFINITION
# =============================================================================

class RoverTraverseProblem(Problem):
    """
    Multi-objective rover traverse problem for NSGA-II optimization.

    Decision variables encode n_waypoints intermediate waypoint positions
    as (row, col) pairs. The algorithm optimizes three objectives:
        f1 — total path distance (accumulated energy cost)
        f2 — cumulative hazard cost along the path
        f3 — maximum shadow fraction encountered along the path

    A single constraint enforces that no waypoint or path segment
    traverses terrain steeper than the rover's maximum slope limit.

    Parameters
    ----------
    cost_energy : np.ndarray
        Energy cost surface from build_cost_surfaces.
    cost_safety : np.ndarray
        Safety cost surface from build_cost_surfaces.
    cost_shadow : np.ndarray
        Shadow cost surface from build_cost_surfaces.
    slope : np.ndarray
        Terrain slope array in degrees.
    illumination : np.ndarray
        Illumination fraction array (0–1).
    start : tuple of int
        Start position as (row, col).
    goal : tuple of int
        Goal position as (row, col).
    n_waypoints : int, optional
        Number of intermediate waypoints (default: 8).
    pixel_size : float, optional
        Ground sampling distance in meters (default: 20).
    """

    def __init__(self, cost_energy, cost_safety, cost_shadow,
                 slope, illumination, start, goal,
                 n_waypoints=8, pixel_size=20):
        self.cost_energy = cost_energy
        self.cost_safety = cost_safety
        self.cost_shadow = cost_shadow
        self.slope = slope
        self.illumination = illumination
        self.start = np.array(start, dtype=int)
        self.goal = np.array(goal, dtype=int)
        self.n_waypoints = n_waypoints
        self.pixel_size = pixel_size

        n_rows, n_cols = slope.shape

        # Variable bounds: each waypoint has (row, col)
        xl = np.zeros(n_waypoints * 2)
        xu = np.zeros(n_waypoints * 2)
        for i in range(n_waypoints):
            xl[2 * i] = 0               # row lower bound
            xu[2 * i] = n_rows - 1       # row upper bound
            xl[2 * i + 1] = 0            # col lower bound
            xu[2 * i + 1] = n_cols - 1   # col upper bound

        super().__init__(
            n_var=n_waypoints * 2,
            n_obj=3,
            n_ieq_constr=1,
            xl=xl,
            xu=xu,
            type_var=float,
        )

    def _decode_waypoints(self, x):
        """
        Decode decision variable vector into ordered waypoint list.

        Parameters
        ----------
        x : np.ndarray
            Decision variable vector of length n_waypoints * 2.

        Returns
        -------
        list of np.ndarray
            Full waypoint sequence including start and goal.
        """
        waypoints = [self.start.copy()]
        for i in range(self.n_waypoints):
            row = int(np.clip(x[2 * i], 0, self.slope.shape[0] - 1))
            col = int(np.clip(x[2 * i + 1], 0, self.slope.shape[1] - 1))
            waypoints.append(np.array([row, col]))
        waypoints.append(self.goal.copy())
        return waypoints

    def _interpolate_segment(self, p1, p2, n_interp=20):
        """
        Interpolate straight line between two waypoints.

        Parameters
        ----------
        p1, p2 : np.ndarray
            Start and end points as [row, col].
        n_interp : int
            Number of interpolation steps.

        Returns
        -------
        np.ndarray
            Array of shape (n_interp, 2) with integer pixel coordinates.
        """
        rows = np.linspace(p1[0], p2[0], n_interp).astype(int)
        cols = np.linspace(p1[1], p2[1], n_interp).astype(int)
        rows = np.clip(rows, 0, self.slope.shape[0] - 1)
        cols = np.clip(cols, 0, self.slope.shape[1] - 1)
        return np.column_stack([rows, cols])

    def _evaluate(self, X, out, *args, **kwargs):
        """
        Evaluate all individuals in population X.

        Computes three objectives and one constraint for each individual.
        """
        n_pop = X.shape[0]
        F = np.zeros((n_pop, 3))
        G = np.zeros((n_pop, 1))

        for idx in range(n_pop):
            waypoints = self._decode_waypoints(X[idx])

            total_distance = 0.0
            total_hazard = 0.0
            max_shadow = 0.0
            max_slope_encountered = 0.0

            for i in range(len(waypoints) - 1):
                segment = self._interpolate_segment(
                    waypoints[i], waypoints[i + 1], n_interp=20
                )

                for j in range(len(segment) - 1):
                    r1, c1 = segment[j]
                    r2, c2 = segment[j + 1]

                    # Euclidean distance in pixel space, scaled to meters
                    dx = (r2 - r1) * self.pixel_size
                    dy = (c2 - c1) * self.pixel_size
                    step_dist = np.sqrt(dx**2 + dy**2)

                    # Accumulate energy cost
                    total_distance += self.cost_energy[r2, c2]

                    # Accumulate hazard cost
                    total_hazard += self.cost_safety[r2, c2]

                    # Track maximum shadow (1 - illumination)
                    shadow_here = 1.0 - self.illumination[r2, c2]
                    if shadow_here > max_shadow:
                        max_shadow = shadow_here

                    # Track max slope for constraint
                    slope_here = self.slope[r2, c2]
                    if slope_here > max_slope_encountered:
                        max_slope_encountered = slope_here

            F[idx, 0] = total_distance   # Objective 1: energy/distance
            F[idx, 1] = total_hazard     # Objective 2: hazard
            F[idx, 2] = max_shadow       # Objective 3: max shadow

            # Constraint: max slope must be <= 20° (g <= 0 means feasible)
            G[idx, 0] = max_slope_encountered - config.ROVER_MAX_SLOPE

        out["F"] = F
        out["G"] = G


# =============================================================================
# NSGA-II EXECUTION
# =============================================================================

def run_nsga2(cost_energy, cost_safety, cost_shadow,
              slope, illumination, start, goal,
              n_waypoints=8, pixel_size=20):
    """
    Execute NSGA-II multi-objective optimization for rover traverse.

    Sets up and runs the NSGA-II algorithm with SBX crossover and
    polynomial mutation to find a Pareto-optimal set of paths.

    Parameters
    ----------
    cost_energy : np.ndarray
        Energy cost surface.
    cost_safety : np.ndarray
        Safety cost surface.
    cost_shadow : np.ndarray
        Shadow cost surface.
    slope : np.ndarray
        Terrain slope array in degrees.
    illumination : np.ndarray
        Illumination fraction array (0–1).
    start : tuple of int
        Start position as (row, col).
    goal : tuple of int
        Goal position as (row, col).
    n_waypoints : int, optional
        Number of intermediate waypoints (default: 8).
    pixel_size : float, optional
        Ground sampling distance in meters (default: 20).

    Returns
    -------
    pareto_F : np.ndarray
        Objective values for each Pareto-optimal solution, shape (N, 3).
    pareto_X : np.ndarray
        Decision variables for each Pareto-optimal solution, shape (N, n_var).
    problem : RoverTraverseProblem
        The problem instance (needed for decoding solutions).
    """
    problem = RoverTraverseProblem(
        cost_energy, cost_safety, cost_shadow,
        slope, illumination, start, goal,
        n_waypoints=n_waypoints, pixel_size=pixel_size,
    )

    algorithm = NSGA2(
        pop_size=config.NSGA2_POP_SIZE,
        n_offsprings=config.NSGA2_N_OFFSPRINGS,
        crossover=SBX(prob=0.9, eta=15),
        mutation=PM(eta=20),
    )

    result = minimize(
        problem,
        algorithm,
        ('n_gen', config.NSGA2_N_GENERATIONS),
        seed=42,
        verbose=False,
    )

    pareto_F = result.F
    pareto_X = result.X

    return pareto_F, pareto_X, problem


# =============================================================================
# PATH SELECTION FROM PARETO FRONT
# =============================================================================

def select_best_path(pareto_F, pareto_X, problem, preference='balanced'):
    """
    Select a single path from the Pareto front based on user preference.

    Parameters
    ----------
    pareto_F : np.ndarray
        Objective values for Pareto-optimal solutions, shape (N, 3).
    pareto_X : np.ndarray
        Decision variables for Pareto-optimal solutions, shape (N, n_var).
    problem : RoverTraverseProblem
        Problem instance for decoding waypoints.
    preference : str, optional
        Selection strategy (default: 'balanced'):
            - 'shortest' : minimize total distance (f1)
            - 'safest'   : minimize hazard exposure (f2)
            - 'balanced' : closest to normalized origin (compromise)

    Returns
    -------
    path : list of np.ndarray
        Ordered list of [row, col] waypoints for the selected path.
    objectives : np.ndarray
        The three objective values for the selected path.
    energy_profile : list of dict
        Energy profile along the selected path (see compute_energy_profile).
    """
    if preference == 'shortest':
        best_idx = np.argmin(pareto_F[:, 0])
    elif preference == 'safest':
        best_idx = np.argmin(pareto_F[:, 1])
    elif preference == 'balanced':
        # Normalize each objective to [0, 1] and find closest to origin
        f_min = pareto_F.min(axis=0)
        f_max = pareto_F.max(axis=0)
        f_range = f_max - f_min
        f_range[f_range == 0] = 1.0  # avoid division by zero
        f_norm = (pareto_F - f_min) / f_range
        distances = np.sqrt(np.sum(f_norm**2, axis=1))
        best_idx = np.argmin(distances)
    else:
        raise ValueError(
            f"Unknown preference '{preference}'. "
            f"Choose from 'shortest', 'safest', 'balanced'."
        )

    best_x = pareto_X[best_idx]
    objectives = pareto_F[best_idx]

    # Reconstruct full waypoint list
    path = problem._decode_waypoints(best_x)

    # Compute energy profile along selected path
    energy_profile = compute_energy_profile(
        path, problem.slope, problem.illumination, problem.pixel_size,
    )

    return path, objectives, energy_profile


# =============================================================================
# ENERGY PROFILE COMPUTATION
# =============================================================================

def compute_energy_profile(path, slope, illumination, pixel_size,
                           solar_power=None, locomotion_power=None,
                           battery_wh=None, rover_speed=None):
    """
    Compute detailed energy budget along a rover traverse path.

    For each segment between consecutive waypoints, calculates distance
    traveled, time elapsed, slope-dependent energy consumed, and solar
    energy gained (if illuminated). Tracks cumulative battery state.

    Parameters
    ----------
    path : list of np.ndarray
        Ordered list of [row, col] waypoints.
    slope : np.ndarray
        Terrain slope array in degrees.
    illumination : np.ndarray
        Illumination fraction array (0–1).
    pixel_size : float
        Ground sampling distance in meters.
    solar_power : float, optional
        Solar panel output in Watts (default: from config).
    locomotion_power : float, optional
        Base locomotion power in Watts (default: from config).
    battery_wh : float, optional
        Battery capacity in Watt-hours (default: from config).
    rover_speed : float, optional
        Rover speed in m/s (default: from config).

    Returns
    -------
    list of dict
        Each dict contains:
            - 'waypoint'     : int — waypoint index
            - 'energy_wh'    : float — cumulative battery energy (Wh)
            - 'distance_m'   : float — cumulative distance traveled (m)
            - 'time_h'       : float — cumulative time elapsed (hours)
            - 'illuminated'  : bool — whether segment is illuminated
            - 'slope_deg'    : float — average slope of segment (degrees)
    """
    # Use config defaults if not specified
    if solar_power is None:
        solar_power = config.ROVER_SOLAR_POWER
    if locomotion_power is None:
        locomotion_power = config.ROVER_LOCOMOTION_POWER
    if battery_wh is None:
        battery_wh = config.ROVER_BATTERY_CAPACITY
    if rover_speed is None:
        rover_speed = config.ROVER_SPEED

    profile = []
    cumulative_energy = battery_wh
    cumulative_distance = 0.0
    cumulative_time = 0.0

    # Initial waypoint entry
    r0, c0 = int(path[0][0]), int(path[0][1])
    profile.append({
        'waypoint': 0,
        'energy_wh': cumulative_energy,
        'distance_m': 0.0,
        'time_h': 0.0,
        'illuminated': bool(illumination[r0, c0] > 0.5),
        'slope_deg': float(slope[r0, c0]),
    })

    for i in range(1, len(path)):
        r_prev = int(path[i - 1][0])
        c_prev = int(path[i - 1][1])
        r_curr = int(path[i][0])
        c_curr = int(path[i][1])

        # Clip to valid grid bounds
        r_prev = np.clip(r_prev, 0, slope.shape[0] - 1)
        c_prev = np.clip(c_prev, 0, slope.shape[1] - 1)
        r_curr = np.clip(r_curr, 0, slope.shape[0] - 1)
        c_curr = np.clip(c_curr, 0, slope.shape[1] - 1)

        # Segment distance in meters
        dr = (r_curr - r_prev) * pixel_size
        dc = (c_curr - c_prev) * pixel_size
        segment_dist = np.sqrt(dr**2 + dc**2)

        # Travel time for this segment
        if rover_speed > 0:
            segment_time_s = segment_dist / rover_speed
        else:
            segment_time_s = 0.0
        segment_time_h = segment_time_s / 3600.0

        # Average slope along segment
        avg_slope = (slope[r_prev, c_prev] + slope[r_curr, c_curr]) / 2.0

        # Slope-dependent energy consumption
        # Power increases with slope: P = P_base * (1 + tan(slope))
        slope_factor = 1.0 + np.tan(np.deg2rad(min(avg_slope, 85.0)))
        energy_consumed = locomotion_power * slope_factor * segment_time_h

        # Solar energy gained if illuminated
        is_illuminated = illumination[r_curr, c_curr] > 0.5
        if is_illuminated:
            energy_gained = solar_power * segment_time_h
        else:
            energy_gained = 0.0

        # Update cumulative state
        cumulative_energy = cumulative_energy - energy_consumed + energy_gained
        cumulative_energy = np.clip(cumulative_energy, 0, battery_wh)
        cumulative_distance += segment_dist
        cumulative_time += segment_time_h

        profile.append({
            'waypoint': i,
            'energy_wh': float(cumulative_energy),
            'distance_m': float(cumulative_distance),
            'time_h': float(cumulative_time),
            'illuminated': bool(is_illuminated),
            'slope_deg': float(avg_slope),
        })

    return profile


# =============================================================================
# PATH INTERPOLATION
# =============================================================================

def interpolate_path_points(path, pixel_size, n_interp=20):
    """
    Generate a densely-sampled path by interpolating between waypoints.

    Adds intermediate points between each pair of consecutive waypoints
    for smooth visualization and fine-grained analysis.

    Parameters
    ----------
    path : list of np.ndarray
        Ordered list of [row, col] waypoints.
    pixel_size : float
        Ground sampling distance in meters.
    n_interp : int, optional
        Number of interpolation points per segment (default: 20).

    Returns
    -------
    list of np.ndarray
        Dense list of [row, col] points along the entire path.
    """
    dense_path = []

    for i in range(len(path) - 1):
        p1 = np.array(path[i], dtype=float)
        p2 = np.array(path[i + 1], dtype=float)

        rows = np.linspace(p1[0], p2[0], n_interp, endpoint=(i == len(path) - 2))
        cols = np.linspace(p1[1], p2[1], n_interp, endpoint=(i == len(path) - 2))

        for r, c in zip(rows, cols):
            dense_path.append(np.array([r, c]))

    # Ensure the final goal point is included
    if len(path) > 0:
        final = np.array(path[-1], dtype=float)
        if len(dense_path) == 0 or not np.allclose(dense_path[-1], final):
            dense_path.append(final)

    return dense_path


def optimize_traverse(dem, hazard, illumination, start, goal, pixel_size=20):
    """
    Run the full traverse optimization pipeline using NSGA-II.
    
    Parameters
    ----------
    dem : np.ndarray
        Digital Elevation Model.
    hazard : np.ndarray
        Hazard map.
    illumination : np.ndarray
        Illumination fraction map.
    start : tuple of int
        Start position as (row, col).
    goal : tuple of int
        Goal position as (row, col).
    pixel_size : float, optional
        GSD in meters (default: 20).
        
    Returns
    -------
    dict
        Dictionary containing best path, pareto front, and energy profile.
    """
    from .terrain import compute_slope

    slope = compute_slope(dem, pixel_size)
    cost_surfaces = build_cost_surfaces(slope, hazard, illumination, pixel_size)
    
    pareto_F, pareto_X, problem = run_nsga2(
        cost_surfaces['energy_cost'],
        cost_surfaces['safety_cost'],
        cost_surfaces['shadow_cost'],
        slope,
        illumination,
        start,
        goal,
        pixel_size=pixel_size
    )
    
    path, objectives, energy_list = select_best_path(
        pareto_F, pareto_X, problem, preference='balanced'
    )
    
    cumulative_distance = np.array([pt['distance_m'] for pt in energy_list])
    battery_energy = np.array([pt['energy_wh'] for pt in energy_list])
    illuminated_arr = np.array([pt['illuminated'] for pt in energy_list])
    
    energy_profile = {
        'cumulative_distance': cumulative_distance,
        'battery_energy': battery_energy,
        'illuminated': illuminated_arr,
        'battery_max': config.ROVER_BATTERY_CAPACITY,
    }
    
    return {
        'best_path': path,
        'pareto_F': pareto_F,
        'energy_profile': energy_profile,
    }

