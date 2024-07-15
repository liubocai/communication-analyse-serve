import csv
import pandas as pd
from configparser import ConfigParser

# 创建解析器对象
config = ConfigParser()
# 读取配置文件
config.read('config.ini')
nameListPath = config.get('DEFAULT', 'nameListPath') #修改为tomcat服务器上的csv文件
linkListPath = config.get('DEFAULT', 'linkListPath')


def csvNodeAdd(category,name,imgName,value):
    df = pd.read_csv(nameListPath,encoding='UTF-8',header=None)
    for i in range(len(df)):
        if(df.iloc[i,1]==name):
            return 'error'
    data=[[category,name,imgName,value]]
    data=pd.DataFrame(data=data)
    data.to_csv(nameListPath,encoding='UTF-8',mode='a',header=False,index=None)
    return 'success'
    # if(nodeFrom):
    #     data=[[nodeFrom,name]]
    #     data=pd.DataFrame(data=data)
    #     data.to_csv(linkListPath,encoding='UTF-8',mode='a',header=False,index=None)
    # if(nodeTo):
    #     data=[[name,nodeTo]]
    #     data=pd.DataFrame(data=data)
    #     data.to_csv(linkListPath,encoding='UTF-8',mode='a',header=False,index=None)
    

def csvNodeUpdate(name,category,newName,imgName,value):
    df = pd.read_csv(nameListPath,encoding='UTF-8',header=None)
    df2 = pd.read_csv(linkListPath,encoding='UTF-8',header=None)
    for i in range(len(df)):
        if(df.iloc[i,1]==name):
            if(category!=''):
                df.iloc[i,0]=category
            if(newName!=''):
                df.iloc[i,1]=newName
                for j in range(len(df2)):
                    if(df2.iloc[j,0]==name):
                        df2.iloc[j,0]=newName
                    if(df2.iloc[j,1]==name):
                        df2.iloc[j,1]=newName
            if(imgName!=''):
                df.iloc[i,2]=imgName
            if(value!=''):
                df.iloc[i,3]=value
            
            
            break
            
    df.to_csv(nameListPath,encoding='UTF-8',mode='w',header=False,index=None)
    df2.to_csv(linkListPath,encoding='UTF-8',mode='w',header=False,index=None)
    return 'success'

def csvNodeDelete(name):
    df = pd.read_csv(nameListPath,encoding='UTF-8',header=None)
    df2 = pd.read_csv(linkListPath,encoding='UTF-8',header=None)
    for i in range(len(df)):
        if(df.iloc[i,1]==name):
            df.drop(i,inplace=True)
            pass
            
            df2=df2[df2[1]!=name]
            df2=df2[df2[0]!=name]

            break
            
    df.to_csv(nameListPath,encoding='UTF-8',mode='w',header=False,index=None)
    df2.to_csv(linkListPath,encoding='UTF-8',mode='w',header=False,index=None)
    return 'success'

def csvLinkAdd(nodeFrom,nodeTo):
    data=[[nodeFrom,nodeTo]]
    data=pd.DataFrame(data=data)
    data.to_csv(linkListPath,encoding='UTF-8',mode='a',header=False,index=None)

    return 'success'

def csvLinkUpdate(nodeFrom,nodeTo,newNodeFrom,newNodeTo):
    df = pd.read_csv(linkListPath,encoding='UTF-8',header=None)
    print(nodeFrom,nodeTo,newNodeFrom,newNodeTo)
    print(df)
    for i in range(len(df)):
        print(i)
        if(df.iloc[i,0]==nodeFrom and df.iloc[i,1]==nodeTo):
            if(newNodeFrom!='' and newNodeTo!=''):
                return 'error'
            if(newNodeFrom!=''):
                df.iloc[i,0]=newNodeFrom
            if(newNodeTo!=''):
                df.iloc[i,1]=newNodeTo
            break
    df.to_csv(linkListPath,encoding='UTF-8',mode='w',header=False,index=None)
    return 'success'

def csvLinkDelete(nodeFrom,nodeTo):
    df = pd.read_csv(linkListPath,encoding='UTF-8',header=None)
    for i in range(len(df)):
        if ((df.iloc[i, 0] == nodeFrom and df.iloc[i, 1] == nodeTo) or
            (df.iloc[i, 0] == nodeTo and df.iloc[i, 1] == nodeFrom)):
            df.drop(i,inplace=True)
            break
    df.to_csv(linkListPath,encoding='UTF-8',mode='w',header=False,index=None)
    return 'success'

