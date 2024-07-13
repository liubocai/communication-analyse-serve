clc;
clear;
speedList=zeros(7,10);
fitnessList=zeros(7,10);
for index=7:7
    selectedRadioList=randperm(7);
    index
    for radioNum=1:7
        radio_pos=xlsread('emradioPos.xlsx',index);

        radio_pos(:,1)=[];
        radio_pos=radio_pos(selectedRadioList(1:radioNum),:);
        [serverNum,~]=size(radio_pos);

        timeList=0;

        best_Points=[];

        %% 读入图像
        tic;
        [dsm_array,dsm_refmat] = readgeoraster("DSM4_double_min.tif");%读取数据

        [building_array,building_refmat] = readgeoraster("building4_min.tif");
        building_array=building_array(:,:,1);
        building_array=bwareaopen(building_array,20);%剔除面积较小的建筑物，设定为20个像素
        not_Building=0;%非建筑物所代表的像素值
        radio_Toground_Dis=1; %电台距离地面的距离

        % mapshow(dsm_array,dsm_refmat)
        cell_width=dsm_refmat.CellExtentInWorldX;
        cell_height=dsm_refmat.CellExtentInWorldY;
        img_X=dsm_refmat.XWorldLimits;
        img_Y=dsm_refmat.YWorldLimits;

        %读取上下左右坐标
        img_X0=img_X(1);
        img_X1=img_X(2);
        img_Y0=img_Y(2);
        img_Y1=img_Y(1);

        [img_height,img_width]=size(building_array);%获得图像大小

        % [i, j, altitude, net] = Point2Ras(246068.11,3382045.28, 20, img_X0, img_Y0, cell_width, cell_height);
        % dsm_array(i,j)

        %% 二值处理提取建筑物
        disp('正在处理建筑物...')
        [building_pos_array,building_Num]=bwlabel(building_array); % 对二维二值图像中的连通分量进行标注
        conncomp=bwconncomp(building_array); % 查找二值图像中的连通分量并对其计数
        building_info=struct(); %用于存储关于建筑物栅格信息

        point_Interval=20; %生成的点的间隔
        %在图像范围内生成一系列测试点用于计算网速
        test_Points=[];
        test_Points_Z=15; %测试点的高程,该高程是相对于模型的高程

        %记录用户的平面坐标位置，用于判断测试点的网速的权值

        for i = floor(img_Y0-point_Interval):-point_Interval:floor(img_Y1+point_Interval)
            for j = floor(img_X0+point_Interval):point_Interval:floor(img_X1-point_Interval)
                %第四列代表点位能获得的最大网速，第五列代表该点是否位于建筑物内，1代表是，0代表不是;
                [tmp_row,tmp_col]=Point2Ras(j, i,img_X0, img_Y0, cell_width, cell_height, dsm_array);
                if building_array(tmp_row,tmp_col)==not_Building
                    test_Points=[test_Points;[j,i,test_Points_Z,0,0]];
                else
                    test_Points=[test_Points;[j,i,test_Points_Z,0,1]];
                end


            end
        end

        [test_Points_Num,~]=size(test_Points); %test_Points_Num


        % 网速衰减方程系数：Y=41.2771-0.0149X_1-0.8211X_2-0.0003795X_1^2
        b0=41.2771;
        b1=-0.0149;
        b2=-0.8211;
        b3=-0.0003795;
        min_net_speed=0; %最小网速速率


        %% 初始化迭代开始前所需要的参数

        userNum=20;
        radioUserRatio=serverNum/userNum;


        %% 开始迭代

        for j =1:serverNum
            serverpoint=[radio_pos(j,1),radio_pos(j,2),radio_pos(j,3)+1];

            for k =1:test_Points_Num
                tespoint=test_Points(k,:);
                %计算穿透距离

                [building_dis,tree_dis]=GetLineNetSpeed(serverpoint(1),serverpoint(2),serverpoint(3), ...
                    tespoint(1),tespoint(2),tespoint(3),img_X0,img_Y0,cell_width,cell_height,dsm_array,building_array);
                net_speed=floor(b0+b1*tree_dis+b2*building_dis+b3*tree_dis*tree_dis);%计算网速
                isLastPointPredicted=0;
                last_building_dis=building_dis;
                if net_speed>min_net_speed && radioUserRatio*net_speed>test_Points(k,4)
                    test_Points(k,4)=radioUserRatio*net_speed;
                end

            end
        end
        sum_speed=sum(test_Points(:,4))/test_Points_Num;
        speedList(radioNum,index)=sum_speed;
        fitness=sum_speed/(1+std(test_Points(:,4)));
        fitnessList(radioNum,index)=fitness;
        timeList=toc;

        %列名称
        col={'X' 'Y' 'Z' 'NET'};
        %生成表格，按列生成
        result_table=table(test_Points(:,1),test_Points(:,2),test_Points(:,3),test_Points(:,4),'VariableNames',col);

        writetable(result_table, ['EM_testPointsNet',num2str(radioNum),'.csv']);
    end
end
