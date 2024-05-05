# myapp/views.py

import base64
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from pyecharts.render import make_snapshot
from snapshot_selenium import snapshot
from pyecharts.charts import Line
from pyecharts import options as opts  # 导入 opts 模块

def index(request):
    return render(request, 'index.html')

def chart(request):
    return render(request, 'chart.html')

def calculate_grade(value, thresholds):
    """
    根据值和阈值列表计算等级
    :param value: 参数值
    :param thresholds: 阈值列表，格式为 [(阈值1, 等级1), (阈值2, 等级2), ...]
    :return: 对应的等级
    """
    for threshold, grade in thresholds:
        if value < threshold:
            return grade
    return thresholds[-1][1]

def generate_line_chart(grades):
    """
    生成折线图，并返回生成的图表的 Base64 编码
    :param grades: 参数等级字典，格式为 {'hotWaterFlow': grade1, 'hotWaterTemperature': grade2, ...}
    :return: 生成的图表的 Base64 编码
    """
    # 参数名称
    parameters = ['热水涌出量', '热水涌出温度', '高温围岩温度', '温度', '湿度', '高温围岩长度', '热水涌出时长']
    
    # 参数等级
    grade_values = list(grades.values())
    
    # 生成折线图
    line = (
        Line()
        .add_xaxis(parameters)
        .add_yaxis("参数等级", grade_values, markpoint_opts=opts.MarkPointOpts(data=[opts.MarkPointItem(type_="max"), opts.MarkPointItem(type_="min")]))
        .set_global_opts(title_opts=opts.TitleOpts(title="参数等级折线图"))
    )
    
    # 将折线图转换为 HTML
    chart_path = "templates/chart.html"
    line.render(chart_path)

    return chart_path

def calculate_environment_score(grades):
    # 定义各因子的权重
    weights = {
        'hotWaterFlow': 0.0631,
        'hotWaterTemperature': 0.1085,
        'rockTemperature': 0.1210,
        'temperature': 0.3558,
        'humidity': 0.2738,
        'rockLength': 0.0444,
        'waterDuration': 0.0334
    }
    
    # 计算每个因子的等级分数乘以权重，并累加
    total_score = sum(grades[factor] * weights[factor] for factor in grades)
    
    return total_score

def calculate_moist_heat_level(environment_score):
    # 湿热强度等级表
    level_table = {
        '一级湿热': (0, 1),
        '二级湿热': (1, 2),
        '三级湿热': (2, 3),
        '四级湿热': (3, 4),
        '五级湿热': (4, 5)
    }
    
    # 根据湿热强度总分确定湿热强度等级
    for level, (lower_bound, upper_bound) in level_table.items():
        if lower_bound <= environment_score < upper_bound:
            return level
    
    # 如果总分不在任何等级范围内，默认返回最高等级
    return '五级湿热'

def calculate_view(request):
    if request.method == 'POST':
        # 获取表单数据
        hot_water_flow = float(request.POST.get('hotWaterFlow', 0))
        hot_water_temperature = float(request.POST.get('hotWaterTemperature', 0))
        rock_temperature = float(request.POST.get('rockTemperature', 0))
        temperature = float(request.POST.get('temperature', 0))
        humidity = float(request.POST.get('humidity', 0))
        rock_length = float(request.POST.get('rockLength', 0))
        water_duration = float(request.POST.get('waterDuration', 0))

        # 定义每个参数的阈值和等级
        thresholds = {
            'hotWaterFlow': [(0.4, 1), (4, 2), (100, 3), (208, 4),(9999999999,5)],
            'hotWaterTemperature': [(40, 1), (45, 2), (50, 3), (60, 4),(9999999999,5)],
            'rockTemperature': [(28, 1), (32, 2), (38, 3), (45, 4),(9999999999,5)],
            'temperature': [(22, 1), (26, 2), (30, 3), (34, 4),(9999999999,5)],
            'humidity': [(30, 1), (40, 2), (50, 3), (60, 4), (80, 5),(9999999999,5)],
            'rockLength': [(50, 1), (100, 2), (150, 3), (200, 4),(9999999999,5)],
            'waterDuration': [(0.5, 1), (1, 2), (1.5, 3), (2, 4),(9999999999,5)]
        }

        # 计算每个参数的等级
        grades = {
            'hotWaterFlow': calculate_grade(hot_water_flow, thresholds['hotWaterFlow']),
            'hotWaterTemperature': calculate_grade(hot_water_temperature, thresholds['hotWaterTemperature']),
            'rockTemperature': calculate_grade(rock_temperature, thresholds['rockTemperature']),
            'temperature': calculate_grade(temperature, thresholds['temperature']),
            'humidity': calculate_grade(humidity, thresholds['humidity']),
            'rockLength': calculate_grade(rock_length, thresholds['rockLength']),
            'waterDuration': calculate_grade(water_duration, thresholds['waterDuration']),
        }

        # 生成折线图并返回生成的图表路径
        generate_line_chart(grades)
        
        score = calculate_environment_score(grades)

        level = calculate_moist_heat_level(score)

        # 返回生成的图表路径给前端
        return JsonResponse({'score': score,'level':level})
    else:
        # 如果请求不是 POST，返回错误
        return JsonResponse({'error': 'Must use POST method'}, status=400)
