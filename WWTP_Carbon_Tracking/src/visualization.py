import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

"""工艺单元碳排热力图 - 修正为真正的热力图"""


def create_heatmap_overlay(emission_data: dict) -> go.Figure:
    """工艺单元碳排热力图 - 修正为真正的热力图"""
    # 根据排放数据创建热力图数据
    units = list(emission_data.keys())
    emissions = [emission_data[unit] for unit in units]
    # 创建矩阵形式的热力图数据
    max_emission = max(emissions) if emissions else 1
    min_emission = min(emissions) if emissions else 0
    # 创建颜色映射
    colors = px.colors.sample_colorscale("RdBu_r",
                                         [(e - min_emission) / (max_emission - min_emission) for e in emissions]
                                         if max_emission > min_emission else [0.5] * len(emissions))
    # 创建热力图
    fig = go.Figure(data=go.Heatmap(
        z=[emissions],
        x=units,
        y=['碳排放'],
        colorscale='RdBu_r',
        text=[[f"{unit}<br>{e:.1f} kgCO2eq" for e, unit in zip(emissions, units)]],
        hoverinfo="text",
        showscale=True,
        colorbar=dict(
            title=dict(text='碳排放 (kgCO2eq)', side='right', font=dict(color='black')),
            thickness=15
        )
    ))
    # 添加标注
    annotations = []
    for i, emission in enumerate(emissions):
        annotations.append(dict(
            x=i,
            y=0,
            text=f"{emission:.1f}",
            showarrow=False,
            font=dict(color='black', size=12),
            xref='x',
            yref='y'
        ))

    fig.update_layout(
        title="工艺单元碳排放热力图",
        title_font=dict(size=24, family="Arial", color="black"),
        xaxis_title="工艺单元",
        yaxis_title="",
        font=dict(size=14, color="black"),
        plot_bgcolor="rgba(245, 245, 245, 1)",
        paper_bgcolor="rgba(245, 245, 245, 1)",
        height=400,
        annotations=annotations
    )
    # 确保坐标轴标签颜色为黑色
    fig.update_xaxes(
        tickfont=dict(color='black'),
        title_font=dict(color='black')
    )
    fig.update_yaxes(
        tickfont=dict(color='black'),
        title_font=dict(color='black')
    )
    return fig


"""碳流动态追踪图谱"""


def create_sankey_diagram(df: pd.DataFrame) -> go.Figure:
    """碳流动态追踪图谱"""
    # 检查数据是否为空
    if df.empty:
        return go.Figure()
    labels = [
        "电耗", "PAC", "PAM", "次氯酸钠",
        "预处理区", "生物处理区", "深度处理区", "泥处理区", "出水区", "除臭系统",
        "N2O排放", "CH4排放", "能耗间接排放", "药耗间接排放"
    ]
    energy = df['energy_CO2eq'].sum()
    pac = df['PAC_CO2eq'].sum() if 'PAC_CO2eq' in df else 0
    pam = df['PAM_CO2eq'].sum() if 'PAM_CO2eq' in df else 0
    naclo = df['NaClO_CO2eq'].sum() if 'NaClO_CO2eq' in df else 0
    source = [0, 0, 0, 0, 0, 0, 1, 2, 3]  # 增加除臭系统源
    target = [4, 5, 6, 7, 8, 9, 6, 6, 6]  # 增加除臭系统目标
    value = [
        energy * 0.3193,
        energy * 0.4453,
        energy * 0.1155,
        energy * 0.0507,
        energy * 0.0672,
        energy * 0.0267,  # 除臭系统能耗
        pac,
        pam,
        naclo
    ]
    # 添加直接排放
    n2o_emission = df['N2O_CO2eq'].sum()
    ch4_emission = df['CH4_CO2eq'].sum()
    if n2o_emission > 0:
        source.append(5)  # 生物处理区
        target.append(10)  # N2O排放
        value.append(n2o_emission)
    if ch4_emission > 0:
        source.append(5)  # 生物处理区
        target.append(11)  # CH4排放
        value.append(ch4_emission)
    # 过滤零值
    valid_indices = [i for i, v in enumerate(value) if v > 0]
    source = [source[i] for i in valid_indices]
    target = [target[i] for i in valid_indices]
    value = [value[i] for i in valid_indices]

    # 定义节点颜色
    node_colors = [
        "#FFD700", "#FFA500", "#FF6347", "#FF4500",  # 输入源（金色、橙色）
        "#1E90FF", "#4169E1", "#4682B4", "#5F9EA0", "#1abc9c", "#1abc9c",  # 处理区（蓝色系，除臭系统用出水区颜色）
        "#32CD32", "#228B22", "#2E8B57", "#3CB371"  # 排放（绿色系）
    ]
    # 修正：移除node配置中的font属性，使用hoverlabel设置文字样式
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=20,
            thickness=30,
            line=dict(color="black", width=1.5),
            label=labels,
            color=node_colors[:len(labels)],
            hovertemplate='%{label}<br>%{value} kgCO2eq',
            hoverlabel=dict(
                font=dict(color='black', size=12)
            )
        ),
        link=dict(
            source=source,
            target=target,
            value=value,
            color="rgba(150, 150, 150, 0.5)",
            hovertemplate='源: %{source.label}<br>目标: %{target.label}<br>流量: %{value} kgCO2eq'
        )
    )])
    fig.update_layout(
        title="碳流动态追踪图谱",
        title_font=dict(size=24, family="Arial", color="black"),
        height=500,
        font=dict(size=14, color="black"),
        plot_bgcolor="rgba(245, 245, 245, 1)",
        paper_bgcolor="rgba(245, 245, 245, 1)"
    )
    return fig


"""碳排放效率排行榜 - 修正文字颜色"""


def create_efficiency_ranking(df: pd.DataFrame) -> go.Figure:
    """碳排放效率排行榜 - 修正文字颜色"""
    # 检查数据是否为空
    if df.empty:
        return go.Figure()
    efficiency_data = {}
    units = ["预处理区", "生物处理区", "深度处理区", "泥处理区", "出水区", "除臭系统"]  # 包含除臭系统
    unit_cols = ['pre_CO2eq', 'bio_CO2eq', 'depth_CO2eq', 'sludge_CO2eq', 'effluent_CO2eq', 'deodorization_CO2eq']
    total_water = df['处理水量(m³)'].sum()
    if total_water > 0:
        for unit, col in zip(units, unit_cols):
            total_emission = df[col].sum()
            if total_emission > 0:
                efficiency_data[unit] = total_water / total_emission
            else:
                efficiency_data[unit] = 0
    else:
        for unit in units:
            efficiency_data[unit] = 0

    df_eff = pd.DataFrame(
        efficiency_data.items(),
        columns=["工艺单元", "效率（m³/kgCO2eq）"]
    ).sort_values("效率（m³/kgCO2eq）", ascending=False)
    fig = px.bar(
        df_eff,
        x="工艺单元",
        y="效率（m³/kgCO2eq）",
        title="碳排放效率排行榜",
        color="效率（m³/kgCO2eq）",
        color_continuous_scale="Tealgrn",
        text="效率（m³/kgCO2eq）",
        height=500
    )
    # 美化图表 - 修正文字颜色
    fig.update_traces(
        texttemplate='%{text:.2f}',
        textposition='outside',
        marker_line_color='rgb(8,48,107)',
        marker_line_width=1.5,
        textfont=dict(color="black", size=12)
    )

    fig.update_layout(
        title_font=dict(size=24, family="Arial", color="black"),
        xaxis_title="工艺单元",
        yaxis_title="碳排放效率 (m³/kgCO2eq)",
        font=dict(size=14, color="black"),
        plot_bgcolor="rgba(245, 245, 245, 1)",
        paper_bgcolor="rgba(245, 245, 245, 1)",
        showlegend=False,
        # 确保坐标轴标签颜色可见
        xaxis=dict(
            tickfont=dict(color="black"),
            title_font=dict(color="black")
        ),
        yaxis=dict(
            tickfont=dict(color="black"),
            title_font=dict(color="black")
        )
    )
    # 设置颜色条的标题字体颜色
    fig.update_coloraxes(
        colorbar_title_text="效率（m³/kgCO2eq）",
        colorbar_title_font_color="black",
        colorbar_tickfont=dict(color="black")
    )
    if not df_eff.empty:
        avg_efficiency = df_eff["效率（m³/kgCO2eq）"].mean()
        fig.add_hline(
            y=avg_efficiency,
            line_dash="dash",
            line_color="red",
            line_width=2,
            annotation_text=f"平均效率: {avg_efficiency:.2f}",
            annotation_position="bottom right",
            annotation_font_size=14,
            annotation_font_color="black"
        )
    return fig


"""工艺优化效果模拟图 - 修正所有文字颜色为黑色"""


def create_optimization_effect_diagram(before_data, after_data) -> go.Figure:
    """工艺优化效果模拟图 - 修正所有文字颜色为黑色"""
    # 计算减排量
    reduction = before_data['total_CO2eq'].sum() - after_data['total_CO2eq'].sum()
    reduction_rate = (reduction / before_data['total_CO2eq'].sum()) * 100 if before_data['total_CO2eq'].sum() > 0 else 0

    # 创建数据
    labels = ['优化前', '优化后']
    total_emissions = [
        before_data['total_CO2eq'].sum(),
        after_data['total_CO2eq'].sum()
    ]

    # 创建图表
    fig = go.Figure(data=[
        go.Bar(
            x=labels,
            y=total_emissions,
            text=[f"{emission:.1f}" for emission in total_emissions],
            textposition='auto',
            marker_color=['#FF6347', '#32CD32'],
            textfont=dict(color="black", size=14)  # 条形图上的数值标注为黑色
        )
    ])

    # 添加优化效果标注（确保文字及单位为黑色）
    fig.add_annotation(
        x=0.5,
        y=max(total_emissions) * 1.1,
        text=f"优化效果：月度减排 {reduction:.1f} kgCO2eq ({reduction_rate:.1f}%)",
        showarrow=False,
        font=dict(size=16, color="black", weight="bold")  # 优化效果文字为黑色
    )

    # 更新布局（确保所有文字为黑色）
    fig.update_layout(
        title="工艺优化效果模拟",
        title_font=dict(size=24, family="Arial", color="black"),  # 标题为黑色
        yaxis_title="总碳排放 (kgCO2eq)",  # Y轴标题及单位为黑色
        font=dict(size=14, color="black"),
        plot_bgcolor="rgba(245, 245, 245, 1)",
        paper_bgcolor="rgba(245, 245, 245, 1)",
        height=500,
        xaxis=dict(
            tickfont=dict(color="black", size=14),  # "优化前"、"优化后"为黑色
            title_font=dict(color="black")
        ),
        yaxis=dict(
            tickfont=dict(color="black", size=12),  # Y轴刻度数字为黑色
            title_font=dict(color="black"),
            showgrid=True,
            gridcolor="rgba(200, 200, 200, 0.3)"
        )
    )

    return fig