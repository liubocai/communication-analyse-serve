import os, sys
import pandas as pd
import numpy as np
from numpy import inf
from osgeo import gdal
import matplotlib.pyplot as plt
from pykrige.ok import OrdinaryKriging
import time


# 读写tif的类
class GRID:
    # 读图像文件
    def read_img(self, filename):
        dataset = gdal.Open(filename)  # 打开文件
        im_width = dataset.RasterXSize  # 栅格矩阵的列数
        im_height = dataset.RasterYSize  # 栅格矩阵的行数
        im_geotrans = dataset.GetGeoTransform()  # 仿射矩阵
        im_proj = dataset.GetProjection()  # 地图投影信息
        im_data = dataset.ReadAsArray(0, 0, im_width, im_height)  # 将数据写成数组，对应栅格矩阵
        im_data = np.array(im_data)
        del dataset  # 关闭对象，文件dataset
        return im_proj, im_geotrans, im_data, im_width, im_height

    # 写文件，写成tiff
    def write_img(self, filename, im_proj, im_geotrans, im_data,zoom):


        # 判断栅格数据的数据类型
        if 'int8' in im_data.dtype.name:
            datatype = gdal.GDT_Byte
        elif 'int16' in im_data.dtype.name:
            datatype = gdal.GDT_UInt16
        else:
            print('ok')
            datatype = gdal.GDT_Float32
        # 判读数组维数
        
        if len(im_data.shape) == 3:
            im_bands, im_height, im_width = im_data.shape
        else:
            im_bands, (im_height, im_width) = 1, im_data.shape
        # 创建文件
        driver = gdal.GetDriverByName("GTiff")  # 数据类型必须有，因为要计算需要多大内存空间
        dataset = driver.Create(filename, im_width, im_height, im_bands, datatype)
        tmp=list(im_geotrans)
        tmp[1]=tmp[1]*zoom
        tmp[2]=tmp[2]*zoom
        tmp[4]=tmp[4]*zoom
        tmp[5]=tmp[5]*zoom
        tmp=tuple(tmp)
        dataset.SetGeoTransform(tmp)  # 写入仿射变换参数
        
        dataset.SetProjection(im_proj)  # 写入投影
        
        if im_bands == 1:
            dataset.GetRasterBand(1).WriteArray(im_data)  # 写入数组数据
        else:
            for i in range(im_bands):
                dataset.GetRasterBand(i + 1).WriteArray(im_data[i])
        del dataset

#读取每个tiff图像的属性信息，和上面函数相似，懒得改了，混着用。
def Readxy(RasterFile):
    ds = gdal.Open(RasterFile,gdal.GA_ReadOnly)
    if ds is None:
        
        sys.exit(1)
    cols = ds.RasterXSize
    rows = ds.RasterYSize
    band = ds.GetRasterBand(1)
    # data = band.ReadAsArray(0,0,cols,rows)
    noDataValue = band.GetNoDataValue()
    projection=ds.GetProjection()
    geotransform = ds.GetGeoTransform()
    return rows,cols,geotransform,projection

# 克里金插值
def KrigingInterpolate(InputExcelPathAndName, X_coordinateField, Y_coordinateField, Sample_valueField,
                       tifDataPath, tifName,resultDataSetPath, outputKrigingTifName):
    start = time.time()                  
    Data = pd.read_excel(InputExcelPathAndName)
    Points = Data.loc[:, [X_coordinateField, Y_coordinateField]].values
    Values = Data.loc[:, [Sample_valueField]].values
    Points1 = np.array(Points)
    
    Values1 = np.array(Values)
    
    # 读取遥感影像数据
    run = GRID()
    # 这一个没有参与运算，主要为了读取它的行列数、投影信息、坐标系和noData值
    
    rows, cols, geotransform, projection= Readxy(tifDataPath + tifName)
    
    nXsize = cols
    nYsize = rows
    # **********************************//
    dataset = gdal.Open(tifDataPath + tifName)  # 打开tif
    adfGeoTransform = dataset.GetGeoTransform()  # 读取地理信息
    # 左上角地理坐标
    # print(adfGeoTransform[0])
    # print(adfGeoTransform[3])
    # 右下角地理坐标
    px = adfGeoTransform[0] + nXsize * adfGeoTransform[1] + nYsize * adfGeoTransform[2]
    py = adfGeoTransform[3] + nXsize * adfGeoTransform[4] + nYsize * adfGeoTransform[5]
    
    
    OK = OrdinaryKriging(
        Points1[:, 0],
        Points1[:, 1],
        Values1[:, 0],
        variogram_model="spherical",
        verbose=False,
        enable_plotting=False,
    )
    zoom=12 #缩放倍数
    # zoom=12 #缩放倍数
    gridx = np.arange(adfGeoTransform[0], px, adfGeoTransform[1]*zoom)
    gridy = np.arange(adfGeoTransform[3], py, adfGeoTransform[5]*zoom)
    
    z, ss = OK.execute("grid", gridx, gridy)
    if 'int8' in z.dtype.name:
        print(1)
    else:
        print(2)
    end = time.time()
    print('execute done',end-start)
    start = time.time()
    run.write_img(resultDataSetPath+outputKrigingTifName + '.png',projection, geotransform, z,zoom)
    end = time.time()
    print('write done',end-start)

def removeFile(removeTifFileFolder, removeTifName):
    filePathAndName = removeTifFileFolder + removeTifName
    os.remove(filePathAndName)

if __name__ == "__main__":
    # 样本点数据
	InputExcelPathAndName = "test_Points.xlsx"
	# 保存x坐标的表头
	X_coordinateField = 'x_coor'
	# 保存y坐标的表头
	Y_coordinateField = 'y_coor'
	# 插值点的值
	Sample_valueField = 'net'
	# 参考tif（提供插值的栅格数和行列号）
	# 参考tif所在的文件夹
	tifDataPath = ''
	# 参考tif的名字
	tifName = 'DSM4_double_min.tif'
	
	# 克里金插值结果保存的名字
	outputKrigingTifName = 'KrigingInterpolate'
	
    
	# ************************** 运行克里金插值函数 ************************ #

    
	KrigingInterpolate(InputExcelPathAndName, X_coordinateField, Y_coordinateField, Sample_valueField,
	                       tifDataPath, tifName, outputKrigingTifName)
	
	# 删除不需要的tif
	# removeTifFileFolder = ''
	# removeTifName = 'regressionTN.tif'
	# removeFile(removeTifFileFolder, removeTifName)
