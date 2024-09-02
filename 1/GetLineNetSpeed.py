from Point2Ras import Point2Ras
import math

def GetLineNetSpeed(X1, Y1, Z1, X2, Y2, Z2, img_X0, img_Y0, cell_width, cell_height, dsm_array, building):
    building_Penetrate_Distance = 0; 
    tree_Penetrate_Distance = 0
    not_Building = 0

    if X1 == X2 and Y1 == Y2:
        return [0,0]

    [startRow,startCol,hj,df] = Point2Ras(X1, Y1, img_X0, img_Y0, cell_width, cell_height,dsm_array)
    [endRow,endCol,hjhg,ghhg] = Point2Ras(X2, Y2, img_X0, img_Y0, cell_width, cell_height,dsm_array)
    Current_Z=Z1

    l = math.sqrt((X1-X2)*(X1-X2)+(Y1-Y2)*(Y1-Y2)+(Z1-Z2)*(Z1-Z2))

    if abs((X1-X2)/cell_width) > abs((Y1-Y2)/cell_height):
        k = (Y2-Y1)/(X2-X1);  # 斜率

        d = abs(endCol-startCol);  # 相差的列数
        if d == 0:
            d = 1
        # 每个栅格平摊的高程和线段长度
        
        divide_Z = (Z1-Z2)/d
        divide_S = l/d

        if endCol > startCol:
            for i in range(d):
                tmpCol = startCol+i
                tmpRow = math.floor(startRow-i*k)
                
                Current_Z = Current_Z - divide_Z
                # 如果DSM的栅格的高度大于或等于当前栅格的高度，可以认为线段通过了DSM该栅格的部分
                if dsm_array[tmpRow][tmpCol] >= Current_Z:
                    # if building[tmpRow][tmpCol]!=not_Building:
                    #     building_Penetrate_Distance = building_Penetrate_Distance+ divide_S
                    # else:
                    tree_Penetrate_Distance = tree_Penetrate_Distance+divide_S
                
        else:
            for i in range(d):
                tmpCol = startCol-i
                tmpRow = math.floor(startRow+i*k)

                Current_Z = Current_Z - divide_Z

                if dsm_array[tmpRow][tmpCol] >= Current_Z:
                    # if building[tmpRow][tmpCol]!=not_Building:
                    #     building_Penetrate_Distance = building_Penetrate_Distance+ divide_S
                    # else:
                    tree_Penetrate_Distance = tree_Penetrate_Distance+divide_S
                    
    else:
        k = (X2-X1)/(Y2-Y1)  # 斜率

        d = abs(endRow-startRow)  # 相差的行数
        if d == 0:
            d = 1
        # 每个栅格平摊的高程和线段长度
        divide_Z = (Z1-Z2)/d
        divide_S = l/d
        
        if endRow > startRow:
            for i in range(d):
                tmpRow = startRow+i
                tmpCol = math.floor(startCol-i*k)

                Current_Z = Current_Z - divide_Z

                if dsm_array[tmpRow][tmpCol] >= Current_Z:
                    # if building[tmpRow][tmpCol]!=not_Building:
                    #     building_Penetrate_Distance = building_Penetrate_Distance+divide_S
                    # else:
                    tree_Penetrate_Distance = tree_Penetrate_Distance+divide_S
                
        else:
            for i in range(d):
                tmpRow = startRow-i
                tmpCol = math.floor(startCol+i*k)

                Current_Z = Current_Z - divide_Z

                if dsm_array[tmpRow][tmpCol] >= Current_Z:
                    # if building[tmpRow][tmpCol]!=not_Building:
                    #     building_Penetrate_Distance =building_Penetrate_Distance+ divide_S
                    # else:
                    tree_Penetrate_Distance =tree_Penetrate_Distance+ divide_S

             
    arr= [building_Penetrate_Distance,tree_Penetrate_Distance]
    return arr


def GetLineNetSpeed(X1, Y1, Z1, X2, Y2, Z2, img_X0, img_Y0, cell_width, cell_height, dsm_array, building):
    building_Penetrate_Distance = 0
    tree_Penetrate_Distance = 0
    not_Building = 0

    if X1 == X2 and Y1 == Y2:
        return [0, 0]

    [startRow, startCol, hj, df] = Point2Ras(X1, Y1, img_X0, img_Y0, cell_width, cell_height, dsm_array)
    [endRow, endCol, hjhg, ghhg] = Point2Ras(X2, Y2, img_X0, img_Y0, cell_width, cell_height, dsm_array)
    Current_Z = Z1

    l = math.sqrt((X1 - X2) * (X1 - X2) + (Y1 - Y2) * (Y1 - Y2) + (Z1 - Z2) * (Z1 - Z2))

    if abs((X1 - X2) / cell_width) > abs((Y1 - Y2) / cell_height):
        k = (Y2 - Y1) / (X2 - X1);  # 斜率

        d = abs(endCol - startCol);  # 相差的列数
        if d == 0:
            d = 1
        # 每个栅格平摊的高程和线段长度

        divide_Z = (Z1 - Z2) / d
        divide_S = l / d

        if endCol > startCol:
            for i in range(d):
                tmpCol = startCol + i
                tmpRow = math.floor(startRow - i * k)

                Current_Z = Current_Z - divide_Z
                # 如果DSM的栅格的高度大于或等于当前栅格的高度，可以认为线段通过了DSM该栅格的部分
                if dsm_array[tmpRow][tmpCol] >= Current_Z:
                    tree_Penetrate_Distance = tree_Penetrate_Distance + divide_S

        else:
            for i in range(d):
                tmpCol = startCol - i
                tmpRow = math.floor(startRow + i * k)

                Current_Z = Current_Z - divide_Z

                if dsm_array[tmpRow][tmpCol] >= Current_Z:
                    # if building[tmpRow][tmpCol]!=not_Building:
                    #     building_Penetrate_Distance = building_Penetrate_Distance+ divide_S
                    # else:
                    tree_Penetrate_Distance = tree_Penetrate_Distance + divide_S

    else:
        k = (X2 - X1) / (Y2 - Y1)  # 斜率

        d = abs(endRow - startRow)  # 相差的行数
        if d == 0:
            d = 1
        # 每个栅格平摊的高程和线段长度
        divide_Z = (Z1 - Z2) / d
        divide_S = l / d

        if endRow > startRow:
            for i in range(d):
                tmpRow = startRow + i
                tmpCol = math.floor(startCol - i * k)

                Current_Z = Current_Z - divide_Z

                if dsm_array[tmpRow][tmpCol] >= Current_Z:
                    # if building[tmpRow][tmpCol]!=not_Building:
                    #     building_Penetrate_Distance = building_Penetrate_Distance+divide_S
                    # else:
                    tree_Penetrate_Distance = tree_Penetrate_Distance + divide_S

        else:
            for i in range(d):
                tmpRow = startRow - i
                tmpCol = math.floor(startCol + i * k)

                Current_Z = Current_Z - divide_Z

                if dsm_array[tmpRow][tmpCol] >= Current_Z:
                    # if building[tmpRow][tmpCol]!=not_Building:
                    #     building_Penetrate_Distance =building_Penetrate_Distance+ divide_S
                    # else:
                    tree_Penetrate_Distance = tree_Penetrate_Distance + divide_S

    arr = [building_Penetrate_Distance, tree_Penetrate_Distance]
    return arr

