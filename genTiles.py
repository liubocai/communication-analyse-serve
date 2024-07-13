import gdal2tiles
import os
# options = { 
#     'zoom':(8,12), # 切片层级 min zoom 5 - max zoom 18
#     'resume':True,
#     'tile_size': 256, # 瓦片大小
#     's_srs': 'PROJCS["CGCS2000 / 3-degree Gauss-Kruger CM 114E",GEOGCS["China Geodetic Coordinate System 2000",DATUM["China_2000",SPHEROID["CGCS2000",6378137,298.257222101,AUTHORITY["EPSG","1024"]],AUTHORITY["EPSG","1043"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4490"]],PROJECTION["Transverse_Mercator"],PARAMETER["latitude_of_origin",0],PARAMETER["central_meridian",114],PARAMETER["scale_factor",1],PARAMETER["false_easting",500000],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["Northing",NORTH],AXIS["Easting",EAST],AUTHORITY["EPSG","4547"]]',
#     'xyz': True,
#     'np_processes':2
# }

# gdal2tiles.generate_tiles('output.tif','./tiles', **options)


def changeName():
    dir = r"C:\tools\apache-tomcat-8.5.82\webapps1\tiles"
    for filename in os.listdir(dir+'\8'):
        if old_str in filename:
            new_filename = filename.replace(old_str, new_str)
            os.rename(os.path.join(directory, filename), os.path.join(directory, new_filename))

if __name__ == '__main__':
    dir = r"C:\workspace\cesiumChooseDot\server\tiles"
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


            
