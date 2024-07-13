import math
def IsPointInScope(point_x,point_y,user_x,user_y,scope):
    dis=math.sqrt((point_x-user_x)*(point_x-user_x)+(point_y-user_y)*(point_y-user_y))

    if dis<scope:
        isIn=True
    else:
        isIn=False
    return isIn




