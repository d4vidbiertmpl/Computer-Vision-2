from scipy import spatial
import numpy as np
import open3d as o3d
import scipy.io


def calc_IPC(base_point_cloud, target_point_cloud, base_point_cloud_normal=None, target_point_cloud_normal=None):
    '''
    Performs the ICP algorithm ...
    :param base_point_cloud:
    :param target_point_cloud:
    :param base_point_cloud_normal:
    :param target_point_cloud_normal:
    :return:
    '''
    if base_point_cloud_normal is not None:
        A1, A1_normal = cleanInput(base_point_cloud, base_point_cloud_normal)
        A2, A2_normal = cleanInput(target_point_cloud, target_point_cloud_normal)

        print(A1.shape, A1_normal.shape)
        print(A2.shape, A2_normal.shape)

    # If no normals are specified => test dummy data is loaded
    else:
        A1 = base_point_cloud
        A2 = target_point_cloud

    final_R = np.identity(3)
    final_t = np.zeros(3)

    # dummy values for initialization
    current_rms, old_RMS = 0.0, 200.0
    # Iterate until RMS is unchanged
    while not (np.isclose(current_rms, old_RMS, atol=0.015)):
        old_RMS = current_rms
        # 1. For each point in the base set (A1), find with brute force the best matching point in the target point set (A2)
        matching_A2 = get_matching_targets(A1, A2)

        # Calculate current error
        current_rms = calc_rms(A1, matching_A2)
        print("Current RMS", current_rms)

        # 2. Refine the rotation matrix R and translation vector t using using SVD
        R, t = compute_SVD(A1, matching_A2)

        # Visualization - We do this before updating to visualize the initial setting
        # visualize_source_and_target(A1, A2)

        # Updating the base point cloud
        A1 = np.dot(A1, R.T) + t

        # update overall R and t
        final_R = R.dot(final_R)
        final_t = R.dot(final_t) + t

    # Final Visualization
    # visualize_source_and_target(A1, A2)

    # Test final transformation matrix
    # A1_test, A1_normal = cleanInput(base_point_cloud, base_point_cloud_normal)
    # test_A1 = np.dot(A1_test, final_R.T) + final_t
    # visualize_source_and_target(test_A1, A2)

    return final_R, final_t


def cleanInput(point_cloud, point_cloud_normal):
    '''
    Filters out all point where the normal is NaN and the Z-value is smaller 1.

    :param point_cloud: The raw point clouds
    :param point_cloud_normal: The normals corresponding to the point cloud
    :return: cleaned point cloud and normals
    '''
    # Keep indices where row not Nan
    el_not_nan = ~np.isnan(point_cloud_normal)
    rows_not_nan = np.logical_or(el_not_nan[:, 0], el_not_nan[:, 1], el_not_nan[:, 2])

    # points shallow enough to survice (depth < 1)
    shallow_rows = point_cloud[:, 2] < 1
    rows_to_keep = np.logical_and(rows_not_nan, shallow_rows)

    A = point_cloud[rows_to_keep, :]
    A_normal = point_cloud_normal[rows_to_keep, :]

    return A, A_normal


def calc_rms(A1, A2):
    return np.sqrt(np.mean(np.sum(np.square(A1 - A2))))


def get_matching_targets(base_point_cloud, target_point_cloud):
    '''

    Finds the closest point in the target point cloud for each base point cloud member.
    Note: Since the brute force approach was not feasible with our hardware, we build up a tree. This is inspired by
    the following stack overflow article: https://stackoverflow.com/questions/32446703/find-closest-vector-from-a-list-of-vectors-python

    '''

    tree = spatial.KDTree(target_point_cloud)
    min_distances, matching_indices = tree.query(base_point_cloud)
    return target_point_cloud[matching_indices, :]


def compute_SVD(A1, A2):
    """
    After: https://igl.ethz.ch/projects/ARAP/svd_rot.pdf
    :param A1: Base point cloud
    :param A2: Target point cloud
    :return: Rotation matrix and translation vector
    """

    centroid_A1 = np.mean(A1, axis=0)
    centroid_A2 = np.mean(A2, axis=0)

    A1_centered = A1 - centroid_A1
    A2_centered = A2 - centroid_A2

    # W = np.eye(A1_centered.shape[0])
    # S = A1_centered.T.dot(W).dot(A2_centered)
    S = A1_centered.T.dot(A2_centered)
    U, _, V = np.linalg.svd(S)

    ident = np.identity(U.shape[0])
    ident[-1, -1] = np.linalg.det(V.T.dot(U))

    R = V.T.dot(ident).dot(U.T)
    t = centroid_A2 - R.dot(centroid_A1)

    return R, t


def visualize_source_and_target(A1, A2):
    '''

    :param A1: Base point cloud
    :param A2: Target point cloud
    :return: Shows both point cloud in one plot
    '''
    point_cloud_source = o3d.PointCloud()
    point_cloud_target = o3d.PointCloud()
    point_cloud_source.points = o3d.Vector3dVector(A1)
    point_cloud_target.points = o3d.Vector3dVector(A2)
    o3d.draw_geometries([point_cloud_source, point_cloud_target])
