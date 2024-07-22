from flask import Flask, Response, jsonify
from flask import request
import requests
from pymongo import MongoClient
import json
from flask_cors import CORS
import string
import random
from deployment2 import *
import time
from datetime import datetime
import atexit
import socket
import re
from csvData import csvNodeAdd,csvNodeUpdate,csvNodeDelete,csvLinkAdd,csvLinkUpdate,csvLinkDelete
from sklearn.cluster import KMeans, DBSCAN
import traceback
app = Flask(__name__)
CORS(app, resources=r'/*')

def before_app_shutdown():
    if os.path.exists(outputTilesPath):
        shutil.rmtree(outputTilesPath)
atexit.register(before_app_shutdown)

def random_code():
    words = string.ascii_uppercase + string.digits
    sample_chars = random.sample(words, 16)
    password = "".join(sample_chars)
    print(password)
    return password

def save2txt():
    a = 1

@app.route('/')
def hello_world():
    return '...main page...'


@app.route('/register', methods=['POST'])
def Register():
    if request.method == 'POST':
        now = datetime.now().strftime("%Y%m%d%H%M%S")
        req_json = request.args.to_dict()
        if usr_collection.find_one({'user_id': req_json['user_id']}) is None:
            req_json['user_project'] = []
            req_json['register_time'] = now
            usr_collection.insert_one(req_json)
            return "0"
        else:
            return "1"


@app.route('/login', methods=['POST'])
def Login():
    if request.method == 'POST':
        req_json = request.args.to_dict()
        rtn_data = usr_collection.find_one({'user_id': req_json['user_id'], 'user_pwd': req_json['user_pwd']})
        rtn_data['_id'] = str(rtn_data['_id'])
        # print(rtn_data, type(rtn_data))
        if rtn_data is not None:
            rtn = {'code': "0", 'data': rtn_data}
            return json.dumps(rtn)
        else:
            return json.dumps({"code": "1"})


@app.route('/createProject', methods=['POST'])
def Create_project():
    if request.method == 'POST':
        now = datetime.now().strftime("%Y%m%d%H%M%S")
        req_json = json.loads(request.json['data'])
        if pjt_collection.find_one({'projectName': req_json['projectName']}) is None:
            req_json['create_time'] = now
            req_json['members'] = [req_json['userName']]
            rd_code = random_code()
            req_json['projectInviteCode'] = rd_code
            req_json['markers'] = []

            req_json['image'] = ""
            req_json['imageCoordinates'] = {'west': 0, 'east': 0, 'north': 0, 'south': 0}

            pjt_collection.insert_one(req_json)

            usr = usr_collection.find_one({'user_id': req_json['userName']})
            pjt_list = list(usr['user_project'])
            pjt_list.append(
                dict({'title': req_json['projectName'],
                      'createTime': now,
                      'projectInviteCode': rd_code
                      })
            )
            usr['user_project'] = pjt_list
            usr_collection.update_one({'user_id': req_json['userName']}, {'$set': usr})

            return rd_code
        else:
            return "1"


@app.route('/joinProject', methods=['POST'])
def Join_project():
    if request.method == 'POST':
        now = datetime.now().strftime("%Y%m%d%H%M%S")
        req_json = json.loads(request.json['data'])
        print(req_json)
        target_project = pjt_collection.find_one({'projectInviteCode': req_json['projectInviteCode']})
        if target_project is not None:
            req_json['register_time'] = now
            usr_list = list(target_project['members'])
            usr_list.append(req_json['userName'])
            target_project['members'] = usr_list
            pjt_collection.update_one(
                {'projectInviteCode': req_json['projectInviteCode']},
                {'$set': target_project})

            usr = usr_collection.find_one({'user_id': req_json['userName']})
            pjt_list = list(usr['user_project'])
            pjt_list.append(
                dict({'title': target_project['projectName'],
                      'createTime': now,
                      'projectInviteCode': req_json['projectInviteCode']
                      })
            )
            usr['user_project'] = pjt_list
            usr_collection.update_one({'user_id': req_json['userName']}, {'$set': usr})

            return "0"
        else:
            return "1"


@app.route('/getProjects', methods=['GET'])
def Get_project():
    if request.method == 'GET':
        req_json = request.args.to_dict()
        get_usr_json = usr_collection.find_one({'user_id': req_json['userName']})
        if get_usr_json is not None:
            edited_pjts = get_usr_json['user_project']
            for i in range(len(edited_pjts)):
                time = edited_pjts[i]['createTime']
                edited_pjts[i]['createTime'] = time[:4] + "-" + time[4:6] + "-" + time[6:8] + " " + \
                                               time[8:10] + ":" + time[10:12] + ":" + time[12:14]

            # print(get_usr_json['user_project'])
            # return json.dumps(get_usr_json['user_project'])
            return json.dumps(edited_pjts)
        else:
            return "1"


@app.route('/getProjectMembers', methods=['GET'])
def Get_project_members():
    if request.method == 'GET':
        req_json = request.args.to_dict()
        pjt_json = pjt_collection.find_one({'projectInviteCode': req_json['projectInviteCode']})
        if pjt_json is not None:
            rtn_json_list = []
            members = list(pjt_json['members'])
            print(members)
            for m in members:
                usr_json = usr_collection.find_one({'user_id': m})

                if m == pjt_json['userName']:
                    if_leader = "项目组长"
                else:
                    if_leader = "项目成员"
                phone = usr_json['user_phone']
                email = usr_json['user_email']
                time = "unknown"
                for pjt in usr_json['user_project']:
                    if pjt['projectInviteCode'] == req_json['projectInviteCode']:
                        time = pjt['createTime']
                time = time[:4] + "-" + time[4:6] + "-" + time[6:8] + " " + \
                       time[8:10] + ":" + time[10:12] + ":" + time[12:14]
                rtn_json_list.append({
                    'name': m,
                    'if_leader': if_leader,
                    'phone': phone,
                    'email': email,
                    'time': time,
                })
            return str(rtn_json_list)
        else:
            return "1"


@app.route('/uploadImage', methods=['POST'])
def Upload_image():
    if request.method == 'POST':
        req_json = request.args.to_dict()
        print(req_json)
        get_pjt_json = pjt_collection.find_one({'projectInviteCode': req_json['projectInviteCode']})

        if get_pjt_json is not None:
            print(request.files)
            now = datetime.now().strftime("%Y%m%d%H%M%S")

            # update coordinates
            get_pjt_json['imageCoordinates']['west'] = req_json['west']
            get_pjt_json['imageCoordinates']['east'] = req_json['east']
            get_pjt_json['imageCoordinates']['north'] = req_json['north']
            get_pjt_json['imageCoordinates']['south'] = req_json['south']

            img = request.files.get('file')  # 从post请求中获取图片数据
            img_path = "E://server//image_db//" \
                       + req_json['projectInviteCode'] + "_" + str(now) + ".png"
            img.save(img_path)
            get_pjt_json['image'] = img_path
            pjt_collection.update_one({'projectInviteCode': req_json['projectInviteCode']}, {'$set': get_pjt_json})
            return "http://127.0.0.1:8092/images/" + req_json['projectInviteCode'] + "_" + str(now) + ".png"
        else:
            return "1"


@app.route('/getImageInfo', methods=['GET'])
def Get_image_info():
    if request.method == 'GET':
        req_json = request.args.to_dict()
        get_pjt_json = pjt_collection.find_one({'projectInviteCode': req_json['projectInviteCode']})
        if get_pjt_json['image'] == "":
            return "1"
        img_url = "http://127.0.0.1:8092/images/" + get_pjt_json['image'].split("//")[-1]
        if get_pjt_json is not None:
            return json.dumps({'url': img_url, 'coordinates': get_pjt_json['imageCoordinates']})
        else:
            return "1"


@app.route("/images/<projectInviteCode>.png")
def Get_image(projectInviteCode):
    if projectInviteCode is None:
        return "1"
    # 去对应的文件夹找到对应名字的图片
    # print(projectInviteCode)
    # img_code = projectInviteCode.split("_")[0]
    with open(r'E://server//image_db//{}.png'.format(projectInviteCode), 'rb') as f:
        image = f.read()
        resp = Response(image, mimetype="image/png")
        return resp


@app.route("/markerImages/<projectInviteCode>.png")
def Get_marker_image(projectInviteCode):
    if projectInviteCode is None:
        return "1"
    # 去对应的文件夹找到对应名字的图片
    # print(projectInviteCode)
    # img_code = projectInviteCode.split("_")[0]
    with open(r'E://server//marker_image_db//{}.png'.format(projectInviteCode),
              'rb') as f:
        image = f.read()
        resp = Response(image, mimetype="image/png")
        return resp


@app.route('/getMarkers', methods=['GET'])
def Get_markers():
    if request.method == 'GET':
        req_json = request.args.to_dict()
        get_pjt_json = pjt_collection.find_one({'projectInviteCode': req_json['projectInviteCode']})
        print(get_pjt_json['markers'])
        if len(get_pjt_json['markers']) == 0:
            return "1"
        else:
            return str(get_pjt_json['markers'])
    return "1"


@app.route('/publishMarker', methods=['POST'])
def Post_marker():
    if request.method == 'POST':
        now = datetime.now().strftime("%Y%m%d%H%M%S")
        now_formatted = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        req_json = request.args.to_dict()
        target_project_json = pjt_collection.find_one({'projectInviteCode': req_json['projectInviteCode']})
        if target_project_json is not None:
            marker_list = target_project_json['markers']
            img = request.files.get('file')  # 从post请求中获取图片数据
            img_path = "E://server//marker_image_db//" \
                       + req_json['projectInviteCode'] + "_" + now + ".png"
            img.save(img_path)

            img_url = "http://127.0.0.1:8092/markerImages/" + req_json['projectInviteCode'] + "_" + now + ".png"

            new_marker = {'user_id': req_json['userName'], 'markerName': req_json['markerName'],
                          'type': req_json['type'], 'description': req_json['description'], 'time': now_formatted,
                          'lat': req_json['lat'], 'lng': req_json['lng'], 'image_path': img_url}
            marker_list.append(new_marker)

            target_project_json['markers'] = marker_list
            pjt_collection.update_one({'projectInviteCode': req_json['projectInviteCode']},
                                      {'$set': target_project_json})

            return "0"
    return "1"


@app.route('/deleteMarker', methods=['DELETE'])
def Del_marker():
    if request.method == 'DELETE':
        req_json = request.args.to_dict()
        markerName = req_json['markerName']
        target_project_json = pjt_collection.find_one({'projectInviteCode': req_json['projectInviteCode']})
        if target_project_json is not None:
            markers = target_project_json['markers']
            print(target_project_json)
            for i in range(len(markers)):
                print(markers[i])
                if markers[i]['markerName'] == markerName:
                    del markers[i]
                    break
            target_project_json['markers'] = markers

            pjt_collection.delete_one({'projectInviteCode': req_json['projectInviteCode']})
            pjt_collection.insert_one(target_project_json)
            return "0"

    return "1"


@app.route("/resultimages/<projectInviteCode>.png")
def Get_ResImage(projectInviteCode):
    if projectInviteCode is None:
        return "1"
    # 去对应的文件夹找到对应名字的图片
    # print(projectInviteCode)
    # img_code = projectInviteCode.split("_")[0]
    with open(r'C:\workspace\cesiumChooseDot\server//resultimg_db//{}.png'.format(projectInviteCode), 'rb') as f:
        image = f.read()
        resp = Response(image, mimetype="image/png")
        return resp

@app.route('/uploadRadioPos', methods=['POST'])
def UploadRadioPos():
    if request.method == 'POST':
        # 获取参数
        req_json = json.loads(request.data)
        recvData = req_json['data']
        recvData = eval(recvData)
        print("uploadRadioPos", recvData)

        # 解析参数
        radioPosList = recvData['radioPos']
        tifName = recvData['tifname']
        dis = float(recvData['samplePointInterval'])
        r = int(recvData['maxComputeRadioDistance'])
        tifFilePath = tifFileDir + tifName
        radioPos=[]
        for i in range(len(radioPosList)):
            radioPos.append([float(radioPosList[i]['lon']),float(radioPosList[i]['lat']),float(radioPosList[i]['height'])])
        print(radioPos)

        a = deploy(tifFilePath, radioPos)
        #检查计算的范围是否合理
        rentangles = a.main2(r, dis)
        print("rentangles",rentangles)
        img_url = "http://127.0.0.1:8092/resultimages/result_img.png"

        return json.dumps({'url': img_url, 'done':1, 'rectangles':rentangles})



@app.route('/analysePlanRadio', methods=['POST'])
def analysePlanRadio():
    #解析入参：现有的radioPos列表， 以及预设的要放电台的类型和高度 h 列表（目前只接受1个）
    req_json = json.loads(request.data)
    recvData = req_json['data']
    recvData = eval(recvData)
    print("analysePlanRadio", recvData)
    # 解析参数
    recvRadiopos = recvData['radioPos']
    tifName = recvData['tifname']
    tifFilePath = tifFileDir+tifName
    maxFlyNum = int(recvData['maxFlyNum'])
    maxFlyHeight = float(recvData['maxFlyHeight'])
    maxGroundNum = int(recvData['maxGroundNum'])
    maxGroundHeight = float(recvData['maxGroundHeight'])
    dis = int(recvData['samplePointInterval'])
    r = float(recvData['maxComputeRadioDistance'])
    print(maxFlyNum,maxFlyHeight,maxGroundNum,maxGroundHeight)
    radioPos = []
    for i in range(len(recvRadiopos)):
        radioPos.append(
            [float(recvRadiopos[i]['lon']), float(recvRadiopos[i]['lat']), float(recvRadiopos[i]['height'])])
    # 该方法局部变量，确定几个点，该点用什么类
    #计算要放的电台
    a = deploy(tifFilePath, radioPos)

    tempt=np.array(a.radioposGrid)
    bounds = [(np.min(tempt[:,0]), np.min(tempt[:,1])), (np.max(tempt[:,0]), np.max(tempt[:,1]))]  # 参数范围

    # num_particles = 500  # 粒子数量
    max_iter = 100  # 最大迭代次数
    w = 0.9  # 惯性权重
    c1 = 2  # 学习因子 1
    c2 = 2  # 学习因子 2

    Y = np.array(a.radioposMeter)
    # 判断需要的补点的类型和个数
    # radioposs是经纬度，Y是三维坐标

    num_uav = 0
    num_ground = 0
    turn = 0
    find = False
    # 回传结果
    planRadiosGround = np.empty(shape=(0, 3))
    planRadiosFly = np.empty(shape=(0, 3))
    adjacency_list_final = {}
    result_all_final = np.empty(shape=(0, 3))
    rectangles = []
    while not find and num_uav <= maxFlyNum and num_ground <= maxGroundNum:
        if num_uav < maxFlyNum and turn == 0:
            num_uav += 1
            turn = 1
        elif num_ground < maxGroundNum and turn == 1:
            num_uav -= 1
            num_ground += 1
            turn = 0
        elif num_uav < maxFlyNum and turn == 1:
            num_uav += 1
        elif num_ground < maxGroundNum and turn == 0:
            num_ground += 1
        elif num_ground == maxGroundNum and num_uav == maxFlyNum:
            break
        else:
            break
        num_particles = 200+120*(num_uav+num_ground) if (num_ground+num_uav)<=5 else 800
        best_position, best_score, adjacency_list, num_in = pso(radioPos, Y, bounds, num_particles, max_iter, w, c1, c2, maxFlyHeight, maxGroundHeight,
                                        num_uav, num_ground, tifFilePath, a)
        res = np.zeros(3)
        print("全局最优得分:", best_score, "联通数：",-num_in)
        if (num_in > -(num_uav + num_ground + len(radioPos))):
            print("uav:", num_uav, "ground", num_ground, "时无满足解")
            continue

        print("uav:", num_uav, "ground", num_ground, "时满足解")
        print("全局最优解:", best_position)
        adjacency_list_final = adjacency_list
        result_all = np.array(radioPos)

        for i in range(num_uav):
            print("无人机坐标为：", a.imgLeftUpX + best_position[2 * i + 1] * a.imgCellWidth,
                  a.imgLeftUpY - best_position[2 * i] * a.imgCellHeight, maxFlyHeight)
            res[0] = a.imgLeftUpX + best_position[2 * i + 1] * a.imgCellWidth
            res[1] = a.imgLeftUpY - best_position[2 * i] * a.imgCellHeight
            tempGroundAltitude = a.imgArray[int(best_position[2*i])][int(best_position[2*i+1])]
            res[2] = maxFlyHeight+ (tempGroundAltitude if tempGroundAltitude >=0 else 0)
            # res[2] = maxFlyHeight
            result = a.meter2latlng(res)
            result = np.array(result)
            result = np.append(result, res[2])
            planRadiosFly = np.vstack((planRadiosFly, result))


        for i in range(num_uav, num_uav + num_ground):
            print("地面电台坐标为：", a.imgLeftUpX + best_position[2 * i + 1] * a.imgCellWidth,
                  a.imgLeftUpY - best_position[2 * i] * a.imgCellHeight, maxGroundHeight)
            res[0] = a.imgLeftUpX + best_position[2 * i + 1] * a.imgCellWidth
            res[1] = a.imgLeftUpY - best_position[2 * i] * a.imgCellHeight
            tempGroundAltitude = a.imgArray[int(best_position[2*i])][int(best_position[2*i+1])]
            res[2] = maxGroundHeight+ (tempGroundAltitude if tempGroundAltitude >=0 else 0)
            # 得到的米没问题，也是x，y
            result = a.meter2latlng(res)
            result = np.array(result)
            result = np.append(result, res[2])
            planRadiosGround = np.vstack((planRadiosGround, result))
        result_all = np.vstack((result_all, planRadiosFly))
        result_all = np.vstack((result_all, planRadiosGround))
        result_all_final = result_all
        print("result_all_final", result_all_final)
        aaa = deploy(tifFilePath, list(result_all))
        rectangles = aaa.main2(r, dis)
        find = True

    # 回传结果
    print("adjacency_list_final",adjacency_list_final)
    print("result_all_final",result_all_final)
    lines = []
    for jacency in list(adjacency_list_final.keys()):
        for point in adjacency_list_final[jacency]:
            if int(point) > int(jacency):
                lines.append(np.concatenate((result_all_final[int(point)], result_all_final[int(jacency)])).tolist())
    print("lines",lines)
    print("rectangles",rectangles)
    planResult = []
    for pos in list(planRadiosFly):
        planResult.append({'lon': round(pos[0], 6), 'lat': round(pos[1], 6), 'height': round(pos[2], 1), 'prtype': "空中"})
    for pos in list(planRadiosGround):
        planResult.append({'lon': round(pos[0],6), 'lat': round(pos[1],6), 'height':round(pos[2],1), 'prtype': "地面"})

    # planResult = [{'lon': 114.123456, 'lat': 30.654321, 'height': 100.2, 'prtype': "空中"},
    #               {'lon': 114.123456, 'lat': 30.654321, 'height': 100.2, 'prtype': "地面"}]
    # 保存结果
    if len(planResult)>0:
        #保存内容
        # 获取当前时间作为文件名
        current_time = time.strftime("%Y-%m%d-%H-%M-%S", time.localtime())
        file_name = resultFileDir + current_time + ".txt"

        # 检查是否存在同名文件，如果存在则删除
        if os.path.exists(file_name):
            os.remove(file_name)

        # 写入数据到txt文件
        with open(file_name, "w") as file:
            for item in planResult:
                line = ', '.join([f"{key}: {value}" for key, value in item.items()])
                file.write(line + "\n")

        print(f"数据已成功写入文件：{file_name}")
        #原始的radioPos输入数据、输入的4个参数、计算的分析补点的列表

    img_url = "http://127.0.0.1:8092/resultimages/result_img.png"
    return json.dumps({'url': img_url, 'plan':planResult, 'find':1 if find else 0, 'lines':lines, 'rectangles':rectangles})



global_token = ""
def get_token():
    response = requests.get("http://192.168.5.61/api/wrtmng/1/user/login?username=admin&password=admin")
    if response.status_code == 200:
        res = json.loads(response.text)
        if res["status"] == "success":
            global global_token
            global_token = res["result"]["token"]
        else:
            print({"code":501, "msg":"connect radio error"})
            return 501
    else:
        print({"code":500, "msg":"server error"})
        return 500

# @app.before_first_request
# def before_first_request():
#     get_token()

@app.route('/testtcp2', methods=['GET'])
def testtcp2():
    global global_token
    print("old"+global_token)
    # token没有初始化
    if global_token == "" or global_token == None:
        code = get_token()
        print("new" + global_token)
        if code == 500:
            return json.dumps({"code":500, "msg":"server error"})
        if code == 501:
            return json.dumps({"code":501, "msg":"connect radio error"})

    url = "http://192.168.5.61/api/wrtmng/1/dev/status?&name=io.gnss&args=mesh&token=" + global_token
    response = requests.get(url)
    res = json.loads(response.text)

    print(res)
    #授权过期
    if res["status"] == "error" and res["error"] == "Auth failed!":
        code = get_token()
        if code == 500:
            return json.dumps({"code":500, "msg":"server error"})
        if code == 501:
            return json.dumps({"code":501, "msg":"connect radio error"})
        url = "http://192.168.5.61/api/wrtmng/1/dev/status?&name=io.gnss&args=mesh&token=" + global_token
        response = requests.get(url)
        res = json.loads(response.text)
        print("new" + global_token)
    #业务逻辑
    poss = {} # {"ip":{"lon":lon,"lat":lat,"height":height}}
    for device in res["result"]["status"]["devices"]:
        pos = {}
        pos['lon'] = float(extract_number(device['gnss']['longitude']))/100
        pos['lat'] = float(extract_number(device['gnss']['latitude']))/100
        pos['height'] = float(extract_number(device['gnss']['altitude']))
        poss[device["ip"].split('/')[0]] = pos
    return json.dumps(poss)

def extract_fields(string, fields):
    results = {}
    for field in fields:
        pattern = r'"{}"\s*:\s*"([^"]+)"'.format(field)
        match = re.search(pattern, string)
        if match:
            results[field] = match.group(1)
        else:
            results[field] = None
    return results
def extract_number(string):
    pattern = r'(\d+\.\d+)'
    match = re.search(pattern, string)
    if match:
        return match.group(1)
    else:
        return None


@app.route('/csvNode', methods=['POST'])
def addNewNode():
    category = request.args.get('category', '')  # 必须,节点类别
    name = request.args.get('name', '')  # 必须，节点名字
    imgName = request.args.get('imgName', '')  # 必须，节点图片名字
    value = request.args.get('value', '')  # 必须，节点的值

    msg = csvNodeAdd(category, name, imgName, value)
    return msg


# 根据name修改
@app.route('/csvNode', methods=['PUT'])
def updateNode():
    name = request.args.get('name', '')  # 必须，节点名字
    category = request.args.get('category', '')  # 非必须
    newName = request.args.get('newName', '')  # 非必须，节点的新名字
    imgName = request.args.get('imgName', '')  # 非必须
    value = request.args.get('value', '')  # 非必须

    msg = csvNodeUpdate(name, category, newName, imgName, value)
    return msg


# 根据name删除
@app.route('/csvNode', methods=['DELETE'])
def deleteNode():
    name = request.args.get('name', '')  # 必须，节点名字

    msg = csvNodeDelete(name)
    return msg


@app.route('/csvLink', methods=['POST'])
def addLink():
    nodeFrom = request.args.get('nodeFrom', '')  # 必须，link的出发点
    nodeTo = request.args.get('nodeTo', '')  # 必须，link的终止点

    msg = csvLinkAdd(nodeFrom, nodeTo)
    return msg


@app.route('/csvLink', methods=['PUT'])
def updateLink():
    nodeFrom = request.args.get('nodeFrom', '')  # 必须
    nodeTo = request.args.get('nodeTo', '')  # 必须

    newNodeFrom = request.args.get('newNodeFrom', '')  # 和下面的参数二选一，否则返回error
    newNodeTo = request.args.get('newNodeTo', '')  # 和上面的参数二选一，否则返回error

    msg = csvLinkUpdate(nodeFrom, nodeTo, newNodeFrom, newNodeTo)
    return msg


@app.route('/csvLink', methods=['DELETE'])
def deleteLink():
    nodeFrom = request.args.get('nodeFrom', '')  # 必须
    nodeTo = request.args.get('nodeTo', '')  # 必须

    msg = csvLinkDelete(nodeFrom, nodeTo)
    return msg
@app.route('/Km', methods=['POST'])
def Kmeans():
    data = request.json.get('data', '')
    K = int(request.json.get('K', ''))
    positions = np.array(data, dtype=np.float64)
    n_init = 10
    max_iter = 300
    best_kmeans = None
    min_inertia = float('inf')
    for _ in range(n_init):
        kmeans = KMeans(n_clusters=K, init='k-means++', max_iter=max_iter, n_init=1)
        kmeans.fit(positions)
        inertia = kmeans.inertia_
        if inertia < min_inertia:
            min_inertia = inertia
            best_kmeans = kmeans
    clusters = {}
    for idx, label in enumerate(best_kmeans.labels_):
        label = int(label)
        if label not in clusters:
            clusters[label] = []
        clusters[label].append(positions[idx].tolist())
    return jsonify(clusters)
@app.route('/DBSCAN', methods=['POST'])
def DBSCAN():
    data = request.json.get('data', '')
    eps = float(request.json.get('eps', ''))
    min_samples = int(request.json.get('min_samples', ''))
    print(eps, min_samples)
    positions = np.array(data, dtype=np.float64)
    db = DBSCAN(eps=eps, min_samples=min_samples)
    db.fit(positions)
    labels = db.labels_
    clusters = {}
    for idx, label in enumerate(labels):
        label = int(label)
        if label == -1:
            continue
        if label not in clusters:
            clusters[label] = []
        clusters[label].append(positions[idx].tolist())
    return jsonify(clusters)
if __name__ == '__main__':
    # 连接MongoDB
    client = MongoClient('mongodb://localhost:27017/?readPreference=primary&appname=MongoDB%20Compass&ssl=false')
    db = client['mydb']
    evt_collection = db['event']
    usr_collection = db['user']
    pjt_collection = db['project']
    img_collection = db['image']
    app.run(host="0.0.0.0", port=8092)
    # get_token()
