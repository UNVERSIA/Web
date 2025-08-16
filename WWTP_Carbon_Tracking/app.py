# app.py
import streamlit as st
import pandas as pd
import re
import numpy as np
import math
import time
import os
import sys
import json
from PIL import Image
import plotly.graph_objects as go
from streamlit.components.v1 import html

# 添加src目录到系统路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
# 修复导入问题
from src.carbon_calculator import CarbonCalculator
import src.visualization as vis

# 页面配置
st.set_page_config(page_title="污水处理厂碳足迹追踪系统", layout="wide", page_icon="♻️")
st.title("基于碳核算-碳账户模型的污水处理厂碳足迹追踪与评估系统")
st.markdown("### 第七届全国大学生市政环境AI＋创新实践能力大赛本科生赛道 环抱未来组")
# 初始化session_state
if 'df' not in st.session_state:
    st.session_state.df = None
if 'df_calc' not in st.session_state:
    st.session_state.df_calc = None
if 'selected_month' not in st.session_state:
    st.session_state.selected_month = None
if 'unit_data' not in st.session_state:
    st.session_state.unit_data = {
        "粗格栅": {"water_flow": 10000.0, "energy": 1500.0, "emission": 450.0, "enabled": True},
        "提升泵房": {"water_flow": 10000.0, "energy": 3500.0, "emission": 1050.0, "enabled": True},
        "细格栅": {"water_flow": 10000.0, "energy": 800.0, "emission": 240.0, "enabled": True},
        "曝气沉砂池": {"water_flow": 10000.0, "energy": 1200.0, "emission": 360.0, "enabled": True},
        "膜格栅": {"water_flow": 10000.0, "energy": 1000.0, "emission": 300.0, "enabled": True},
        "厌氧池": {"water_flow": 10000.0, "energy": 3000.0, "TN_in": 40.0, "TN_out": 30.0, "COD_in": 200.0,
                   "COD_out": 180.0, "emission": 1200.0, "enabled": True},
        "缺氧池": {"water_flow": 10000.0, "energy": 3500.0, "TN_in": 30.0, "TN_out": 20.0, "COD_in": 180.0,
                   "COD_out": 100.0, "emission": 1500.0, "enabled": True},
        "好氧池": {"water_flow": 10000.0, "energy": 5000.0, "TN_in": 20.0, "TN_out": 15.0, "COD_in": 100.0,
                   "COD_out": 50.0, "emission": 1800.0, "enabled": True},
        "MBR膜池": {"water_flow": 10000.0, "energy": 4000.0, "emission": 1200.0, "enabled": True},
        "污泥处理车间": {"water_flow": 500.0, "energy": 2000.0, "PAM": 100.0, "emission": 800.0, "enabled": True},
        "DF系统": {"water_flow": 10000.0, "energy": 2500.0, "PAC": 300.0, "emission": 1000.0, "enabled": True},
        "催化氧化": {"water_flow": 10000.0, "energy": 1800.0, "emission": 700.0, "enabled": True},
        "鼓风机房": {"water_flow": 0.0, "energy": 2500.0, "emission": 900.0, "enabled": True},
        "消毒接触池": {"water_flow": 10000.0, "energy": 1000.0, "emission": 400.0, "enabled": True},
        # 新增除臭系统
        "除臭系统": {"water_flow": 0.0, "energy": 1800.0, "emission": 600.0, "enabled": True}
    }
if 'custom_calculations' not in st.session_state:
    st.session_state.custom_calculations = {}
if 'emission_data' not in st.session_state:
    st.session_state.emission_data = {}
if 'df_selected' not in st.session_state:
    st.session_state.df_selected = None
if 'selected_unit' not in st.session_state:
    st.session_state.selected_unit = "粗格栅"
if 'animation_active' not in st.session_state:
    st.session_state.animation_active = True
if 'formula_results' not in st.session_state:
    st.session_state.formula_results = {}
if 'flow_position' not in st.session_state:
    st.session_state.flow_position = 0
if 'water_quality' not in st.session_state:
    st.session_state.water_quality = {
        "COD": {"in": 200, "out": 50},
        "TN": {"in": 40, "out": 15},
        "SS": {"in": 150, "out": 10},
        "flow_rate": 10000
    }
if 'last_clicked_unit' not in st.session_state:
    st.session_state.last_clicked_unit = None
if 'unit_details' not in st.session_state:
    st.session_state.unit_details = {}
if 'flow_data' not in st.session_state:
    st.session_state.flow_data = {
        "flow_rate": 10000,
        "direction": "right"
    }
if 'unit_status' not in st.session_state:
    st.session_state.unit_status = {unit: "运行中" for unit in st.session_state.unit_data.keys()}

# 侧边栏：数据输入与处理
with st.sidebar:
    st.header("数据输入与设置")
    # 上传运行数据（表格）
    data_file = st.file_uploader("上传运行数据（Excel）", type=["xlsx"])
    if data_file:
        try:
            # 读取多级表头（前2行为表头）
            df = pd.read_excel(data_file, header=[0, 1])
            # 合并多级表头为单级列名
            new_columns = []
            for col in df.columns:
                part1 = str(col[0]).strip()  # 第一行表头（指标名）
                part2 = str(col[1]).strip() if not pd.isna(col[1]) else ""  # 第二行表头（状态/单位）
                # 改进合并规则：去除多余空格和换行符
                merged_col = f"{part1}_{part2}" if part2 else part1
                merged_col = re.sub(r'\s+', ' ', merged_col)  # 替换多个空格为单个空格
                merged_col = merged_col.replace('\n', '')  # 移除换行符
                new_columns.append(merged_col)
            df.columns = new_columns
            # 调试：显示合并后的列名
            st.subheader("合并后的列名")
            col_dict = {i: col for i, col in enumerate(df.columns)}
            st.write(col_dict)  # 使用字典格式显示列名
            # 列名映射（根据实际列名调整）
            date_col_candidates = [col for col in df.columns if "日期" in col]
            if not date_col_candidates:
                st.error("错误：表格中未找到包含'日期'的列，请检查表格结构！")
                st.stop()
            date_col = date_col_candidates[0]  # 自动获取日期列实际名称
            # 修正映射关系（根据实际列名）
            column_mapping = {
                date_col: "日期",
                "处理水量 m3/d_Unnamed: 1_level_1": "处理水量(m³)",
                "能耗 kWh/d_Unnamed: 2_level_1": "电耗(kWh)",
                "自来水 m³/d_Unnamed: 3_level_1": "自来水(m³/d)",
                "CODcr(mg/l)_进水": "进水COD(mg/L)",
                "CODcr(mg/l)_出水": "出水COD(mg/L)",
                "SS(mg/l)_进水": "进水SS(mg/L)",
                "SS(mg/l)_出水": "出水SS(mg/L)",
                "NH3-N(mg/l)_进水": "进水NH3-N(mg/L)",
                "NH3-N(mg/l)_出水": "出水NH3-N(mg/L)",
                "TN(mg/l)_进水": "进水TN(mg/L)",
                "TN(mg/l)_出水": "出水TN(mg/L)",
                "PAC消耗 kg/d_Unnamed: 12_level_1": "PAC投加量(kg)",
                "次氯酸钠消耗 kg/d_Unnamed: 13_level_1": "次氯酸钠投加量(kg)",
                "污泥脱水药剂消耗(PAM) kg/d_Unnamed: 14_level_1": "PAM投加量(kg)",
                "脱水污泥外运量(80%)_Unnamed: 15_level_1": "脱水污泥外运量(80%)"
            }
            # 应用映射
            df = df.rename(columns=column_mapping)
            # 检查必需的列是否存在
            required_columns = [
                "日期", "处理水量(m³)", "电耗(kWh)", "进水COD(mg/L)", "出水COD(mg/L)",
                "进水TN(mg/L)", "出水TN(mg/L)", "PAC投加量(kg)", "次氯酸钠投加量(kg)", "PAM投加量(kg)"
            ]
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                col_dict = {i: col for i, col in enumerate(df.columns)}
                st.error(f"错误：映射后仍缺少以下必需列：{missing_columns}。当前列名：{col_dict}")
                st.stop()
            # 改进日期解析
            if df["日期"].dtype in [np.int64, np.float64]:
                # 处理Excel序列号日期
                base_date = pd.Timestamp("1899-12-30")
                df["日期"] = base_date + pd.to_timedelta(df["日期"], unit='D')
            else:
                # 处理文本格式日期
                df["日期"] = pd.to_datetime(df["日期"], errors="coerce", format='mixed')
            # 处理无效日期
            invalid_rows = df[df["日期"].isna()].index.tolist()
            if invalid_rows:
                st.warning(f"警告：表格第{[i + 3 for i in invalid_rows]}行（表头占2行）日期格式无效，已过滤")
            df = df.dropna(subset=["日期"]).sort_values("日期")
            if len(df) == 0:
                st.error("错误：没有有效日期数据，请检查表格日期格式")
                st.stop()
            # 创建年月选择（动态生成）
            df["年月"] = df["日期"].dt.strftime("%Y年%m月")
            unique_months = df["年月"].unique().tolist()
            st.success(
                f"数据加载成功！共{len(df)}条有效记录（覆盖{df['日期'].dt.year.min()}-{df['日期'].dt.year.max()}年度）")
            # 月份选择器
            selected_month = st.selectbox(
                "选择月份",
                unique_months,
                index=len(unique_months) - 1 if unique_months else 0
            )
            df_selected = df[df["年月"] == selected_month].drop(columns=["年月"])
            st.session_state.df = df  # 存储整个df
            st.session_state.df_selected = df_selected  # 存储选中的月份数据
            st.session_state.selected_month = selected_month
        except Exception as e:
            st.error(f"数据加载错误: {str(e)}")
            st.stop()
    # 工艺优化参数
    st.header("工艺优化模拟")
    aeration_adjust = st.slider("曝气时间调整（%）", -30, 30, 0)
    pac_adjust = st.slider("PAC投加量调整（%）", -20, 20, 0)
    # 动态效果控制
    st.header("动态效果设置")
    st.session_state.animation_active = st.checkbox("启用动态水流效果", value=True)
    st.session_state.flow_data["flow_rate"] = st.slider("水流速度", 1000, 20000, 10000)

# 主界面使用选项卡组织内容
tab1, tab2, tab3, tab4 = st.tabs(["工艺流程仿真", "碳足迹追踪", "碳账户管理", "优化与决策"])


# 工艺流程图HTML组件
def create_plant_diagram(selected_unit=None, flow_position=0, flow_rate=10000, animation_active=True):
    # 创建动态水流效果
    flow_animation = "animation: flow 10s linear infinite;" if animation_active else ""

    # 创建工艺流程图HTML
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>污水处理厂工艺流程</title>
        <style>
            .plant-container {{
                position: relative;
                width: 100%;
                height: 900px;
                background-color: #e6f7ff;
                border: 2px solid #0078D7;
                border-radius: 10px;
                overflow: hidden;
                font-family: Arial, sans-serif;
            }}

            .unit {{
                position: absolute;
                border: 2px solid #2c3e50;
                border-radius: 8px;
                padding: 10px;
                text-align: center;
                cursor: pointer;
                transition: all 0.3s;
                font-weight: bold;
                color: white;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                z-index: 10;
            }}

            .unit:hover {{
                transform: scale(1.05);
                box-shadow: 0 5px 15px rgba(0,0,0,0.3);
                z-index: 20;
            }}

            .unit.active {{
                border: 3px solid #FFD700;
                box-shadow: 0 0 10px #FFD700;
            }}

            .unit.disabled {{
                background-color: #cccccc !important;
                opacity: 0.7;
            }}

            .unit-name {{
                font-size: 15px;
                margin-bottom: 5px;
                text-shadow: 1px 1px 2px rgba(0,0,0,0.7);
            }}

            .unit-status {{
                font-size: 12px;
                padding: 2px 5px;
                border-radius: 3px;
                background-color: rgba(255,255,255,0.2);
            }}

            .pre-treatment {{ background-color: #3498db; }}
            .bio-treatment {{ background-color: #2ecc71; }}
            .advanced-treatment {{ background-color: #e74c3c; }}
            .sludge-treatment {{ background-color: #f39c12; }}
            .auxiliary {{ background-color: #9b59b6; }}
            .effluent-area {{ background-color: #1abc9c; }}

            .flow-line {{
                position: absolute;
                background-color: #1e90ff;
                z-index: 5;
            }}

            .water-flow {{
                position: absolute;
                background: linear-gradient(90deg, transparent, rgba(30, 144, 255, 0.8), transparent);
                {flow_animation}
                z-index: 6;
                border-radius: 3px;
            }}

            .gas-flow {{
                position: absolute;
                background: linear-gradient(90deg, transparent, rgba(169, 169, 169, 0.8), transparent);
                {flow_animation}
                z-index: 6;
                border-radius: 3px;
            }}

            .sludge-flow {{
                position: absolute;
                background: linear-gradient(90deg, transparent, rgba(139, 69, 19, 0.8), transparent);
                {flow_animation}
                z-index: 6;
                border-radius: 3px;
            }}

            .air-flow {{
                position: absolute;
                background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.6), transparent);
                {flow_animation}
                z-index: 6;
                border-radius: 3px;
            }}

            .flow-arrow {{
                position: absolute;
                width: 0;
                height: 0;
                border-style: solid;
                z-index: 7;
            }}

            .flow-label {{
                position: absolute;
                font-size: 13px;
                background: rgba(255, 255, 255, 0.7);
                padding: 2px 5px;
                border-radius: 3px;
                z-index: 8;
            }}

            .special-flow-label {{
                position: absolute;
                color: black;
                font-size: 15px;  /* 这里设置你需要的字体大小 */
                background:none;
            }}

            .particle {{
                position: absolute;
                width: 4px;
                height: 4px;
                border-radius: 50%;
                background-color: #1e90ff;
                z-index: 9;
                opacity: 0.7;
            }}

            .sludge-particle {{
                background-color: #8B4513;
            }}

            .gas-particle {{
                background-color: #A9A9A9;
            }}

            .waste-particle {{
                background-color: #FF6347;
            }}

            .air-particle {{
                background-color: #FFFFFF;
            }}

            .info-panel {{
                position: absolute;
                bottom: 10px;
                left: 10px;
                background-color: rgba(255, 255, 255, 0.9);
                padding: 10px;
                border-radius: 5px;
                border: 1px solid #ccc;
                z-index: 100;
                font-size: 12px;
                max-width: 250px;
            }}

            .bio-deodorization {{
                position: absolute;
                text-align: center;
                font-weight: bold;
                color: #333;
                z-index: 10;
            }}

            /* 区域标注样式 */
            .region-box {{
                position: absolute;
                border: 3px solid;
                border-radius: 10px;
                z-index: 3;
                opacity: 0.3;
            }}

            .region-label {{
                position: absolute;
                font-weight: bold;
                font-size: 16px;
                color: black;
                text-shadow: 1px 1px 2px white;
                z-index: 4;
            }}

            .region-pre-treatment {{
                background-color: rgba(52, 152, 219, 0.3);
                border-color: #3498db;
            }}

            .region-bio-treatment {{
                background-color: rgba(46, 204, 113, 0.3);
                border-color: #2ecc71;
            }}

            .region-advanced-treatment {{
                background-color: rgba(231, 76, 60, 0.3);
                border-color: #e74c3c;
            }}

            .region-sludge-treatment {{
                background-color: rgba(243, 156, 18, 0.3);
                border-color: #f39c12;
            }}

            .region-effluent-area {{
                background-color: rgba(26, 188, 156, 0.3);
                border-color: #1abc9c;
            }}

            @keyframes flow {{
                0% {{ background-position: -100% 0; }}
                100% {{ background-position: 200% 0; }}
            }}

            @keyframes moveParticle {{
                0% {{ transform: translateX(0); }}
                100% {{ transform: translateX(50px); }}
            }}
        </style>
    </head>
    <body>
        <div class="plant-container">
            <!-- 区域标注框 -->
            <!-- 预处理区 -->
            <div class="region-box region-pre-treatment" style="top: 126px; left: 110px; width: 783px; height: 142px;"></div>
            <div class="region-label" style="top: 133px; left: 120px;">预处理区</div>

            <!-- 生物处理区 -->
            <div class="region-box region-bio-treatment" style="top: 400px; left: 490px; width: 415px; height: 140px;"></div>
            <div class="region-label" style="top: 405px; left: 500px;">生物处理区</div>

            <!-- 深度处理区 -->
            <div class="region-box region-advanced-treatment" style="top: 620px; left: 500px; width: 370px; height: 140px;"></div>
            <div class="region-label" style="top: 735px; left: 520px;">深度处理区</div>

            <!-- 泥处理区 -->
            <div class="region-box region-sludge-treatment" style="top: 400px; left: 270px; width: 170px; height: 200px;"></div>
            <div class="region-label" style="top: 405px; left: 280px;">泥处理区</div>

            <!-- 出水区 -->
            <div class="region-box region-effluent-area" style="top: 640px; left: 180px; width: 250px; height: 100px;"></div>
            <div class="region-label" style="top: 650px; left: 190px;">出水区</div>

            <!-- 新增除臭系统区域标注框 -->
            <div class="region-box region-effluent-area" style="top: 282px; left: 26px; width: 135px; height: 160px;"></div>
            <div class="region-label" style="top: 286px; left: 35px;">出水区</div>

            <!-- 工艺单元 -->
            <!-- 第一行：预处理区 -->
            <div class="unit pre-treatment {'disabled' if not st.session_state.unit_data['粗格栅']['enabled'] else ''}" style="top: 160px; left: 150px; width: 90px; height: 60px;" onclick="selectUnit('粗格栅')">
                <div class="unit-name">粗格栅</div>
                <div class="unit-status">{st.session_state.unit_status['粗格栅']}</div>
            </div>

            <div class="unit pre-treatment {'disabled' if not st.session_state.unit_data['提升泵房']['enabled'] else ''}" style="top: 160px; left: 300px; width: 90px; height: 60px;" onclick="selectUnit('提升泵房')">
                <div class="unit-name">提升泵房</div>
                <div class="unit-status">{st.session_state.unit_status['提升泵房']}</div>
            </div>

            <div class="unit pre-treatment {'disabled' if not st.session_state.unit_data['细格栅']['enabled'] else ''}" style="top: 160px; left: 450px; width: 90px; height: 60px;" onclick="selectUnit('细格栅')">
                <div class="unit-name">细格栅</div>
                <div class="unit-status">{st.session_state.unit_status['细格栅']}</div>
            </div>

            <div class="unit pre-treatment {'disabled' if not st.session_state.unit_data['曝气沉砂池']['enabled'] else ''}" style="top: 160px; left: 600px; width: 90px; height: 60px;" onclick="selectUnit('曝气沉砂池')">
                <div class="unit-name">曝气沉砂池</div>
                <div class="unit-status">{st.session_state.unit_status['曝气沉砂池']}</div>
            </div>

            <div class="unit pre-treatment {'disabled' if not st.session_state.unit_data['膜格栅']['enabled'] else ''}" style="top: 160px; left: 750px; width: 90px; height: 60px;" onclick="selectUnit('膜格栅')">
                <div class="unit-name">膜格栅</div>
                <div class="unit-status">{st.session_state.unit_status['膜格栅']}</div>
            </div>

            <!-- 第二行：生物处理区（中行） -->
            <div class="unit bio-treatment {'disabled' if not st.session_state.unit_data['厌氧池']['enabled'] else ''}" style="top: 430px; left: 810px; width: 50px; height: 60px;" onclick="selectUnit('厌氧池')">
                <div class="unit-name">厌氧池</div>
                <div class="unit-status">{st.session_state.unit_status['厌氧池']}</div>
            </div>

            <div class="unit bio-treatment {'disabled' if not st.session_state.unit_data['缺氧池']['enabled'] else ''}" style="top: 430px; left: 750px; width: 50px; height: 60px;" onclick="selectUnit('缺氧池')">
                <div class="unit-name">缺氧池</div>
                <div class="unit-status">{st.session_state.unit_status['缺氧池']}</div>
            </div>

            <div class="unit bio-treatment {'disabled' if not st.session_state.unit_data['好氧池']['enabled'] else ''}" style="top: 430px; left: 690px; width: 50px; height: 60px;" onclick="selectUnit('好氧池')">
                <div class="unit-name">好氧池</div>
                <div class="unit-status">{st.session_state.unit_status['好氧池']}</div>
            </div>

            <div class="unit bio-treatment {'disabled' if not st.session_state.unit_data['MBR膜池']['enabled'] else ''}" style="top: 430px; left: 520px; width: 90px; height: 60px;" onclick="selectUnit('MBR膜池')">
                <div class="unit-name">MBR膜池</div>
                <div class="unit-status">{st.session_state.unit_status['MBR膜池']}</div>
            </div>

            <div class="unit sludge-treatment {'disabled' if not st.session_state.unit_data['污泥处理车间']['enabled'] else ''}" style="top: 430px; left: 300px; width: 90px; height: 60px;" onclick="selectUnit('污泥处理车间')">
                <div class="unit-name">污泥处理车间</div>
                <div class="unit-status">{st.session_state.unit_status['污泥处理车间']}</div>
            </div>

            <!-- 中行最右侧：鼓风机房 -->
            <div class="unit auxiliary {'disabled' if not st.session_state.unit_data['鼓风机房']['enabled'] else ''}" style="top: 430px; left: 930px; width: 90px; height: 60px;" onclick="selectUnit('鼓风机房')">
                <div class="unit-name">鼓风机房</div>
                <div class="unit-status">{st.session_state.unit_status['鼓风机房']}</div>
            </div>

            <!-- 除臭系统单元 -->
            <div class="unit effluent-area {'disabled' if not st.session_state.unit_data['除臭系统']['enabled'] else ''}" style="top: 310px; left: 50px; width: 70px; height: 40px;" onclick="selectUnit('除臭系统')">
                <div class="unit-name">除臭系统</div>
                <div class="unit-status">{st.session_state.unit_status['除臭系统']}</div>
            </div>

            <!-- 第三行：深度处理区 -->
            <div class="unit advanced-treatment {'disabled' if not st.session_state.unit_data['DF系统']['enabled'] else ''}" style="top: 650px; left: 520px; width: 90px; height: 60px;" onclick="selectUnit('DF系统')">
                <div class="unit-name">DF系统</div>
                <div class="unit-status">{st.session_state.unit_status['DF系统']}</div>
            </div>

            <div class="unit advanced-treatment {'disabled' if not st.session_state.unit_data['催化氧化']['enabled'] else ''}" style="top: 650px; left: 740px; width: 90px; height: 60px;" onclick="selectUnit('催化氧化')">
                <div class="unit-name">催化氧化</div>
                <div class="unit-status">{st.session_state.unit_status['催化氧化']}</div>
            </div>

            <!-- 出水区单元 -->
            <div class="unit effluent-area {'disabled' if not st.session_state.unit_data['消毒接触池']['enabled'] else ''}" style="top: 660px; left: 325px; width: 76px; height: 40px;" onclick="selectUnit('消毒接触池')">
                <div class="unit-name">消毒接触池</div>
                <div class="unit-status">{st.session_state.unit_status['消毒接触池']}</div>
            </div>

            <!-- 水流线条与箭头 -->

            <!-- 污泥流向 -->
            <div class="flow-line" style="top: 410px; left: 460px; width: 5px; height: 120px; transform: rotate(90deg); background-color: #8B4513;"></div>
            <div class="flow-line" style="top: 540px; left: 322px; width: 68px; height: 5px; transform: rotate(90deg); background-color: #8B4513;"></div>
            <div class="flow-arrow" style="top: 573px; left: 349px; width: 0; height: 0; border-style: solid;border-width: 7px 7px 0 7px;border-color: #8B4513 transparent transparent transparent;"></div>
            <div class="flow-arrow" style="top: 463px; left: 412px; width: 0; height: 0; border-style: solid;border-width: 7px 7px 7px 0;border-color: transparent #8B4513 transparent transparent;"></div>

            <!-- 鼓风机到MBR膜池的气流 -->
            <div class="flow-line" style="top: 470px; left: 770px; width: 180px; height: 5px; background-color: #999999; opacity: 0.6;"></div>

            <!-- 水流动画 -->
            <div class="water-flow" style="top: 197px; left: 80px; width: 66px; height: 7px;"></div>
            <div class="water-flow" style="top: 197px; left: 270px; width: 30px; height: 7px;"></div>
            <div class="water-flow" style="top: 197px; left: 411px; width: 40px; height: 7px;"></div>
            <div class="water-flow" style="top: 197px; left: 560px; width: 42px; height: 7px;"></div>
            <div class="water-flow" style="top: 197px; left: 709px; width: 42px; height: 7px;"></div>
            <div class="water-flow" style="top: 197px; left: 100px; width: 30px; height: 7px; transform: rotate(180deg);"></div>
            <div class="water-flow" style="top: 197px; left: 290px; width: 30px; height: 7px; transform: rotate(180deg);"></div>
            <div class="water-flow" style="top: 197px; left: 431px; width: 30px; height: 7px; transform: rotate(180deg);"></div>
            <div class="water-flow" style="top: 197px; left: 580px; width: 30px; height: 7px; transform: rotate(180deg);"></div>
            <div class="water-flow" style="top: 197px; left: 729px; width: 30px; height: 7px; transform: rotate(180deg);"></div>
            <div class="water-flow" style="top: 467px; left: 629px; width: 66px; height: 7px;"></div>
            <div class="water-flow" style="top: 197px; left: 850px; width: 56px; height: 7px;"></div>
            <div class="water-flow" style="top: 197px; left: 896px; width: 8px; height: 250px;"></div>
            <div class="water-flow" style="top: 443px; left: 874px; width: 30px; height: 7px;"></div>
            <div class="water-flow" style="top: 685px; left: 850px; width: 50px; height: 7px;"></div>

            <div class="water-flow" style="top: 500px; left: 896px; width: 8px; height: 190px;"></div>
            <div class="water-flow" style="top: 500px; left: 880px; width: 20px; height: 7px;"></div>

            <div class="water-flow" style="top: 685px; left: 626px; width: 125px; height: 7px;"></div>
            <div class="water-flow" style="top: 685px; left: 305px; width: 220px; height: 7px;"></div>
            <div class="water-flow" style="top: 685px; left: 205px; width: 220px; height: 7px;"></div>

            <div class="water-flow" style="top: 510px; left: 575px; width: 8px; height: 200px;"></div>

            <!-- 污泥流动画 -->
            <div class="sludge-flow" style="top: 120px; left: 207px; width: 5px; height: 40px;"></div>
            <div class="sludge-flow" style="top: 120px; left: 508px; width: 5px; height: 40px;"></div>
            <div class="sludge-flow" style="top: 120px; left: 658px; width: 5px; height: 40px;"></div>
            <div class="sludge-flow" style="top: 120px; left: 807px; width: 5px; height: 40px;"></div>
            <div class="flow-arrow" style="top: 123px; left: 204px; width: 0; height: 0; border-style: solid; border-width: 0 6px 6px 6px; border-color: transparent transparent #8B4513 transparent;"></div>
            <div class="flow-arrow" style="top: 123px; left: 505px; width: 0; height: 0; border-style: solid; border-width: 0 6px 6px 6px; border-color: transparent transparent #8B4513 transparent;"></div>
            <div class="flow-arrow" style="top: 123px; left: 655px; width: 0; height: 0; border-style: solid; border-width: 0 6px 6px 6px; border-color: transparent transparent #8B4513 transparent;"></div>
            <div class="flow-arrow" style="top: 123px; left: 804px; width: 0; height: 0; border-style: solid; border-width: 0 6px 6px 6px; border-color: transparent transparent #8B4513 transparent;"></div>


            <!-- 臭气流动画 -->
            <div class="gas-flow" style="top: 243px; left: 202px; width: 6px; height: 100px;"></div>
            <div class="gas-flow" style="top: 243px; left: 503px; width: 6px; height: 100px;"></div>
            <div class="gas-flow" style="top: 243px; left: 652px; width: 6px; height: 100px;"></div>
            <div class="gas-flow" style="top: 243px; left: 802px; width: 6px; height: 190px;"></div>
            <div class="gas-flow" style="top: 340px; left: 350px; width: 6px; height: 100px;"></div>
            <div class="gas-flow" style="top: 340px; left: 570px; width: 6px; height: 100px;"></div>
            <div class="gas-flow" style="top: 340px; left: 35px; width: 800px; height: 4px;"></div>
            <div class="gas-flow" style="top: 340px; left: 660px; width: 150px; height: 3px;"></div>
            <div class="gas-flow" style="top: 352px; left: 90px; width: 6px; height: 61px;"></div>

            <!-- 鼓风机到MBR膜池的气流动画 -->
            <div class="air-flow" style="top: 900px; left: 770px; width: 230px; height: 5px;"></div>

            <!-- 水流箭头 -->
            <div class="flow-arrow" style="top: 193px; left: 136px; border-width: 8px 0 8px 8px; border-color: transparent transparent transparent #1e90ff;"></div>
            <div class="flow-arrow" style="top: 193px; left: 293px; border-width: 8px 0 8px 8px; border-color: transparent transparent transparent #1e90ff;"></div>
            <div class="flow-arrow" style="top: 193px; left: 442px; border-width: 8px 0 8px 8px; border-color: transparent transparent transparent #1e90ff;"></div>
            <div class="flow-arrow" style="top: 193px; left: 593px; border-width: 8px 0 8px 8px; border-color: transparent transparent transparent #1e90ff;"></div>
            <div class="flow-arrow" style="top: 193px; left: 741px; border-width: 8px 0 8px 8px; border-color: transparent transparent transparent #1e90ff;"></div>
            <div class="flow-arrow" style="top: 642px; left: 572px; border-width: 8px 8px 0 8px; border-color: #1e90ff transparent transparent transparent;"></div>

            <div class="flow-arrow" style="top: 464px; left: 633px; border-width: 8px 8px 8px 0; border-color: transparent #1e90ff transparent transparent;"></div>
            <div class="flow-arrow" style="top: 439px; left: 882px; border-width: 8px 8px 8px 0; border-color: transparent #1e90ff transparent transparent;"></div>
            <div class="flow-arrow" style="top: 496px; left: 882px; border-width: 8px 8px 8px 0; border-color: transparent #1e90ff transparent transparent;"></div>
            <div class="flow-arrow" style="top: 682px; left: 423px; border-width: 8px 8px 8px 0; border-color: transparent #1e90ff transparent transparent;"></div>
            <div class="flow-arrow" style="top: 682px; left: 222px; border-width: 8px 8px 8px 0; border-color: transparent #1e90ff transparent transparent;"></div>

            <div class="flow-arrow" style="top: 682px; left: 732px; border-width: 8px 8px 8px 0; border-color: transparent #1e90ff transparent transparent; transform: rotate(180deg);"></div>


            <!-- 臭气箭头 -->
            <div class="flow-arrow" style="top: 410px; left: 85px; border-width: 8px 8px 0 8px; border-color: #A9A9A9 transparent transparent transparent;"></div>
            <div class="flow-arrow" style="top: 334px; left: 144px; border-width: 8px 8px 8px 0; border-color: transparent #A9A9A9 transparent transparent;"></div>
            <div class="flow-arrow" style="top: 464px; left: 883px; border-width: 8px 8px 8px 0; border-color: transparent #A9A9A9 transparent transparent;"></div>


            <!-- 鼓风机到MBR膜池的箭头（白灰色透明） -->
            <div class="flow-arrow" style="top: 450px; left: 775px; border-width: 5px 0 5px 8px; border-color: transparent transparent transparent rgba(255, 255, 255, 0.8);"></div>

            <!-- 流向标签 -->
            <div class="flow-label" style="top: 190px; left: 40px;">污水</div>
            <div class="flow-label" style="top: 540px; left: 308px;">污泥</div>
            <div class="flow-label" style="top: 435px; left: 440px;">污泥S5</div>
            <div class="flow-label" style="top: 290px; left: 180px;">臭气G1</div>
            <div class="flow-label" style="top: 290px; left: 480px;">臭气G2</div>
            <div class="flow-label" style="top: 290px; left: 635px;">臭气G3</div>
            <div class="flow-label" style="top: 290px; left: 780px;">臭气G4</div>
            <div class="flow-label" style="top: 370px; left: 780px;">臭气G5</div>
            <div class="flow-label" style="top: 370px; left: 545px;">臭气G6</div>
            <div class="flow-label" style="top: 370px; left: 325px;">臭气G7</div>
            <div class="flow-label" style="top: 415px; left: 46px;background:none;">处理后的臭气排放</div>
            <div class="flow-label" style="top: 645px; left: 672px;">浓水</div>
            <div class="flow-label" style="top: 710px; left: 672px;">臭氧</div>

            <!-- 排出物标签 -->
            <div class="flow-label" style="top: 100px; left: 185px; background: #FF6347;">栅渣S1</div>
            <div class="flow-label" style="top: 100px; left: 485px; background: #FF6347;">栅渣S2</div>
            <div class="flow-label" style="top: 100px; left: 635px; background: #FF6347;">沉渣S3</div>
            <div class="flow-label" style="top: 100px; left: 785px; background: #FF6347;">栅渣S4</div>
            <div class="flow-label" style="top: 580px; left: 340px; background: none;">外运</div>
            <div class="flow-label" style="top: 675px; left: 190px; background: none;">排河</div>
            <div class="special-flow-label" style="top: 520px; left: 750px;">MBR生物池</div>

            <!-- 动态粒子 -->
            <div class="particle" id="particle1" style="top: 197px; left: 80px;"></div>
            <div class="particle" id="particle2" style="top: 197px; left: 411px;"></div>
            <div class="particle" id="particle3" style="top: 197px; left: 560px;"></div>
            <div class="particle" id="particle4" style="top: 197px; left: 709px;"></div>
            <div class="particle" id="particle5" style="top: 197px; left: 270px;"></div>
            <div class="particle" id="particle6" style="top: 685px; left: 660px;"></div>
            <div class="particle" id="particle7" style="top: 685px; left: 675px;"></div>


            <!-- 信息面板 -->
            <div class="info-panel">
                <h3>当前水流状态</h3>
                <p>流量: {flow_rate} m³/d</p>
                <p>COD: {st.session_state.water_quality["COD"]["in"]} → {st.session_state.water_quality["COD"]["out"]} mg/L</p>
                <p>TN: {st.session_state.water_quality["TN"]["in"]} → {st.session_state.water_quality["TN"]["out"]} mg/L</p>
            </div>
        </div>

        <script>
            // 设置选中单元
            function selectUnit(unitName) {{
                // 高亮显示选中的单元
                document.querySelectorAll('.unit').forEach(unit => {{
                    unit.classList.remove('active');
                }});

                // 找到并高亮选中的单元
                const units = document.querySelectorAll('.unit');
                units.forEach(unit => {{
                    if (unit.querySelector('.unit-name').textContent === unitName) {{
                        unit.classList.add('active');
                    }}
                }});

                // 发送单元选择信息到Streamlit
                if (window.Streamlit) {{
                    window.Streamlit.setComponentValue(unitName);
                }}
            }}

            // 初始化选中单元
            document.addEventListener('DOMContentLoaded', function() {{
                const units = document.querySelectorAll('.unit');
                units.forEach(unit => {{
                    if (unit.querySelector('.unit-name').textContent === "{selected_unit}") {{
                        unit.classList.add('active');
                    }}
                }});

                // 粒子动画
                function animateParticles() {{
                    for (let i = 1; i <= 12; i++) {{
                        const particle = document.getElementById(`particle${{i}}`);
                        if (particle) {{
                            const top = Math.random() * 5;
                            const left = Math.random() * 50;
                            particle.style.animation = `moveParticle ${{1 + Math.random()}}s linear infinite`;
                        }}
                    }}
                    requestAnimationFrame(animateParticles);
                }}
                animateParticles();
            }});
        </script>
    </body>
    </html>
    """
    return html_content


with tab1:
    st.header("2D水厂工艺流程仿真")

    # 创建两列布局
    col1, col2 = st.columns([3, 1])

    with col1:
        # 渲染工艺流程图
        plant_html = create_plant_diagram(
            selected_unit=st.session_state.get('selected_unit', "粗格栅"),
            flow_rate=st.session_state.flow_data["flow_rate"],
            animation_active=st.session_state.animation_active
        )
        html(plant_html, height=920)

        # 处理单元选择事件
        selected_unit = st.session_state.get('last_clicked_unit', "粗格栅")
        if st.session_state.get('component_value'):
            selected_unit = st.session_state.component_value
            st.session_state.last_clicked_unit = selected_unit
            st.session_state.selected_unit = selected_unit
            st.experimental_rerun()

        # 显示当前选中单元
        if selected_unit:
            st.success(f"当前选中单元: {selected_unit}")

    with col2:
        # 根据点击事件或下拉框选择单元
        if st.session_state.get('last_clicked_unit'):
            selected_unit = st.session_state.last_clicked_unit
        else:
            # 下拉框选项中包含除臭系统
            selected_unit = st.selectbox(
                "选择工艺单元",
                list(st.session_state.unit_data.keys()),
                key="unit_selector"
            )
        st.subheader(f"{selected_unit} - 参数设置")
        unit_params = st.session_state.unit_data[selected_unit]
        # 单元开关
        unit_enabled = st.checkbox("启用单元", value=unit_params["enabled"], key=f"{selected_unit}_enabled")
        st.session_state.unit_data[selected_unit]["enabled"] = unit_enabled

        # 更新单元状态文字
        status_text = "运行中" if unit_enabled else "已停用"
        st.session_state.unit_status[selected_unit] = status_text

        # 通用参数
        if "water_flow" in unit_params:
            unit_params["water_flow"] = st.number_input(
                "处理水量(m³)",
                value=unit_params["water_flow"],
                min_value=0.0
            )
        if "energy" in unit_params:
            unit_params["energy"] = st.number_input(
                "能耗(kWh)",
                value=unit_params["energy"],
                min_value=0.0
            )
        # 特殊参数
        if selected_unit in ["厌氧池", "缺氧池", "好氧池"]:
            unit_params["TN_in"] = st.number_input(
                "进水TN(mg/L)",
                value=unit_params["TN_in"],
                min_value=0.0
            )
            unit_params["TN_out"] = st.number_input(
                "出水TN(mg/L)",
                value=unit_params["TN_out"],
                min_value=0.0
            )
            unit_params["COD_in"] = st.number_input(
                "进水COD(mg/L)",
                value=unit_params["COD_in"],
                min_value=0.0
            )
            unit_params["COD_out"] = st.number_input(
                "出水COD(mg/L)",
                value=unit_params["COD_out"],
                min_value=0.0
            )
        if selected_unit == "DF系统":
            unit_params["PAC"] = st.number_input(
                "PAC投加量(kg)",
                value=unit_params["PAC"],
                min_value=0.0
            )
            st.info("次氯酸钠投加量: 100 kg/d")
        if selected_unit == "催化氧化":
            st.info("臭氧投加量: 80 kg/d")
        if selected_unit == "污泥处理车间":
            unit_params["PAM"] = st.number_input(
                "PAM投加量(kg)",
                value=unit_params["PAM"],
                min_value=0.0
            )
        st.subheader(f"{selected_unit} - 当前状态")
        st.metric("碳排放量", f"{unit_params['emission']:.2f} kgCO2eq")
        st.metric("运行状态", status_text)
        if "water_flow" in unit_params:
            st.metric("处理水量", f"{unit_params['water_flow']:.0f} m³")
        if "energy" in unit_params:
            st.metric("能耗", f"{unit_params['energy']:.0f} kWh")
        # 显示单元详情 - 使用可扩展区域
        if selected_unit not in st.session_state.unit_details:
            st.session_state.unit_details[selected_unit] = {
                "description": "",
                "notes": ""
            }
        with st.expander("单元详情", expanded=True):
            st.session_state.unit_details[selected_unit]["description"] = st.text_area(
                "单元描述",
                value=st.session_state.unit_details[selected_unit]["description"],
                height=100
            )
            st.session_state.unit_details[selected_unit]["notes"] = st.text_area(
                "运行笔记",
                value=st.session_state.unit_details[selected_unit]["notes"],
                height=150
            )
        # 显示单元说明
        if selected_unit == "粗格栅":
            st.info("粗格栅主要用于去除污水中的大型固体杂质，防止后续设备堵塞")
        elif selected_unit == "提升泵房":
            st.info("提升泵房将污水提升到足够高度，以便重力流通过后续处理单元")
        elif selected_unit == "厌氧池":
            st.info("厌氧池进行有机物分解和磷的释放，产生少量甲烷")
        elif selected_unit == "好氧池":
            st.info("好氧池进行有机物氧化和硝化反应，是N2O主要产生源")
        elif selected_unit == "DF系统":
            st.info("DF系统进行深度过滤，需要投加PAC等化学药剂")
        elif selected_unit == "污泥处理车间":
            st.info("污泥处理车间进行污泥浓缩和脱水，需要投加PAM等絮凝剂")
        elif selected_unit == "除臭系统":
            st.info("除臭系统处理全厂产生的臭气，减少恶臭排放")
        elif selected_unit == "消毒接触池":
            st.info("消毒接触池对处理后的水进行消毒，确保水质安全")

# 其余选项卡保持不变
with tab2:
    st.header("碳足迹追踪与评估")
    # 如果有选中的数据，进行碳核算计算
    if 'df_selected' in st.session_state and st.session_state.df_selected is not None:
        df_selected = st.session_state.df_selected
        calculator = CarbonCalculator()
        try:
            df_calc = calculator.calculate_direct_emissions(df_selected)
            df_calc = calculator.calculate_indirect_emissions(df_calc)
            df_calc = calculator.calculate_unit_emissions(df_calc)
            st.session_state.df_calc = df_calc
            # 计算单元排放数据（包含除臭系统）
            st.session_state.emission_data = {
                "预处理区": df_calc['pre_CO2eq'].sum(),
                "生物处理区": df_calc['bio_CO2eq'].sum(),
                "深度处理区": df_calc['depth_CO2eq'].sum(),
                "泥处理区": df_calc['sludge_CO2eq'].sum(),
                "出水区": df_calc['effluent_CO2eq'].sum(),
                "除臭系统": df_calc['deodorization_CO2eq'].sum()  # 新增除臭系统
            }
        except Exception as e:
            st.error(f"碳核算计算错误: {str(e)}")
            st.stop()
    # 工艺全流程碳排热力图
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("工艺全流程碳排热力图")
        if st.session_state.emission_data:
            heatmap_fig = vis.create_heatmap_overlay(st.session_state.emission_data)
            st.plotly_chart(heatmap_fig, use_container_width=True)
        else:
            st.warning("请先上传运行数据")
    with col2:
        st.subheader("碳流动态追踪图谱")
        if 'df_calc' in st.session_state and st.session_state.df_calc is not None:
            sankey_fig = vis.create_sankey_diagram(st.session_state.df_calc)
            st.plotly_chart(sankey_fig, use_container_width=True)
        else:
            st.warning("请先上传运行数据")
    # 碳排放效率排行榜
    if 'df_calc' in st.session_state and st.session_state.df_calc is not None:
        st.subheader("碳排放效率排行榜")
        eff_fig = vis.create_efficiency_ranking(st.session_state.df_calc)
        st.plotly_chart(eff_fig, use_container_width=True)

with tab3:
    st.header("碳账户管理")
    if 'df_calc' in st.session_state and st.session_state.df_calc is not None:
        df_calc = st.session_state.df_calc
        # 碳账户明细（包含除臭系统）
        st.subheader("碳账户收支明细（当月）")
        account_df = pd.DataFrame({
            "工艺单元": ["预处理区", "生物处理区", "深度处理区", "泥处理区", "出水区", "除臭系统"],
            "碳流入(kgCO2eq)": [
                df_calc['energy_CO2eq'].sum() * 0.3193,
                df_calc['energy_CO2eq'].sum() * 0.4453,
                df_calc['energy_CO2eq'].sum() * 0.1155 + df_calc['chemicals_CO2eq'].sum(),
                df_calc['energy_CO2eq'].sum() * 0.0507,
                df_calc['energy_CO2eq'].sum() * 0.0672,
                df_calc['energy_CO2eq'].sum() * 0.0267  # 除臭系统能耗占比
            ],
            "碳流出(kgCO2eq)": [
                df_calc['pre_CO2eq'].sum(),
                df_calc['bio_CO2eq'].sum(),
                df_calc['depth_CO2eq'].sum(),
                df_calc['sludge_CO2eq'].sum(),
                df_calc['effluent_CO2eq'].sum(),
                df_calc['deodorization_CO2eq'].sum()  # 除臭系统排放
            ],
            "净排放(kgCO2eq)": [
                df_calc['pre_CO2eq'].sum() - df_calc['energy_CO2eq'].sum() * 0.3193,
                df_calc['bio_CO2eq'].sum() - df_calc['energy_CO2eq'].sum() * 0.4453,
                df_calc['depth_CO2eq'].sum() - (
                        df_calc['energy_CO2eq'].sum() * 0.1155 + df_calc['chemicals_CO2eq'].sum()),
                df_calc['sludge_CO2eq'].sum() - df_calc['energy_CO2eq'].sum() * 0.0507,
                df_calc['effluent_CO2eq'].sum() - df_calc['energy_CO2eq'].sum() * 0.0672,
                df_calc['deodorization_CO2eq'].sum() - df_calc['energy_CO2eq'].sum() * 0.0267  # 除臭系统净排放
            ]
        })


        # 添加样式
        def color_negative_red(val):
            color = 'red' if val < 0 else 'green'
            return f'color: {color}'


        styled_account = account_df.style.applymap(color_negative_red, subset=['净排放(kgCO2eq)'])
        st.dataframe(styled_account, use_container_width=True, height=300)
        # 自定义公式计算器
        st.subheader("自定义公式计算器")
        st.markdown("""
        **使用说明**:
        1. 在下方输入公式名称和表达式
        2. 公式中可以使用以下变量（单位）:
           - 处理水量(m³): `water_flow`
           - 能耗(kWh): `energy`
           - 药耗(kg): `chemicals`
           - PAC投加量(kg): `pac`
           - PAM投加量(kg): `pam`
           - 次氯酸钠投加量(kg): `naclo`
           - 进水TN(mg/L): `tn_in`
           - 出水TN(mg/L): `tn_out`
           - 进水COD(mg/L): `cod_in`
           - 出水COD(mg/L): `cod_out`
        3. 支持数学运算和函数: `+`, `-`, `*`, `/`, `**`, `sqrt()`, `log()`, `exp()`, `sin()`, `cos()`等
        """)
        col1, col2 = st.columns([1, 1])
        with col1:
            formula_name = st.text_input("公式名称", "单位水处理碳排放")
            formula_expression = st.text_area("公式表达式", "energy * 0.9419 / water_flow")
            if st.button("保存公式"):
                if formula_name and formula_expression:
                    st.session_state.custom_calculations[formula_name] = formula_expression
                    st.success(f"公式 '{formula_name}' 已保存！")
                else:
                    st.warning("请填写公式名称和表达式")
        with col2:
            if st.session_state.custom_calculations:
                selected_formula = st.selectbox("选择公式", list(st.session_state.custom_calculations.keys()))
                st.code(f"{selected_formula}: {st.session_state.custom_calculations[selected_formula]}")
        # 公式计算区域
        if st.session_state.custom_calculations:
            st.subheader("公式计算")
            # 创建变量输入表
            variables = {
                "water_flow": "处理水量(m³)",
                "energy": "能耗(kWh)",
                "chemicals": "药耗总量(kg)",
                "pac": "PAC投加量(kg)",
                "pam": "PAM投加量(kg)",
                "naclo": "次氯酸钠投加量(kg)",
                "tn_in": "进水TN(mg/L)",
                "tn_out": "出水TN(mg/L)",
                "cod_in": "进水COD(mg/L)",
                "cod_out": "出水COD(mg/L)"
            }
            col1, col2, col3 = st.columns(3)
            var_values = {}
            # 动态生成变量输入
            for i, (var, label) in enumerate(variables.items()):
                if i % 3 == 0:
                    with col1:
                        var_values[var] = st.number_input(label, value=0.0, key=f"var_{var}")
                elif i % 3 == 1:
                    with col2:
                        var_values[var] = st.number_input(label, value=0.0, key=f"var_{var}")
                else:
                    with col3:
                        var_values[var] = st.number_input(label, value=0.0, key=f"var_{var}")
            # 计算按钮
            if st.button("计算公式"):
                try:
                    # 安全计算环境
                    safe_env = {
                        "__builtins__": None,
                        "math": math,
                        "sqrt": math.sqrt,
                        "log": math.log,
                        "exp": math.exp,
                        "sin": math.sin,
                        "cos": math.cos,
                        "tan": math.tan,
                        "pi": math.pi,
                        "e": math.e
                    }
                    # 添加变量值
                    safe_env.update(var_values)
                    # 获取当前公式
                    formula = st.session_state.custom_calculations[selected_formula]
                    # 计算结果
                    result = eval(formula, {"__builtins__": None}, safe_env)
                    # 保存结果
                    st.session_state.formula_results[selected_formula] = {
                        "result": result,
                        "variables": var_values.copy()
                    }
                    st.success(f"计算结果: {result:.4f}")
                except Exception as e:
                    st.error(f"计算错误: {str(e)}")
            # 显示历史计算结果
            if st.session_state.formula_results:
                st.subheader("历史计算结果")
                for formula_name, result_data in st.session_state.formula_results.items():
                    st.markdown(f"**{formula_name}**: {result_data['result']:.4f}")
                    st.json(result_data["variables"])

with tab4:
    st.header("优化与决策支持")
    if 'df_calc' in st.session_state and st.session_state.df_calc is not None:
        df_calc = st.session_state.df_calc
        df = st.session_state.df
        df_selected = st.session_state.df_selected
        # 异常识别与优化建议
        st.subheader("异常识别与优化建议")
        if len(df) >= 3 and 'total_CO2eq' in df_calc.columns and '处理水量(m³)' in df.columns:
            # 计算历史平均值（使用处理水量加权）
            total_water = df['处理水量(m³)'].sum()
            if total_water > 0:
                historical_mean = df_calc['total_CO2eq'].sum() / total_water
            else:
                historical_mean = 0
            current_water = df_selected['处理水量(m³)'].sum()
            if current_water > 0:
                current_total = df_calc['total_CO2eq'].sum() / current_water
            else:
                current_total = 0
            if historical_mean > 0 and current_total > 1.5 * historical_mean:
                st.warning(f"⚠️ 异常预警：当月单位水量碳排放（{current_total:.4f} kgCO2eq/m³）超历史均值50%！")
                # 识别主要问题区域（包含除臭系统）
                unit_emissions = {
                    "预处理区": df_calc['pre_CO2eq'].sum() / current_water,
                    "生物处理区": df_calc['bio_CO2eq'].sum() / current_water,
                    "深度处理区": df_calc['depth_CO2eq'].sum() / current_water,
                    "泥处理区": df_calc['sludge_CO2eq'].sum() / current_water,
                    "出水区": df_calc['effluent_CO2eq'].sum() / current_water,
                    "除臭系统": df_calc['deodorization_CO2eq'].sum() / current_water
                }
                max_unit = max(unit_emissions, key=unit_emissions.get)
                st.error(f"主要问题区域: {max_unit} (排放强度: {unit_emissions[max_unit]:.4f} kgCO2eq/m³)")
                # 针对性建议
                if max_unit == "生物处理区":
                    st.info("优化建议：")
                    st.write("- 检查曝气系统效率，优化曝气量")
                    st.write("- 调整污泥回流比，优化生物处理效率")
                    st.write("- 监控进水水质波动，避免冲击负荷")
                elif max_unit == "深度处理区":
                    st.info("优化建议：")
                    st.write("- 优化化学药剂投加量，避免过量投加")
                    st.write("- 检查混合反应效果，提高药剂利用率")
                    st.write("- 考虑使用更环保的替代药剂")
                elif max_unit == "预处理区":
                    st.info("优化建议：")
                    st.write("- 优化格栅运行频率，降低能耗")
                    st.write("- 检查水泵效率，考虑变频控制")
                    st.write("- 加强进水监控，避免大颗粒物进入")
                elif max_unit == "出水区" or max_unit == "除臭系统":  # 除臭系统与出水区建议类似
                    st.info("优化建议：")
                    st.write("- 优化消毒剂投加量，减少化学药剂使用")
                    st.write("- 检查消毒接触时间，提高消毒效率")
                    st.write("- 考虑紫外线消毒等低碳替代方案")
                else:
                    st.info("优化建议：")
                    st.write("- 优化污泥脱水工艺参数")
                    st.write("- 检查脱水设备运行效率")
                    st.write("- 考虑污泥资源化利用途径")
            else:
                st.success("✅ 当月碳排放水平正常")
        else:
            st.info("数据量不足，无法进行异常识别")
        # 优化效果模拟
        st.subheader("工艺优化效果模拟")
        if not df_selected.empty:
            optimized_bio = df_calc['bio_CO2eq'].sum() * (1 - aeration_adjust / 100)
            optimized_depth = df_calc['depth_CO2eq'].sum() * (1 - pac_adjust / 100)
            optimized_total = (df_calc['total_CO2eq'].sum()
                               - (df_calc['bio_CO2eq'].sum() - optimized_bio)
                               - (df_calc['depth_CO2eq'].sum() - optimized_depth))
            # 创建优化效果图表 - 所有文字改为黑色
            opt_fig = go.Figure()
            opt_fig.add_trace(go.Bar(
                x=["优化前", "优化后"],
                y=[df_calc['total_CO2eq'].sum(), optimized_total],
                marker_color=["#EF553B", "#00CC96"],
                text=[f"{emission:.1f}" for emission in [df_calc['total_CO2eq'].sum(), optimized_total]],
                textposition='auto',
                textfont=dict(color='black')  # 确保文字为黑色
            ))
            opt_fig.update_layout(
                title=f"优化效果：月度减排{(df_calc['total_CO2eq'].sum() - optimized_total):.1f} kgCO2eq",
                title_font=dict(color="black"),  # 标题文字颜色改为黑色
                yaxis_title="总碳排放（kgCO2eq/月）",
                yaxis_title_font=dict(color="black"),  # Y轴标题文字颜色改为黑色
                font=dict(size=14, color="black"),  # 整体文字颜色改为黑色
                plot_bgcolor="rgba(245, 245, 245, 1)",
                paper_bgcolor="rgba(245, 245, 245, 1)",
                height=400,
                # 确保坐标轴标签颜色为黑色
                xaxis=dict(
                    tickfont=dict(color="black"),
                    title_font=dict(color="black")
                ),
                yaxis=dict(
                    tickfont=dict(color="black"),
                    title_font=dict(color="black")
                )
            )
            # 添加减排量标注 - 文字颜色改为黑色
            opt_fig.add_annotation(
                x=1, y=optimized_total,
                text=f"减排: {df_calc['total_CO2eq'].sum() - optimized_total:.1f} kg",
                showarrow=True,
                arrowhead=1,
                ax=0,
                ay=-40,
                font=dict(color="black")  # 标注文字颜色改为黑色
            )
            st.plotly_chart(opt_fig, use_container_width=True)
            # 显示优化细节
            st.subheader("优化措施详情")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("曝气时间调整", f"{aeration_adjust}%",
                          delta=f"生物处理区减排: {df_calc['bio_CO2eq'].sum() - optimized_bio:.1f} kgCO2eq",
                          delta_color="inverse")
            with col2:
                st.metric("PAC投加量调整", f"{pac_adjust}%",
                          delta=f"深度处理区减排: {df_calc['depth_CO2eq'].sum() - optimized_depth:.1f} kgCO2eq",
                          delta_color="inverse")
        else:
            st.warning("没有选中数据，无法进行优化模拟")
    else:

        st.warning("请先上传运行数据")
