import math
import shutil
from osgeo import gdal
from osgeo import osr
import cv2
import numpy as np
import os

import time

from tqdm import *
# device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# 3屏电脑：D:/apache-tomcat-8.5.99/webapps/tiles
outputTilesPath = 'D:/apache-tomcat-8.5.99/webapps/tiles'
outputTifFileName = 'C:/workspace/cesiumChooseDot/server/output.tif'
tifFileDir = "C:/workspace/cesiumChooseDot/server/data/"
resultFileDir = "C:/workspace/cesiumChooseDot/server/analyse/"
# 自己测试
# outputTilesPath = 'C:/tools/apache-tomcat-8.5.82/webapps1/tiles'
# outputTifFileName = 'C:/workspace/cesiumChooseDot/server/output.tif'
# tifFileDir = "C:/workspace/lbc/txc/0226/"

WORKER_NUM = 4
cmax = 40  # 理论最大网速
gamma = 0.5  # 衰减因子
def select_indices(imin, imax, jmin, jmax, num_points):
    # 生成均匀分布的整数索引
    indices_i = np.linspace(imin, imax, num_points, dtype=int)
    indices_j = np.linspace(jmin, jmax, num_points, dtype=int)
    indices = np.array(np.meshgrid(indices_i, indices_j)).T.reshape(-1, 2)
    return indices

class deploy():
    #一张tif的大小为3000*4000左右的栅格，计算每个栅格的网速作为通信态势
    def __init__(self, tifname, radioposs):
        # tifname = r"C:\workspace\cesiumChooseDot\server\data\guangxi_guilin_dsmWGS84_5.tif"

        self.dsmPath = tifname
        self.timemask = np.load('timesmask.npy')
        #读入tif
        dsm_gdal = gdal.Open(tifname)
        dsm_array = dsm_gdal.GetRasterBand(1).ReadAsArray()

        geotransform = dsm_gdal.GetGeoTransform()  # 图像得仿射变换参数
        self.imgWidth = dsm_gdal.RasterXSize  # 图像列数
        self.imgHeight = dsm_gdal.RasterYSize  # 图像行数
        self.size = np.array([self.imgHeight, self.imgWidth])

        if "WGS84" in tifname:
            source_srs = osr.SpatialReference()
            source_srs.ImportFromEPSG(4326)  # WGS84
            target_srs = osr.SpatialReference()
            target_srs.ImportFromEPSG(4546)  # UTM Zone 10N
            transform = osr.CoordinateTransformation(source_srs, target_srs)
            leftUpLon = geotransform[0]  # 左上角横坐标
            leftUpLat = geotransform[3]  # 左上角纵坐标
            cellDegreeResolutionX = geotransform[1]
            cellDegreeResolutionY = -geotransform[5]
            rightDownLon = leftUpLon + self.imgWidth * cellDegreeResolutionX
            rightDownLat = leftUpLat - self.imgHeight *cellDegreeResolutionY
            self.imgLeftUpY, self.imgLeftUpX, _ = transform.TransformPoint(leftUpLat, leftUpLon)
            self.imgRightDownY, self.imgRightDownX, _ = transform.TransformPoint(rightDownLat, rightDownLon)
            self.imgCellWidth = (self.imgRightDownX - self.imgLeftUpX) / self.imgWidth
            self.imgCellHeight = (self.imgLeftUpY - self.imgRightDownY) / self.imgHeight
        else:
            self.imgCellWidth = geotransform[1]  # 像元宽度
            self.imgCellHeight = -geotransform[5]  # 像元高度,需要加一个负号
            self.imgLeftUpX = geotransform[0]  # 左上角横坐标
            self.imgLeftUpY = geotransform[3]  # 左上角纵坐标
            self.imgRightDownX = self.imgLeftUpX + self.imgWidth * self.imgCellWidth + self.imgHeight * geotransform[2]  # 右下角横坐标
            self.imgRightDownY = self.imgLeftUpY - self.imgHeight * self.imgCellHeight + self.imgWidth * geotransform[4]  # 右下角纵坐标
        # 保存dsm句柄
        self.imgArray = dsm_array
        self.imgGdal = dsm_gdal
        # 保存radiopos
        self.radioposs = radioposs
        self.radioposMeter = []
        self.radioposGrid = []
        for radio in radioposs:
            meterpos = self.latlng2meter(radio) #米转换是对的，仿射变换参数是wgs84下的经纬度的值
            meterpos = [meterpos[0], meterpos[1], radio[2]]
            gridpos  = self.meterPos2GridPos(meterpos[0], meterpos[1], radio[2])
            self.radioposGrid.append(gridpos)
            self.radioposMeter.append(meterpos)

        print("radio lon,lat:",self.radioposs)
        print("radio meter:",self.radioposMeter)
        print("radio grid:",self.radioposGrid)

    def meter2Grid(self, X, Y):
        i = math.floor((self.imgLeftUpY - Y) / self.imgCellHeight) + 1
        j = math.floor((X - self.imgLeftUpX) / self.imgCellWidth) + 1
        i = max(min(i, self.size[0] - 1), 0)
        j = max(min(j, self.size[1] - 1), 0)
        return i, j

    def meterPos2GridPos(self, X, Y, Z):
        i = math.floor((self.imgLeftUpY - Y) / self.imgCellHeight)+1
        j = math.floor((X - self.imgLeftUpX) / self.imgCellWidth)+1
        i = max(min(i, self.size[0]-1), 0)
        j = max(min(j, self.size[1]-1), 0)
        # h = math.floor( Z / 10) + 1
        return i, j, Z

    def getNetSpeed3d(self, point1, point2) -> float:
        # 1.直线栅格化
        grids, dis = self.getGridInLine(point1, point2)
        total = grids.shape[0]
        if total <= 1:
            return 1
        if dis > 500:
            return 0
        # 2.判断高度以及坐标是否经过建筑并记录个数
        count = 0
        for i in range(total):
            if self.imgArray.ReadAsArray(grids[i][0], grids[i][1],1,1) >= (grids[i][2]-1)*10:
                count += 1
        # 3.以直线总长除以栅格数量表示每个栅格长度
        d_undergroud = count / total
        d_notundergroud = 1 - d_undergroud
        return d_notundergroud

    def gridPos2meterPos(self, i, j):
        x = self.imgLeftUpX + j * self.imgCellWidth
        y = self.imgLeftUpY - i * self.imgCellHeight
        # z = self.imgArray.ReadAsArray(i,j,1,1)
        z = self.imgArray[i][j]
        return x, y, z



    def meter2latlng(self, metercoor):
        # X,Y -> lon, lat

        prosrs = osr.SpatialReference()  # 空间参考，源数据是SpatialReference
        if "WGS84" in self.dsmPath:
            if "guilin" in self.dsmPath:
                prosrs.ImportFromEPSG(4546)
            elif "nanning" in self.dsmPath:
                prosrs.ImportFromEPSG(4546)
            else:
                prosrs.ImportFromEPSG(4547)
        else:
            prosrs.ImportFromWkt(self.imgGdal.GetProjection())  # dataset.GetProjection()源结果CGCS2000 PROJCS["CGCS2000_3_Degree_GK_CM_117E",GEOGCS["China Geodetic Coordinate System 2000",DATUM["China_2000",SPHEROID["CGCS2000",6378137,298.257222101004,AUTHORITY["EPSG","1024"]],AUTHORITY["EPSG","1043"]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4490"]],PROJECTION["Transverse_Mercator"],PARAMETER["latitude_of_origin",0],PARAMETER["central_meridian",117],PARAMETER["scale_factor",1],PARAMETER["false_easting",500000],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["Easting",EAST],AXIS["Northing",NORTH],AUTHORITY["EPSG","4548"]]
        source_projection = osr.SpatialReference()
        source_projection.ImportFromEPSG(4326)
        ct = osr.CoordinateTransformation(prosrs, source_projection  )
        if metercoor[1]< 3000000:
            coords = ct.TransformPoint(metercoor[1], metercoor[0])  # 源结果 (211938.94312448334, 3379371.4904014003, 0.0)
        else:
            coords = ct.TransformPoint(metercoor[0], metercoor[1])  # 源结果 (211938.94312448334, 3379371.4904014003, 0.0)
        if coords[1] > coords[0]:
            return [coords[1], coords[0]]
        else:
            return coords[:2]



    def latlng2meter(self, radiopos):
        # [lon, lat] -> [X, Y]
        prosrs = osr.SpatialReference()
        source = osr.SpatialReference()
        source.ImportFromEPSG(4326)
        if "WGS84" in self.dsmPath:
            if "guilin" in self.dsmPath:
                prosrs.ImportFromEPSG(4546)
            elif "nanning" in self.dsmPath:
                prosrs.ImportFromEPSG(4546)
            else:
                prosrs.ImportFromEPSG(4547)
        else:
            prosrs.ImportFromWkt(self.imgGdal.GetProjection())

        ct = osr.CoordinateTransformation(source, prosrs)
        coords = ct.TransformPoint(radiopos[1], radiopos[0])  # 源结果 (211938.94312448334, 3379371.4904014003, 0.0)
        if coords[0] > coords[1]:
            return [coords[1], coords[0]]
        else:
            return coords[:2]




    def grid2latlon(self, i, j):
        x, y, _ = self.gridPos2meterPos(i, j)
        return self.meter2latlng([x, y])

    def GetLineNetSpeedFrowTwoGridPos(self, X1, Y1, Z1, endRow, endCol, Z2): #栅格坐标
        #改进1：直线栅格化的步进加大，并且如果两点间都没有遇到建筑物的话，步进值可以进一步加大
        #改进2：将要计算的栅格构建成四分树结构，越到外层，就更多个栅格合并成一个栅格。  计算量减少十分之一
        #改进3：使用numpy进行判断 ok
        dtimes = 1
        if Z2 < 0:
            return 1000

        X2, Y2, _ = self.gridPos2meterPos(endRow, endCol) # 测试点
        # 电台点
        startRow, startCol, _ = self.meterPos2GridPos(X1, Y1, Z1)


        if X1 == X2 and Y1 == Y2:
            return 0

        tree_Penetrate_Distance = 0
        Current_Z = Z1

        l = math.sqrt((X1 - X2) * (X1 - X2) + (Y1 - Y2) * (Y1 - Y2) + (Z1 - Z2) * (Z1 - Z2))

        if abs((X1 - X2) / self.imgCellWidth) > abs((Y1 - Y2) / self.imgCellHeight): # 哪个方向上的格子更多，则采用哪个方向，这里的是X方向
            k = (Y2 - Y1) / (X2 - X1) # 斜率
            d = abs(endCol - startCol) / dtimes # 相差的列数，X方向的相差格子数
            if d == 0:
                d = 1
            # 每个栅格平摊的高程和线段长度
            divide_Z = (Z1 - Z2) / d
            divide_S = l / d
            if endCol > startCol:
                tmpCols = np.clip(startCol + np.arange(d, dtype=np.int32), 0, self.imgWidth-1)
                tmpRows = np.clip(np.floor(startRow - np.arange(d)*k).astype(int), 0, self.imgHeight-1)
                tmpZ = Z1 + np.arange(d) * (-divide_Z)
                count = np.sum(tmpZ < self.imgArray[tmpRows, tmpCols])
                # tmpDsm = np.array([self.imgArray.ReadAsArray(tr, tc, 1, 1)[0] for tr, tc in zip(tmpRows, tmpCols)]).reshape(1,-1)
                # count = np.sum(tmpZ < tmpDsm)
                tree_Penetrate_Distance = count * divide_S
            else:
                tmpCols = np.clip(startCol + np.arange(d, dtype=np.int32) * (-1), 0, self.imgWidth-1)
                tmpRows = np.clip(np.floor(startRow + np.arange(d)*k).astype(int), 0, self.imgHeight-1)
                tmpZ = Z1 + np.arange(d) * (-divide_Z)
                # tmpDsm = np.array([self.imgArray.ReadAsArray(tr, tc, 1, 1)[0] for tr, tc in zip(tmpRows, tmpCols)]).reshape(1,-1)
                # count = np.sum(tmpZ < tmpDsm)
                count = np.sum(tmpZ < self.imgArray[tmpRows, tmpCols])
                tree_Penetrate_Distance = count * divide_S


        else:
            k = (X2 - X1) / (Y2 - Y1)  # 斜率

            d = abs(endRow - startRow)/ dtimes  # 相差的行数
            if d == 0:
                d = 1
            # 每个栅格平摊的高程和线段长度
            divide_Z = (Z1 - Z2) / d
            divide_S = l / d

            if endRow > startRow:
                tmpRows = np.clip(startRow + np.arange(d, dtype=np.int32), 0, self.imgWidth-1)
                tmpCols = np.clip(np.floor(startCol - np.arange(d)*k).astype(int), 0, self.imgHeight-1)
                # tmpCols = tmpCols[np.all([tmpCols<self.size[0] , tmpCols>=0])]
                # tmpRows = tmpRows[np.all([tmpRows<self.size[1] , tmpRows>=0])]
                tmpZ = Z1 + np.arange(d) * (-divide_Z)
                count = np.sum(tmpZ < self.imgArray[tmpRows, tmpCols])
                # tmpDsm = np.array([self.imgArray.ReadAsArray(tr, tc, 1, 1)[0] for tr, tc in zip(tmpRows, tmpCols)]).reshape(1,-1)
                # count = np.sum(tmpZ < tmpDsm)

                tree_Penetrate_Distance = count * divide_S
            else:
                tmpRows = np.clip(startRow + np.arange(d, dtype=np.int32) * (-1), 0, self.imgWidth-1)
                tmpCols = np.clip(np.floor(startCol + np.arange(d)*k).astype(int), 0, self.imgHeight-1)
                # tmpCols = tmpCols[np.all([tmpCols<self.size[0] , tmpCols>=0])]
                # tmpRows = tmpRows[np.all([tmpRows<self.size[1] , tmpRows>=0])]
                tmpZ = Z1 + np.arange(d) * (-divide_Z)
                count = np.sum(tmpZ < self.imgArray[tmpRows, tmpCols])
                # tmpDsm = np.array([self.imgArray.ReadAsArray(tr, tc, 1, 1)[0] for tr, tc in zip(tmpRows, tmpCols)]).reshape(1,-1)
                # count = np.sum(tmpZ < tmpDsm)

                tree_Penetrate_Distance = count * divide_S
        return tree_Penetrate_Distance

    def GetLineNetSpeed(self, count, endRow, endCol, Z2): #栅格坐标
        #改进1：直线栅格化的步进加大，并且如果两点间都没有遇到建筑物的话，步进值可以进一步加大
        #改进2：将要计算的栅格构建成四分树结构，越到外层，就更多个栅格合并成一个栅格。  计算量减少十分之一
        #改进3：使用numpy进行判断 ok
        dtimes = 1
        if Z2 < 0:
            return 1000

        X2, Y2, _ = self.gridPos2meterPos(endRow, endCol) # 测试点
        # 电台点
        startRow, startCol, _ = self.radioposGrid[count]
        X1, Y1, Z1 = self.radioposMeter[count]

        if X1 == X2 and Y1 == Y2:
            return 0

        tree_Penetrate_Distance = 0
        Current_Z = Z1

        l = math.sqrt((X1 - X2) * (X1 - X2) + (Y1 - Y2) * (Y1 - Y2) + (Z1 - Z2) * (Z1 - Z2))

        if abs((X1 - X2) / self.imgCellWidth) > abs((Y1 - Y2) / self.imgCellHeight): # 哪个方向上的格子更多，则采用哪个方向，这里的是X方向
            k = (Y2 - Y1) / (X2 - X1) # 斜率
            d = abs(endCol - startCol) / dtimes # 相差的列数，X方向的相差格子数
            if d == 0:
                d = 1
            # 每个栅格平摊的高程和线段长度
            divide_Z = (Z1 - Z2) / d
            divide_S = l / d
            if endCol > startCol:
                tmpCols = np.clip(startCol + np.arange(d, dtype=np.int32), 0, self.imgWidth-1)
                tmpRows = np.clip(np.floor(startRow - np.arange(d)*k).astype(int), 0, self.imgHeight-1)
                tmpZ = Z1 + np.arange(d) * (-divide_Z)
                count = np.sum(tmpZ < self.imgArray[tmpRows, tmpCols])
                # tmpDsm = np.array([self.imgArray.ReadAsArray(tr, tc, 1, 1)[0] for tr, tc in zip(tmpRows, tmpCols)]).reshape(1,-1)
                # count = np.sum(tmpZ < tmpDsm)
                tree_Penetrate_Distance = count * divide_S
            else:
                tmpCols = np.clip(startCol + np.arange(d, dtype=np.int32) * (-1), 0, self.imgWidth-1)
                tmpRows = np.clip(np.floor(startRow + np.arange(d)*k).astype(int), 0, self.imgHeight-1)
                tmpZ = Z1 + np.arange(d) * (-divide_Z)
                # tmpDsm = np.array([self.imgArray.ReadAsArray(tr, tc, 1, 1)[0] for tr, tc in zip(tmpRows, tmpCols)]).reshape(1,-1)
                # count = np.sum(tmpZ < tmpDsm)
                count = np.sum(tmpZ < self.imgArray[tmpRows, tmpCols])
                tree_Penetrate_Distance = count * divide_S


        else:
            k = (X2 - X1) / (Y2 - Y1)  # 斜率

            d = abs(endRow - startRow)/ dtimes  # 相差的行数
            if d == 0:
                d = 1
            # 每个栅格平摊的高程和线段长度
            divide_Z = (Z1 - Z2) / d
            divide_S = l / d

            if endRow > startRow:
                tmpRows = np.clip(startRow + np.arange(d, dtype=np.int32), 0, self.imgWidth-1)
                tmpCols = np.clip(np.floor(startCol - np.arange(d)*k).astype(int), 0, self.imgHeight-1)
                # tmpCols = tmpCols[np.all([tmpCols<self.size[0] , tmpCols>=0])]
                # tmpRows = tmpRows[np.all([tmpRows<self.size[1] , tmpRows>=0])]
                tmpZ = Z1 + np.arange(d) * (-divide_Z)
                count = np.sum(tmpZ < self.imgArray[tmpRows, tmpCols])
                # tmpDsm = np.array([self.imgArray.ReadAsArray(tr, tc, 1, 1)[0] for tr, tc in zip(tmpRows, tmpCols)]).reshape(1,-1)
                # count = np.sum(tmpZ < tmpDsm)

                tree_Penetrate_Distance = count * divide_S
            else:
                tmpRows = np.clip(startRow + np.arange(d, dtype=np.int32) * (-1), 0, self.imgWidth-1)
                tmpCols = np.clip(np.floor(startCol + np.arange(d)*k).astype(int), 0, self.imgHeight-1)
                # tmpCols = tmpCols[np.all([tmpCols<self.size[0] , tmpCols>=0])]
                # tmpRows = tmpRows[np.all([tmpRows<self.size[1] , tmpRows>=0])]
                tmpZ = Z1 + np.arange(d) * (-divide_Z)
                count = np.sum(tmpZ < self.imgArray[tmpRows, tmpCols])
                # tmpDsm = np.array([self.imgArray.ReadAsArray(tr, tc, 1, 1)[0] for tr, tc in zip(tmpRows, tmpCols)]).reshape(1,-1)
                # count = np.sum(tmpZ < tmpDsm)

                tree_Penetrate_Distance = count * divide_S
        return tree_Penetrate_Distance

    def main(self):
        radiaArea = 100
        result = np.ones(shape=self.size[:2])
        result *= -1
        for count in range(len(self.radioposMeter)):
            radiopixel = self.radioposGrid[count]


            imin = max(0, radiopixel[0]-radiaArea)
            imax = min(self.imgHeight-1, radiopixel[0]+radiaArea)
            jmin = max(0, radiopixel[1]-radiaArea)
            jmax = min(self.imgWidth-1, radiopixel[1]+radiaArea)
            for i in range(imin, imax, 1):
                for j in range(jmin, jmax, 1):
                    dis = (i-radiopixel[0])*(i-radiopixel[0])+(j-radiopixel[1])*(j-radiopixel[1])
                    times = 1
                    pixelHeight = self.imgArray[i][j]
                    if pixelHeight < 0:
                        continue
                        pixelHeight = 5
                    if dis > radiaArea*radiaArea:
                        continue
                    times = 1- math.sqrt(dis) / radiaArea
                    # for calculateRadio in self.radioposMeter:    
                    value = self.GetLineNetSpeed(self.radioposMeter[count][0], self.radioposMeter[count][1], self.radioposMeter[count][2], i, j, pixelHeight)
                    speed = (40-0.05*value[1]) * times
                    speed = max(0, speed)
                    if speed > result[i][j]:
                        result[i][j] = speed
            result[radiopixel[0]][radiopixel[1]] = 0
        array_color = self.drawColor(result)
        # self.tilesResult(array_color)
        self.drawResult(array_color, '')
        return result

    def main2(self, r=9000, dis=30): #根据电台为中心生成多个图片
        # r = 300 # 半径（m）要计算的电台通信覆盖范围的半径
        # dis = r*2/radiaArea / self.imgCellHeight #目前是间隔的格子数，不是m，用户应该用米更好

        radiaArea = (int) (2*r/dis)
        rectangles = []
        for count in range(len(self.radioposMeter)):
            radiopixel = self.radioposGrid[count]
            radioMeter = self.radioposMeter[count]
            r = min([r, radioMeter[0] - self.imgLeftUpX, self.imgRightDownX - radioMeter[0], self.imgLeftUpY - radioMeter[1], radioMeter[1] - self.imgRightDownY])
            imin = max(0, round(radiopixel[0] - r / self.imgCellHeight))
            imax = min(self.imgHeight - 1, round(radiopixel[0] +r / self.imgCellHeight))
            jmin = max(0, round(radiopixel[1] - r / self.imgCellWidth))
            jmax = min(self.imgWidth - 1, round(radiopixel[1] + r / self.imgCellWidth))

            #计算要放的矩形经纬度
            west_south = self.grid2latlon(imax, jmin)
            east_north = self.grid2latlon(imin, jmax)
            rectangles.append(west_south+east_north)
            #计算要参与的栅格的索引
            indices = select_indices(imin, imax, jmin, jmax, radiaArea)
            print("r",r, imin, imax, jmin, jmax, self.imgHeight, self.imgWidth)

            #开始计算
            st = time.time()
            result = np.array([self.GetLineNetSpeed(count, a, b, self.imgArray[a][b]) if self.imgArray[a][b] > 0 else 1000 for a, b in indices]).reshape(radiaArea, radiaArea)
            # result = np.array([self.GetLineNetSpeed(count, a, b, self.imgArray.ReadAsArray(a,b,1,1)) if self.imgArray.ReadAsArray(a,b,1,1) > 0 else 1000 for a, b in indices]).reshape(radiaArea, radiaArea)
            #乘距离衰减倍率模型
            result = np.clip((cmax - gamma * result), 0, cmax)
            et = time.time()
            print("网速用时：", et - st)
            array_color = self.drawColor(result)
            self.drawResult(array_color, str(count))
        return rectangles

    def main3(self): #根据电台为中心生成多个图片
        radiaArea = 100
        rectangles = []
        for count in range(len(self.radioposMeter)):
            result = np.ones(shape=(2 * radiaArea, 2 * radiaArea))
            result *= -1
            radiopixel = self.radioposGrid[count]
            imin = max(0, radiopixel[0] - radiaArea)
            imax = min(self.imgHeight - 1, radiopixel[0] + radiaArea-1)
            jmin = max(0, radiopixel[1] - radiaArea)
            jmax = min(self.imgWidth - 1, radiopixel[1] + radiaArea-1)
            #计算要放的矩形范围
            west_south = self.grid2latlon(imax, jmin)
            east_north = self.grid2latlon(imin, jmax)
            rectangles.append(west_south+east_north)
            st = time.time()
            for i in range(imin, imax+1, 1):
                for j in range(jmin, jmax+1, 1):
                    dis = (i - radiopixel[0]) * (i - radiopixel[0]) + (j - radiopixel[1]) * (j - radiopixel[1])
                    pixelHeight = self.imgArray[i][j]
                    if pixelHeight < 0:
                        continue
                    if dis > radiaArea*radiaArea:
                        continue
                    times = 1 - math.sqrt(dis) / radiaArea
                    value = self.getCoveredDistance_cuda(np.array(radiopixel), np.array([i, j, pixelHeight]))
                    speed = (40 - 0.05 * value) * times
                    speed = max(0, speed)
                    if speed > result[i-imin][j-jmin]:
                        result[i-imin][j-jmin] = speed
            et = time.time()
            print("计算网速用时：", et - st)
            result[99][99] = 0
            array_color = self.drawColor(result)
            self.drawResult(array_color, str(count))
        return rectangles

    # def getCoveredDistance_cuda(self, point1, point2):
    #     point1 = torch.from_numpy(point1).float().to(device)
    #     point2 = torch.from_numpy(point2).float().to(device)
    #
    #     v = point2 - point1
    #     grids = torch.empty(size=(0, point1.shape[0]),  dtype=torch.long, device=device)
    #     dis = torch.norm(v, p=2)
    #     step = 1.0
    #     curlength = 0
    #     while curlength < dis:
    #         curlength += step
    #         tp = torch.round(point1 + v * curlength / dis + 0.5).reshape(1, point1.shape[0]).to(torch.int32)
    #         tp = torch.clamp(tp, torch.tensor(0).to(device), torch.from_numpy(self.size-1).to(device))
    #         grids = torch.cat((grids, tp), axis=0)
    #     grids = torch.unique(grids, dim=0)
    #     under = torch.sum(grids[:, 2] < self.imgArray_cuda[grids[:, 0], grids[:, 1]])
    #     total = grids.shape[0]
    #     result = under / total * dis
    #     return result.to("cpu")

    def getCoveredDistance(self, point1, point2):
        v = point2 - point1
        grids = np.empty(shape=(0, point1.shape[0]), dtype ='uint8')
        dis = np.linalg.norm(v, ord=2)
        step = 1.0
        curlength = 0
        while curlength < dis:
            curlength += step
            tp = np.clip(np.fix(point1 + v * curlength / dis + 0.5).reshape(1, point1.shape[0]), 0, self.size-1).astype(np.int32)
            grids = np.append(grids, tp, axis=0)
        grids = np.unique(grids, axis=0)
        under = np.sum(grids[:,2] < self.imgArray[grids[:,0], grids[:,1]])
        total = grids.shape[0]
        return under / total * dis

    def getGridInLine(self, point1, point2, r):
        v = point2 - point1
        grids = np.empty(shape=(0, point1.shape[0]), dtype =np.int32)
        dis = np.linalg.norm(v, ord=2)
        step = 1.0
        curlength = 0
        while curlength < dis:
            curlength += step
            tp = np.clip(np.fix(point1 + v * curlength / dis + 0.5).reshape(1, 2), 0, 2*r).astype(np.int32)
            grids = np.append(grids, tp, axis=0)
        return np.unique(grids, axis=0)

    def lineTemplates(self, r):
        #求二维r+1 * r+1的二维矩阵中，点i，j到点r，r的射线投影在二维平面后，经过的栅格的索引
        dict = {}
        for i in range(2*r+1):
            for j in range(2*r+1):
                if (i==r) & (j==r):
                    continue
                p1 = np.array([i,j])
                p2 = np.array([r,r])
                grids = self.getGridInLine(p1, p2, r)
                # ndarray不能作为hash的键，可以转成tuple
                dict[tuple(p1)] = grids
        return dict

    def drawResult(self, result, label):
        # displaying the image
        # cv2.imwrite("C:/workspace/cesiumChooseDot/server/resultimg_db/result_img0703.png", result)
        cv2.imwrite("C:/workspace/cesiumChooseDot/server/resultimg_db/result_img"+ label + ".png", result)

    def drawColor(self, result):
        shape = result.shape
        array_created = np.full((shape[0], shape[1], 3), 255, dtype=np.uint8)
        for i in range(shape[0]):
            for j in range(shape[1]):
                # if result[i][j]>=0 and result[i][j] < 8:
                #     array_created[i, j] = [0, 0, 255]
                #     pass
                if result[i][j] >= 8 and result[i][j] < 16:
                    array_created[i, j] = [255, 0, 255]
                    pass
                elif result[i][j] >= 16 and result[i][j] < 24:
                    array_created[i, j] = [64,125,255]
                    pass
                elif result[i][j] >= 24 and result[i][j] < 32:
                    array_created[i, j] = [255, 0, 0]
                    pass
                elif result[i][j] >= 32:
                    array_created[i, j] = [0, 252, 124]
                    pass
        return array_created

    # def tilesResult(self, data):
    #     min_level = 5
    #     max_level = 13 # 5-15的用时太久了，要将近8min
    #
    #     # 设置驱动和文件名
    #     driver = gdal.GetDriverByName('GTiff')
    #
    #     # 创建新的TIF文件
    #     dataset = driver.Create(outputTifFileName, self.imgWidth, self.imgHeight, 3, gdal.GDT_Byte)
    #
    #     # 设置几何信息和投影信息
    #     dataset.SetGeoTransform(self.imgGdal.GetGeoTransform())
    #     dataset.SetProjection(self.imgGdal.GetProjection())
    #
    #
    #     # 为每个波段生成随机数据并写入
    #     for i in range(1, 4):
    #         band = dataset.GetRasterBand(i)
    #         band.WriteArray(data[:,:,3-i])
    #
    #     # 关闭数据集
    #     dataset = None
    #
    #     options = {
    #         'zoom':(min_level,max_level), # 切片层级 min zoom 5 - max zoom 18
    #         'resume':True,
    #         'tile_size': 256, # 瓦片大小
    #         # 's_srs': 'PROJCS["CGCS2000 / 3-degree Gauss-Kruger CM 114E",GEOGCS["China Geodetic Coordinate System 2000",DATUM["China_2000",SPHEROID["CGCS2000",6378137,298.257222101,AUTHORITY["EPSG","1024"]],AUTHORITY["EPSG","1043"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4490"]],PROJECTION["Transverse_Mercator"],PARAMETER["latitude_of_origin",0],PARAMETER["central_meridian",114],PARAMETER["scale_factor",1],PARAMETER["false_easting",500000],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["Northing",NORTH],AXIS["Easting",EAST],AUTHORITY["EPSG","4547"]]',
    #         's_srs': self.imgGdal.GetProjection(),
    #         'xyz': True,
    #         'np_processes':2
    #     }
    #     if os.path.exists(outputTilesPath):  # 3屏电脑：D:/apache-tomcat-8.5.99/webapps/tiles
    #         shutil.rmtree(outputTilesPath)
    #     gdal2tiles.generate_tiles(outputTifFileName, outputTilesPath, **options)
    #     self.changeName(outputTilesPath)
    #
    def changeName(self, dir):
        levels = os.listdir(dir)
        levels = [name for name in levels if os.path.isdir(os.path.join(dir, name))]
        for level in levels:
            dir1 = dir+'/'+level
            level1 = os.listdir(dir1)
            for director in level1:
                dir2 = dir1+'/'+director
                level2 = os.listdir(dir2)
                for pic in level2:
                    strs = pic.split('.')
                    if strs[1] == 'png':
                        oldname = int(strs[0])
                        newname = str(pow(2,int(level))-1 - oldname)+'.png'
                        os.rename(os.path.join(dir2, pic), os.path.join(dir2, newname))


class Particle:
    def __init__(self, dim, bounds):
        #self.position = np.random.uniform(bounds[0], bounds[1], dim)  # 初始化粒子位置

        x_coords = np.random.uniform(bounds[0][0], bounds[1][0], dim)
        y_coords = np.random.uniform(bounds[0][1], bounds[1][1], dim)

        # 将点的坐标按照所需的格式组织成一个NumPy数组
        self.position = np.empty(2 * dim)
        self.position[::2] = x_coords
        self.position[1::2] = y_coords

        self.velocity = np.random.uniform(-1, 1, 2 *dim)  # 初始化粒子速度
        self.best_position = self.position.copy()  # 记录粒子历史最佳位置
        self.best_score = float('inf')  # 记录粒子历史最佳得分

def objective_function(x):
    # 这是一个示例的目标函数，你可以根据需要修改
    return np.sum(np.square(x))

def update_velocity(particle, global_best_position, w, c1, c2):
    r1 = np.random.rand(len(particle.velocity))
    r2 = np.random.rand(len(particle.velocity))
    inertia = w * particle.velocity  # 惯性项
    cognitive = c1 * r1 * (particle.best_position - particle.position)  # 认知项
    social = c2 * r2 * (global_best_position - particle.position)  # 社会项
    particle.velocity = inertia + cognitive + social  # 更新粒子速度

def update_position(particle, bounds):
    particle.velocity[particle.velocity>50] = 50
    particle.velocity[particle.velocity < -50] = -50
    particle.position += particle.velocity  # 更新粒子位置
    # 确保粒子位置在边界内
    particle.position[::2] = np.clip(particle.position[::2], bounds[0][0], bounds[1][0])
    particle.position[1::2] = np.clip(particle.position[1::2], bounds[0][1], bounds[1][1])

def dfs(node, visited, adjacency_list):
    visited[node] = True
    for neighbor in adjacency_list[node]:
        if not visited[neighbor]:
            dfs(neighbor, visited, adjacency_list)

def pso(radioposs,Y, bounds, num_particles, max_iter, w, c1, c2,h_uav,h_ground,num_uav,num_ground ,tifFilePath, aa):
    # aa = deploy(tifFilePath, radioposs)
    dim = num_uav+num_ground
    particles = [Particle(dim, bounds) for _ in range(num_particles)]  # 初始化粒子群
    global_best_position = None
    global_best_score = float('inf')
    length = len(radioposs)
    #print((-Y[1]+a.imgRightDownY)//a.imgCellHeight)
    adjacency_list_final = {}
    best_num_in = 0
    for _ in range(max_iter):
        for particle in particles:
            score = 0
            num_in=0#连通个数

            score_total=0
            dis_total=0

            # 建立一个图，使用dfs判断是否为连通图
            # 构建邻接列表
            num_nodes = length + num_uav + num_ground
            adjacency_list = {i: [] for i in range(num_nodes)}
            # nodes1为所有点的grid表示，height为所有点的高度
            nodes1 = np.array([[aa.meter2Grid(row[0], row[1])[0], aa.meter2Grid(row[0], row[1])[1]] for row in Y]).flatten()
            nodes1 = np.concatenate((nodes1, particle.position))
            nodes1 = nodes1.astype(int)
            height = np.zeros(num_nodes)
            for i in range(length):
                height[i] = Y[i, 2]
            height[length:length + num_uav] = h_uav
            score_rate=np.zeros(num_nodes)#记录每个节点速率
            score_rate_tempt = np.zeros(num_nodes)  # 记录每个节点连通个数
            # uav高度改为比地面高
            for i in range(length, length + num_uav):
                height[i] = h_uav + aa.imgArray[nodes1[i * 2]][nodes1[i * 2+ 1] ]
            #ground高度改为比地面高
            for i in range(length + num_uav,length + num_uav+num_ground):
                height[i] = h_ground+aa.imgArray[nodes1[i * 2]][nodes1[i * 2+1]]
            for i in range(num_nodes):
                for j in range(i + 1, num_nodes):
                    value = aa.GetLineNetSpeedFrowTwoGridPos(aa.gridPos2meterPos(nodes1[i * 2], nodes1[i * 2 + 1])[0],
                                               aa.gridPos2meterPos(nodes1[i * 2], nodes1[i * 2 + 1])[1], height[i],
                                               nodes1[j * 2], nodes1[j * 2 + 1], height[j])

                    dis = (nodes1[i * 2] - nodes1[j * 2]) ** 2 + (nodes1[i * 2 + 1] - nodes1[j * 2 + 1]) ** 2
                    times = 1 - math.sqrt(dis) / 100
                    #通视怎么办
                    if ((i>=length and i<length+num_uav) and (j>=length and j<length+num_uav)) and math.sqrt(dis)<1736 and value<=0: #如果i和j都是无人机，并且两者距离小于50km，并且被挡的距离等于0（即通视）
                        adjacency_list[i].append(j)
                        adjacency_list[j].append(i)
                        continue
                    #score = (40 - 0.05 * value[1]) * times
                    # rate = (40 - 0.05 * value[1]) * times
                    print(value)
                    rate = (cmax - gamma * value)
                    if rate > 24 and times>0:
                        score_rate[i]+=rate
                        score_rate[j] += rate
                        adjacency_list[i].append(j)
                        adjacency_list[j].append(i)
            # 使用深度优先搜索来检查连通性
            visited = [False] * num_nodes
            dfs(0, visited, adjacency_list)

            # 如果所有节点都被访问到，则说明是连通图
            for item in visited:
                if item==True:
                    score=score-1
                    num_in=num_in-1

            if(score==-num_nodes):
                score=score-np.sum(np.log(score_rate))/400/num_nodes/num_nodes
            if(num_in<best_num_in):
                best_num_in=num_in


            '''
            for index in range(length):
                value = aa.GetLineNetSpeed(Y[index, 0], Y[index, 1], Y[index, 2], i, j, h)
                dis = (aa.radioposGrid[index][0] - i) ** 2 + (aa.radioposGrid[index][1] - j) ** 2
                dis_total+=math.sqrt(dis)/100000
                times = 1 - math.sqrt(dis) / 100
                score = (40 - 0.05 * value[1]) * times
                if (40 - 0.05 * value[1]) * times > 8:
                    score = 8
                    score_total-=score
                if times < 0 or score < 8:
                    score_total = 0

            if score_total!=-length*8:
                score_total=0
            '''



            #score=score_total+dis_total
            #score=math.sqrt(dis)
            if score < particle.best_score:
                particle.best_score = score
                particle.best_position = particle.position.copy()
            if score < global_best_score:
                global_best_score = score
                global_best_position = particle.position.copy()
                adjacency_list_final = adjacency_list


        for particle in particles:
            update_velocity(particle, global_best_position, w, c1, c2)
            update_position(particle, bounds)

    return global_best_position, global_best_score, adjacency_list_final, best_num_in



# tifFilePath = r"C:\workspace\lbc\txc\0226\wuhan_dsm_114.tif"






if __name__ == '__main__':
    dsm = gdal.Open(r'C:\workspace\lbc\自组网通导遥群智时空动态优化\RDDPG_anet\map\dsmwithbuildFromEx2_blabel - 副本.tif')

    fdsm = dsm.GetRasterBand(1).ReadAsArray(0,0,500,500)
    fdsm[fdsm==255] = 0

    def save_as_tif(data, save_path, file_name):
        driver = gdal.GetDriverByName('GTiff')
        dataset = driver.Create(save_path + file_name, data.shape[1], data.shape[0], 1, gdal.GDT_Float32)
        dataset.GetRasterBand(1).WriteArray(data)
        dataset.FlushCache()
        dataset = Nonedata = np.array([[1, 2], [3, 4]])


    save_as_tif(fdsm, r'C:/workspace/lbc/自组网通导遥群智时空动态优化/RDDPG_anet/map/', 'newtree.tif')
    print(fdsm)

#     import matplotlib
#     matplotlib.use('agg')
#     tifFilePath = r"C:\workspace\lbc\txc\0226\数据\guangxi_guilin_dsmCGCS2k.tif"
#     tifFilePath = r"C:\workspace\cesiumChooseDot\server\data\wuhan_dsm_114_dsmCGCS2k_30.tif"
#     tifFilePath = r"C:\workspace\cesiumChooseDot\server\data\guangxi_guilin_dsmWGS84_5.tif"
#
# #     tifFilePath = r"C:\workspace\lbc\自组网通导遥群智时空动态优化\地理数据\DSM_XXXB.tif"
# #xlxs测试数据
#     # radioposs = [[110.46807629 , 25.27389282, 268], [110.56807629 , 25.37389282, 200]]
#     radioposs = [[114.3557052,30.5300442,16.9]]
#     # radioposs = [[110.193871,25.285245,125.86]] #418,566.52东2,798,003.86北
# #     # radioposs = [[110.46807629 , 25.27389282,
#     #     268    ], [110.43096165 , 25.3100568 , 242   ]    ]
#     st = time.time()
#
#     a = deploy(tifFilePath, radioposs)
#     m = [417910.37828443747, 2796838.3409542013]
#     # m = a.latlng2meter([114.3557052,30.5300442])
#     t = a.meter2latlng(m)
#     print(m)
#     print(t)
#     et = time.time()
#     print("读图用时：", et - st)
#     st = time.time()
#     a.main2(2000, 100)
#     et = time.time()
#     print("计算用时：", et - st)
# p1 = np.array([200,300,100])
    # p2 = np.array([200,300,20])
    # dict = a.lineTemplates(600)
    # print(len(dict))
    # print(dict)

    # testmap = a.imgArray
    # testmap[testmap==32767] = 0
    #不能直接把整个map变成一个三维的矩阵
    # testmap = generate_tensor2(testmap)
#     print(testmap)
#     # print(a.GetLineNetSpeed(446421.4117935, 2796500.813667, 268, 2557,1455,242))





    # 示例：
    imin, imax = 0, 599
    jmin, jmax = 0, 599
    num_points = 600


    # 设定矩阵大小
    size = 600
    half_size = size // 2

    # 解方程找到a的值，使得f(250) = 1且f(0) = 0
    # 对于f(x) = -ax^2 + b，由于中心倍率为1且对称，b = 1
    # 代入f(250) = 1得：-a*250^2 + 1 = 1，解得a = 1 / 62500
    a = 1 / (half_size ** 2)

    # 创建一个空的500x500矩阵
    mask = np.zeros((size, size))

    # 填充矩阵，使用二次函数计算每个点的值
    for i in range(size):
        for j in range(size):
            # 计算x和y方向上与中心的距离的平方
            x_dist_sq = (i - half_size) ** 2
            y_dist_sq = (j - half_size) ** 2

            # 使用二次函数计算倍率并赋值给矩阵
            # 注意：由于我们想要倍率从1递减到0，并且a是负的，所以不需要取负号
            mask[i, j] = 1 - a * (x_dist_sq + y_dist_sq)

            # 确保倍率不会小于0（由于数值精度问题可能会出现略小于0的值）
            mask[i, j] = max(mask[i, j], 0)

    st = time.time()
    random_float_array = np.random.rand(600, 600)
    c = random_float_array * mask
    et = time.time()
    print("用时：", et - st)


    def generate_mask(size, boundary_value=0):
        # 创建一个空的size x size矩阵
        mask = np.zeros((size, size))

        # 计算中心索引
        center_x, center_y = size // 2, size // 2

        # 遍历矩阵的每一个元素
        for x in range(size):
            for y in range(size):
                # 计算当前位置到中心的距离的平方
                distance_squared = (x - center_x) ** 2 + (y - center_y) ** 2

                # 为了避免除以零，并且确保中心点的倍率为1
                if distance_squared == 0:
                    mask[x, y] = 1
                else:
                    # 使用二次函数递减，这里我们假设a为-1/(中心到边界距离的平方)，这样边界处为boundary_value
                    # 但为了简化，我们可以直接计算一个缩放因子，使得中心为1，边界为boundary_value
                    max_distance_squared = (size // 2) ** 2
                    scale_factor = (1 - boundary_value) / max_distance_squared
                    mask[x, y] = 1 - scale_factor * distance_squared

                    # 确保值不小于边界值（由于数值精度问题可能会出现略小于boundary_value的值）
                    mask[x, y] = max(mask[x, y], boundary_value)

        return mask

        # 生成一个500x500的倍率掩膜矩阵，边界值为0

    st = time.time()
    mask_0_5 = generate_mask(600, boundary_value=0.5)
    random_float_array = np.random.rand(600, 600)
    c = random_float_array * mask_0_5
    et = time.time()
    print("用时：", et - st)

    # 生成一个500x500的倍率掩膜矩阵，边界值为0.5


    # np.save('timesmask.npy', mask)
    # #测试并行计算
#     import multiprocessing
#     processes = []
#     st = time.time()
#     # # for i in range(4):
#     # #     p = multiprocessing.Process(target=a.main3, args=(i,))
#     # #     processes.append(p)
#     # #     p.start()
#     # # # 等待所有子进程结束
#     # # for p in processes:
#     # #     p.join()
#     # 创建进程池，最大进程数为4
#     pool = multiprocessing.Pool(processes=4)
#     inputs = [0,1,2,3]
#     intputs = tuple(inputs)
#
#     # 在进程池中并行计算函数
#     pool.imap(a.main3, inputs)
#     # 提交任务到进程池
#
#     # 关闭进程池，不再接受新的任务
#     pool.close()
#     # 等待所有任务完成
#     pool.join()
#     # for i in range(4):
#     #     a.main3(i)
#     et = time.time()
#     print("用时：", et - st)
#
#
#
#
#
#
#
#
#
#
#
#     leftup = [496992.6730883496347815,3433606.7595169977284968]
#     rightdown = [598469.4938060842687264,3318023.9410257339477539]
#
#     leftdown = [497008.1,3318036.0]
#     rightdown = [598448.7,3433597.0]
#
#     #cesiumlab 影像切片经纬度范围
#     #输出结果：(496960.28080999607, 3317599.907954256) (598467.7295418619, 3434063.5611976646)
#     b = [113.968503,29.977322]
#     c = [115.031259,31.023744]
#     #cesiumlab 地形切片经纬度范围
#     b = [113.968306,29.976969] #(496941.2578756226, 3317560.78241345)
#     c = [115.031233,31.023760] #(598465.2303981915, 3434065.3122185073)

    # result = a.main()
    # print(result)


    #测试并行
    # def worker(num):
    #     """线程工作函数"""
    #     print(f'Worker {num} is starting...')
    #     time.sleep(2)  # 模拟耗时操作
    #     print(f'Worker {num} is done.')
    #
    #
    # def main():
    #     # 创建线程列表
    #     threads = []
    #
    #     # 创建并启动5个线程
    #     for i in range(5):
    #         t = threading.Thread(target=worker, args=(i,))
    #         threads.append(t)
    #         t.start()
    #
    #         # 等待所有线程完成
    #     for t in threads:
    #         t.join()

