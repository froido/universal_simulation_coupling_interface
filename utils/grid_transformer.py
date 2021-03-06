import logging as log
from utils.grid import Grid
from scipy.spatial import KDTree  # nearest neighbor search
import numpy
import matplotlib.pyplot as plt  # visualisation of transformation validation
import sys


class GridTransformer:
    """ Grid Transformer is used to transform in a Grid object saved values from one Grid object to another. At the
        at the moment the two Grid objects need to have the same origin. Otherwise the data transformation will lead to
        unpredictable results.
    """

    def __init__(self):
        self.log = log.getLogger(self.__class__.__name__)

        self.grids = {}
        self.transformation = []

    def __str__(self):
        string = f'{self.__class__.__name__} contains {len(self.grids)} grids'
        if len(self.grids) > 0:
            string = f'{string}:'

            for key in self.grids.keys():
                string = f'{string} {key}'

                if self.grids[key]['transform']:
                    string = f'{string} (transformation mapping available);'
                else:
                    string = f'{string};'

        return string

    def add_grid(self, grid: Grid, grid_name: str):
        """
        Add a grid to the instance.

        Args:
            grid: Grid to be added.
            grid_name: Name of the grid in the instance.

        Returns:
            boolean: true on success
        """

        if not isinstance(grid, Grid):
            raise TypeError(f'Input parameter grid must be of type Grid, is {type(grid)}.')
        if not isinstance(grid_name, str):
            raise TypeError(f'Input parameter grid_name must be of type Grid, is {type(grid_name)}.')

        if grid_name in self.grids:
            raise KeyError(f'Grid with name {grid_name} already exists. Please use .update_grid() instead.')

        self.grids[grid_name] = {}
        self.grids[grid_name]['transform'] = {}
        self.grids[grid_name]['grid'] = grid

        self.log.debug(f'Grid added successfully. ({grid_name})')
        return True

    def update_grid(self, grid: Grid, grid_name: str):
        """
            Update a grid in instance. The available grid will be deleted and replaced by the new grid.
        Args:
            grid: Grid to be added.
            grid_name: Name of the grid in the instance.

        Returns:
            boolean: true on success
        """

        if not isinstance(grid, Grid):
            raise TypeError(f'Input parameter grid must be of type Grid, is {type(grid)}.')
        if not isinstance(grid_name, str):
            raise TypeError(f'Input parameter grid_name must be of type string, is {type(grid_name)}.')

        if grid_name not in self.grids:
            raise KeyError(f'Grid with name {grid_name} does not exists. Please use .add_grid() instead.')

        del self.grids['grid_name']
        self.log.debug(f'Grid deleted for update. ({grid_name})')

        self.add_grid(grid, grid_name)

        return True

    def find_nearest_neighbors(self, grid_name_1: str, grid_name_2: str, neighbors_quantity: int = 10,
                               distance_max: float = numpy.inf):
        """
        To transfer the data from one grid to another a modified nearest neighbor approach is used. This method takes
        the coordinates of each point in two grids and searches for nearest neighbors. Thereby the first grid is the
        source and the second grid is the target, means that for each node in the target neighbors in the source are
        found. The amount of neighbors used for each node is set with the optional parameter neighbors_quantity.
        Even if the density of neighbor nodes all over the grid seems to be good, there are some minor problems at
        the edges, especially at the corners. In the corners the distance to the neighbors vary very much. The
        parameter distance_max helps with this issue, as one can set a maximum distance between the node and a
        neighbor. The results are stored in the instance and are used by the function .transition() to transfer
        the data from one grid to another. This saves time, as the fitting of the grids is done only once.

        Args:
            grid_name_1 (str): Name of the first grid (source)
            grid_name_2 (str): Name of the second grid (target)
            neighbors_quantity (int, optional): Number of neighbors to use
            distance_max (int, optional): maximum distance between node and neighbors

        Returns:
            boolean: true on success
        """

        # Check input parameters
        if not isinstance(grid_name_1, str):
            raise TypeError(f'Input parameter grid_name_1 must be of type string, is {type(grid_name_1)}.')
        if not isinstance(grid_name_2, str):
            raise TypeError(f'Input parameter grid_name_2 must be of type string, is {type(grid_name_2)}.')
        if not isinstance(neighbors_quantity, int):
            raise TypeError(f'Input parameter neighbors_quantity must be of type integer, '
                            f'is {type(neighbors_quantity)}.')
        if not isinstance(distance_max, int) and not isinstance(distance_max, float) and distance_max != numpy.inf:
            raise TypeError(f'Input parameter distance_max must be of type integer or float, is {type(distance_max)}.')

        # Check if grids exist
        if grid_name_1 not in self.grids:
            raise KeyError(f'Grid with name "{grid_name_1}" not found in {self.grids.keys()}')

        if grid_name_2 not in self.grids:
            raise KeyError(f'Grid with name "{grid_name_2}" not found in {self.grids.keys()}')

        self.log.debug(f'Start identifying nearest neighbors in {grid_name_1} for {grid_name_2}: '
                       f'neighbors={neighbors_quantity}; max distance={distance_max};')

        # Transform grids to arrays containing the coordinates to use KDTree
        grid_1_coordinates = self.grids[grid_name_1]['grid'].get_coordinates_array()
        grid_1_nodes = list(self.grids[grid_name_1]['grid'].nodes.keys())
        grid_2_coordinates = self.grids[grid_name_2]['grid'].get_coordinates_array()
        grid_2_nodes = list(self.grids[grid_name_2]['grid'].nodes.keys())

        # Numpy is used to get max and min values, because min() and max() deliver wrong values
        x_min_1 = numpy.amin(a=grid_1_coordinates, axis=0)[0]
        y_min_1 = numpy.amin(a=grid_1_coordinates, axis=0)[1]
        z_min_1 = numpy.amin(a=grid_1_coordinates, axis=0)[2]

        x_max_1 = numpy.amax(a=grid_1_coordinates, axis=0)[0]
        y_max_1 = numpy.amax(a=grid_1_coordinates, axis=0)[1]
        z_max_1 = numpy.amax(a=grid_1_coordinates, axis=0)[2]

        x_min_2 = numpy.amin(a=grid_2_coordinates, axis=0)[0]
        y_min_2 = numpy.amin(a=grid_2_coordinates, axis=0)[1]
        z_min_2 = numpy.amin(a=grid_2_coordinates, axis=0)[2]

        x_max_2 = numpy.amax(a=grid_2_coordinates, axis=0)[0]
        y_max_2 = numpy.amax(a=grid_2_coordinates, axis=0)[1]
        z_max_2 = numpy.amax(a=grid_2_coordinates, axis=0)[2]

        self.log.debug(f'Dimensions of {grid_name_1}:')
        self.log.debug(f'\t (x): {x_min_1} to {x_max_1}')
        self.log.debug(f'\t (y): {y_min_1} to {y_max_1}')
        self.log.debug(f'\t (z): {z_min_1} to {z_max_1}')

        self.log.debug(f'Dimensions of {grid_name_2}:')
        self.log.debug(f'\t (x): {x_min_2} to {x_max_2}')
        self.log.debug(f'\t (y): {y_min_2} to {y_max_2}')
        self.log.debug(f'\t (z): {z_min_2} to {z_max_2}')

        # Check if grids are overlapping. If not throw an error as unpredictable errors may occur.
        if not (x_min_1 <= x_max_2 and x_max_1 >= x_min_2):
            self.log.error("Given grids are not overlapping in x direction. This may lead to unpredictable results.")
            raise ValueError("Given grids are not overlapping in x direction. This may lead to unpredictable results.")
        if not (y_min_1 <= y_max_2 and y_max_1 >= y_min_2):
            self.log.error("Given grids are not overlapping in y direction. This may lead to unpredictable results.")
            raise ValueError("Given grids are not overlapping in y direction. This may lead to unpredictable results.")
        if not (z_min_1 <= z_max_2 and z_max_1 >= z_min_2):
            self.log.error("Given grids are not overlapping in z direction. This may lead to unpredictable results.")
            raise ValueError("Given grids are not overlapping in z direction. This may lead to unpredictable results.")

        # Check for nearest neighbor
        self.log.debug(f'set initiate "grid_1_coordinates" as KDTree')
        tree = KDTree(numpy.float32(grid_1_coordinates))

        # Check whether a 32bit oder 64bit version of python is used. If a 32bit version is used, the maximum memory
        # is limited to 4 gb which might be to low. In these cases, the nearest neighbor search will be split up
        # in smaller arrays and merged after.

        if sys.maxsize > 2 ** 32 and 1 == 2:
            self.log.debug(f'tree.query on KDTree(grid_1_coordinates) and grid_2_coordinates')
            dist, points = tree.query(numpy.float32(grid_2_coordinates), neighbors_quantity, distance_max)
        else:
            # Using a 32 bit version of python. Splitting up in
            splits = 10
            coordinates_split = numpy.array_split(numpy.float32(grid_2_coordinates), splits)

            dist = []
            points = []
            i = 0

            for arr in coordinates_split:
                i += 1

                self.log.debug(f'tree.query on KDTree(grid_1_coordinates) and grid_2_coordinates [{i}/{splits}]')
                dist_tmp, points_tmp = tree.query(x=numpy.float32(arr),
                                                  k=neighbors_quantity,
                                                  distance_upper_bound=distance_max)
                # dist.append(dist_tmp)
                # points.append(points_tmp)
                if i == 1:
                    points = points_tmp
                    dist = dist_tmp
                else:
                    points = numpy.concatenate((points, points_tmp), axis=0)
                    dist = numpy.concatenate((dist, dist_tmp), axis=0)

        transform_dict = {}
        count_lonely_nodes = 0

        # Iterate through the results to put them into a dictionary. Additionally the maximum distance will be
        # checked.
        self.log.debug(f'Check results from .query and save in dictionary')
        for i in range(len(dist)):
            # Initialize the dictionary entry for a node
            transform_dict[grid_2_nodes[i]] = []

            # Loop through all neighbors and check distance
            # Distinguish between only one neighbor and a couple of neighbors.
            if not len(dist.shape) == 1:  # Only one neighbor has been taken into account
                for k in range(len(dist[i])):
                    node = grid_1_nodes[points[i][k]-1]
                    distance = dist[i][k]

                    # Easily just continue when the maximum distance is exceeded
                    if distance_max != numpy.inf:
                        if distance > distance_max:
                            continue

                    # Append node and distance to list in dictionary
                    transform_dict[grid_2_nodes[i]].append({'node_number': node, 'distance': distance})
            else:  # A couple of neighbors have been taken into account
                node = grid_1_nodes[points[i] - 1]
                distance = dist[i]

                # Easily just continue when the maximum distance is exceeded
                if distance_max != numpy.inf:
                    if distance > distance_max:
                        continue

                # Append node and distance to list in dictionary
                transform_dict[grid_2_nodes[i]].append({'node_number': node, 'distance': distance})

            # Check if at least one neighbor was found according to the maximum distance. Otherwise exit method and
            # and log an error.
            if len(transform_dict[grid_2_nodes[i]]) == 0:
                self.log.debug(f'No neighbor found for node {grid_2_nodes[i]} in {grid_name_2}')
                count_lonely_nodes += 1
                transform_dict[grid_2_nodes[i]] = None

        if count_lonely_nodes > 0:
            self.log.warning(f'No neighbors found for {count_lonely_nodes} nodes in {grid_name_1} for {grid_name_2} in '
                             f'a range of {distance_max}.')
        self.grids[grid_name_2]['transform'][grid_name_1] = transform_dict
        self.log.info(f'Nearest neighbors in {grid_name_1} found for {grid_name_2}')

        return True

    def transition(self, src_grid_name, value_name, target_grid_name):
        """
        The values (value_name) of the source grid (src_grid_name) are transferred to the target grid
        (target_grid_name). For the transfer a modified nearest neighbor approach is used (see
        .find_nearest_neighbors()). The relevant neighbors and their distance to the corresponding node are stored.
        This function used the distance from the node to calculate a weighted average.

        Args:
            src_grid_name (str): Name of the source grid
            value_name (str): Name of the values in source grid
            target_grid_name (str): Name of the target grid

        Returns:
            boolean: true on success
        """
        # Check input parameters
        if not isinstance(src_grid_name, str):
            raise TypeError(f'Input parameter src_grid_name must be of type string, is {type(src_grid_name)}.')
        if not isinstance(value_name, str):
            raise TypeError(f'Input parameter value_name must be of type string, is {type(value_name)}.')
        if not isinstance(target_grid_name, str):
            raise TypeError(f'Input parameter target_grid_name must be of type string, is {type(target_grid_name)}.')

        # Check if grids exist
        if src_grid_name not in self.grids:
            raise KeyError(f'Grid with name "{src_grid_name}" not found in {self.grids.keys()}')
        if target_grid_name not in self.grids:
            raise KeyError(f'Grid with name "{target_grid_name}" not found in {self.grids.keys()}')

        # Check if value exists in src_grid
        src_grid = self.grids[src_grid_name]
        target_grid = self.grids[target_grid_name]
        if not src_grid['grid'].get_node_values(value_name):
            raise KeyError(f'Value_name ({value_name}) not found in nodes.')

        src_values = src_grid['grid'].get_node_values(value_name)

        # Check if neighbors for this combination have been set
        if src_grid_name not in target_grid['transform']:
            raise KeyError(f'No transformation matrix has been found for {src_grid_name} to {target_grid_name}. '
                           f'Before transformation neighbors have to be found.')

        for node, node_dict in target_grid['transform'][src_grid_name].items():
            sum_distance = 0
            factor = 0

            if node_dict:
                # Calculating of the weighted average
                # Take into account if a value has the distance of 0. In this case this particular value should be
                # used instead of creating a weighted average.
                result = None

                for item in node_dict:
                    distance = item['distance']
                    node_number = item['node_number']
                    value = src_values[node_number]

                    # Check if the actual node has distance of 0. If so set value as final result and stop looping.
                    # sum_distance will be set to zero to show, that a perfect fitting node has been found.
                    if distance == 0:
                        result = value
                        sum_distance = 0
                        break
                    else:
                        sum_distance += 1 / distance
                        factor += value * 1 / distance

                # sum_distance is 0 when a perfect match has been found for the specific node
                if not sum_distance == 0:
                    result = factor / sum_distance

                target_grid['grid'].nodes[node].set_value(value_name, result)
            else:
                target_grid['grid'].nodes[node].set_value(value_name, numpy.nan)

        # Check if a value is set for all nodes
        target_grid['grid'].check_value_set_completeness(value_name)

        self.log.info(f'Transition for {value_name} from {src_grid_name} to {target_grid_name} successful')
        return True

    def nearest_neighbors_stat(self, grid_name):
        """
        The mentioned grid and the established connections to other grids are (statistically) examined
        in this function and the results are output in the log.

        Args:
            grid_name: Name of the grid, to be examined

        Returns:
            boolean: true on success
        """
        # Check input parameters
        if not isinstance(grid_name, str):
            raise TypeError(f'Input parameter grid_name must be of type string, is {type(grid_name)}.')

        # Check if grids exist
        if grid_name not in self.grids:
            raise KeyError(f'Grid with name "{grid_name}" not found in {self.grids.keys()}')

        self.log.info(f'Statistics for: {grid_name}')
        self.log.info(f'Nodes: {len(self.grids[grid_name]["grid"])}')

        for grid, node_list in self.grids[grid_name]['transform'].items():
            distances = []
            count_lonely_nodes = 0

            if node_list:
                for node, node_dict in node_list.items():
                    if node_dict:
                        for item in node_dict:
                            if item['distance'] > 0:
                                distances.append(item['distance'])
                            else:
                                count_lonely_nodes += 1
                    else:
                        count_lonely_nodes += 1
            else:
                count_lonely_nodes += 1

            distances = numpy.array(distances)

            self.log.info(f'Neighborhood to: {grid}')
            self.log.info(f'\t Number of neighbors in total: {len(distances)}')
            self.log.info(f'\t Mean: {numpy.nanmean(distances)}')
            self.log.info(f'\t Std. Deviation: {numpy.nanstd(distances)}')
            self.log.info(f'\t Min: {numpy.ndarray.min(distances)}')
            self.log.info(f'\t Max: {numpy.ndarray.max(distances)}')
            self.log.info(f'\t Lonely: {count_lonely_nodes}')

        self.log.info(f'End of Statistics')

        return True

    def transformation_validation(self, src_grid_name, value_name, target_grid_name):
        """ Validating the method of transferring data from one grid to another. There are two different grids (one is
        maybe coarser then the other). The information within the grid is transferred from one grid to the other and
        backwards. The transformation form a (e.g. finer) to b (e.g. coarser) includes data loss. The amount of loss
        is influenced by the difference of the grid resolution. The following code transforms the data from the
        source grid (src_grid_name) to the target grid (target_grid_name) and back to the source grid.
        The data loss will be shown by checking the difference 'source - source_re'. As a result one
        get a min/max-value, mean and standard deviation to check whether the data loss is acceptable. In addition
        a plot is created to be able to make a visual check.

        Parameters:
            src_grid_name (str): name of source grid
            target_grid_name (str): name of target grid
            value_name (str): name of values in source grid

        Returns:
            None
        """
        # Check input parameters
        if not isinstance(src_grid_name, str):
            raise TypeError(f'Input parameter src_grid_name must be of type string, is {type(src_grid_name)}.')
        if not isinstance(value_name, str):
            raise TypeError(f'Input parameter value_name must be of type string, is {type(value_name)}.')
        if not isinstance(target_grid_name, str):
            raise TypeError(f'Input parameter target_grid_name must be of type string, is {type(target_grid_name)}.')

        try:
            # Data transformation from input_mesh to output_mesh
            # output = mesh_transformation(input_mesh, output_mesh, input_data)
            src_grid_begin = self.grids[src_grid_name]['grid']
            data_begin = numpy.array(list(src_grid_begin.get_node_values(value_name).values()))
            target_grid = self.grids[target_grid_name]['grid']

            self.transition(src_grid_name, value_name, target_grid_name)
            self.transition(target_grid_name, value_name, src_grid_name)

            src_grid_end = self.grids[src_grid_name]['grid']
            data_end = numpy.array(list(src_grid_end.get_node_values(value_name).values()))

            self.log.info('Array output: input after retransformation')

            # Calculating mean and standard deviation
            # For statistics the absolute values of fine_new_data are used
            diff = numpy.absolute(data_begin - data_end)

            self.log.info(f'Statistics:')
            self.log.info(f'Source Grid: {src_grid_begin}')
            self.log.info(f'Target Grid: {target_grid}')
            self.log.info(f'After transformation:')
            self.log.info(f'NaN-Values: {sum(numpy.isnan(data_end))}')
            self.log.info(f'Mean: {numpy.nanmean(diff)}')
            self.log.info(f'Std. Deviation: {numpy.nanstd(diff)}')
            self.log.info(f'Mean Match: {numpy.nanmean(numpy.absolute(data_end / data_begin))}')
            self.log.info(f'Std. Deviation: {numpy.nanstd(numpy.absolute(data_end / data_begin))}')
            self.log.info(f'Worst Match: {numpy.ndarray.max(numpy.absolute(data_end / data_begin))}')
            self.log.info(f'Worst Match: {numpy.ndarray.min(numpy.absolute(data_end / data_begin))}')

            # # Generating the visual output
            # self.log.info('Plotting 2d data sets to visually comparison')
            # mpl_fig = plt.figure()
            # ax1 = mpl_fig.add_subplot(221)
            # cb1 = ax1.scatter(list(src_grid_begin.get_node_values('x_coordinate').values()),
            #                   list(src_grid_begin.get_node_values('y_coordinate').values()),
            #                   s=1, c=data_begin, cmap=plt.cm.get_cmap('RdBu'))
            # plt.colorbar(cb1, ax=ax1)
            # ax1.set_title('input (original)')
            # ax2 = mpl_fig.add_subplot(222)
            # cb2 = ax2.scatter(list(target_grid.get_node_values('x_coordinate').values()),
            #                   list(target_grid.get_node_values('y_coordinate').values()),
            #                   s=1, c=list(target_grid.get_node_values(value_name).values()),
            #                   cmap=plt.cm.get_cmap('RdBu'))
            # plt.colorbar(cb2, ax=ax2)
            # ax2.set_title('output')
            #
            # ax3 = mpl_fig.add_subplot(223)
            # cb3 = ax3.scatter(list(src_grid_end.get_node_values('x_coordinate').values()),
            #                   list(src_grid_end.get_node_values('y_coordinate').values()),
            #                   s=1, c=data_end, cmap=plt.cm.get_cmap('RdBu'))
            # plt.colorbar(cb3, ax=ax3)
            # ax3.set_title('input (retransformation)')
            #
            # # function to show the plot
            # plt.show()
            # #########################################################################################
            # Generating the visual output
            self.log.info('Plotting 3d data sets to visually comparison')
            mpl_fig = plt.figure()
            ax1 = mpl_fig.add_subplot(221)
            cb1 = ax1.scatter(list(src_grid_begin.get_node_values('x_coordinate').values()),
                              list(src_grid_begin.get_node_values('y_coordinate').values()),
                              list(src_grid_begin.get_node_values('z_coordinate').values()),
                              # s=1, c=data_begin, cmap=plt.cm.get_cmap('RdBu'))
                              c=data_begin, cmap=plt.cm.get_cmap('RdBu'))
            plt.colorbar(cb1, ax=ax1)
            ax1.set_title('input (original)')
            ax2 = mpl_fig.add_subplot(222)
            cb2 = ax2.scatter(list(target_grid.get_node_values('x_coordinate').values()),
                              list(target_grid.get_node_values('y_coordinate').values()),
                              list(target_grid.get_node_values('z_coordinate').values()),
                              # s=1, c=list(target_grid.get_node_values(value_name).values()),
                              c=list(target_grid.get_node_values(value_name).values()),
                              cmap=plt.cm.get_cmap('RdBu'))
            plt.colorbar(cb2, ax=ax2)
            ax2.set_title('output')

            ax3 = mpl_fig.add_subplot(223)
            cb3 = ax3.scatter(list(src_grid_end.get_node_values('x_coordinate').values()),
                              list(src_grid_end.get_node_values('y_coordinate').values()),
                              list(src_grid_end.get_node_values('z_coordinate').values()),
                              # s=1, c=data_end, cmap=plt.cm.get_cmap('RdBu'))
                              c=data_end, cmap=plt.cm.get_cmap('RdBu'))
            plt.colorbar(cb3, ax=ax3)
            ax3.set_title('input (retransformation)')

            # function to show the plot
            plt.show()

            return True

        except Exception as err:
            self.log.critical('Execution aborted! [%s]', str(err))
            return False
