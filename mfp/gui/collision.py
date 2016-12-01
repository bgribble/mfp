#! /usr/bin/env python
'''
collision.py

Test for collision between objects
'''
from math import sqrt

def point_sqr_dist(p_1, p_2):
    p1x, p1y = p_1
    p2x, p2y = p_2

    xdelta = p2x - p1x
    ydelta = p2y - p1y
    return xdelta*xdelta + ydelta*ydelta

def point_dist(p_1, p_2):
    return sqrt(point_sqr_dist(p_1, p_2))

def normal_diff(p_1, p_2):
    p1x, p1y = p_1
    p2x, p2y = p_2

    return min(abs(p1x-p2x) + abs(p1y-p2y), abs(p1x+p2x) + abs(p1y+p2y))

def centroid(poly):
    c_xsum = 0
    c_ysum = 0

    if not poly:
        return None

    for point in poly:
        c_xsum += point[0]
        c_ysum += point[1]

    return (c_xsum / len(poly), c_ysum / len(poly))

def max_dist(poly, ref_point):
    max_sqr_dist = -1

    for point in poly:
        sqr_dist = point_sqr_dist(point, ref_point)
        if sqr_dist > max_sqr_dist:
            max_sqr_dist = sqr_dist

    if max_sqr_dist >= 0:
        return sqrt(max_sqr_dist)
    else:
        return None

def circle_test(poly_1, poly_2):
    centroid_1 = centroid(poly_1)
    centroid_2 = centroid(poly_2)

    center_dist = point_dist(centroid_1, centroid_2)
    sum_max_dist = max_dist(poly_1, centroid_1) + max_dist(poly_2, centroid_2)

    if center_dist > sum_max_dist:
        # polygons could not collide
        return False
    else:
        # polygons might collide
        return True

DISTINCT_THRESH = .00001

def poly_left_normals(poly):
    normals = []
    for segment_num, point_1 in enumerate(poly):
        point_2 = poly[segment_num-1]
        segment_len = point_dist(point_1, point_2)
        if segment_len and segment_len > 0:
            normals.append((
                (point_1[1] - point_2[1])/segment_len,
                (point_2[0] - point_1[0])/segment_len))

    distinct = []
    for normal in normals:
        normal_is_distinct = True
        for d in distinct:
            if normal_diff(normal, d) < DISTINCT_THRESH:
                normal_is_distinct = False
                break
        if normal_is_distinct:
            distinct.append(normal)

    return distinct

def point_dot_product(p_1, p_2):
    return p_1[0] * p_2[0] + p_1[1] * p_2[1]

def poly_project_minmax(poly, normal):
    minval = None
    maxval = None

    for point in poly:
        projval = point_dot_product(point, normal)
        if minval is None or projval < minval:
            minval = projval
        if maxval is None or projval > maxval:
            maxval = projval

    return (minval, maxval)


def collision_check(poly_1, poly_2):
    if not circle_test(poly_1, poly_2):
        return False

    distinct_normals = poly_left_normals(poly_1) + poly_left_normals(poly_2)

    for normal in distinct_normals:
        min_1, max_1 = poly_project_minmax(poly_1, normal)
        min_2, max_2 = poly_project_minmax(poly_2, normal)

        # short-circuit if there is any separating axis
        if min_1 > max_2:
            return False
        elif min_2 > max_1:
            return False

    # no collision-free axis found
    return True








