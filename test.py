import math
import Ras2Point
from Point2Ras import Point2Ras
from GetLineNetSpeed import GetLineNetSpeed
from osgeo import gdal
from osgeo import osr
import xlsxwriter as xw
from Krige import KrigingInterpolate
import matplotlib.pyplot as plt
# importing the libraries
import cv2
import numpy as np
  

#30m分辨率tif
wuhanimg = gdal.Open(r"C:\workspace\lbc\txc\0226\Copernicus_DSM_COG_10_N30_00_E114_00-elevation.tif")
# 获取图层的四个角的坐标
x0 = wuhanimg.GetGeoTransform()[0]
y0 = wuhanimg.GetGeoTransform()[3]
x1 = x0 + wuhanimg.RasterXSize * wuhanimg.GetGeoTransform()[1]
y1 = y0 + wuhanimg.RasterYSize * wuhanimg.GetGeoTransform()[5]
x2 = x0 + wuhanimg.RasterXSize * wuhanimg.GetGeoTransform()[2]
y2 = y0 + wuhanimg.RasterYSize * wuhanimg.GetGeoTransform()[4]

# 获取影像的投影信息
projection = wuhanimg.GetProjection()
# 获取影像的地理坐标系信息
geotransform = wuhanimg.GetGeoTransform()
# 打印坐标系信息
print("投影信息：", projection)
print("地理坐标系信息：", geotransform)

# 关闭数据集
wuhanimg = None

# 打印坐标
print('左上角: (%f, %f)' % (x0, y0))
print('右上角: (%f, %f)' % (x1, y1))
print('左下角: (%f, %.7f)' % (x2, y2))


# # 克里金插值结果保存的文件夹
# resultDataSetPath = './resultimg_db/'
# # 克里金插值结果保存的名字
# outputKrigingTifName = 'KrigingInterpolate'
#
#
#
#
# resImg_gdal= gdal.Open(resultDataSetPath+outputKrigingTifName+'.png')  # 读取数据
# resImg_array=resImg_gdal.GetRasterBand(1).ReadAsArray()
# im_width = resImg_gdal.RasterXSize #图像宽度
# im_height = resImg_gdal.RasterYSize #图像高度
#
# # creating an array using np.full
# # 255 is code for white color
# array_created = np.full((im_height, im_width, 3),255, dtype = np.uint8)
#
# for i in range(im_height):
#     for j in range(im_width):
#         if resImg_array[i][j]<8:
#             array_created[i,j]=[20,50,60]
#
#             pass
#         elif resImg_array[i][j]>=8 and resImg_array[i][j]<16:
#             array_created[i,j]=[120,50,160]
#             pass
#         elif resImg_array[i][j]>=16 and resImg_array[i][j]<24:
#             array_created[i,j]=[200,50,120]
#             pass
#         elif resImg_array[i][j]>=24 and resImg_array[i][j]<32:
#             array_created[i,j]=[200,250,10]
#             pass
#         elif resImg_array[i][j]>=32:
#             array_created[i,j]=[120,120,0]
#             pass
# print(array_created)
# # displaying the image
#
# cv2.imwrite("imwrite_pic.png", array_created)

   
