import pandas as pd
import numpy as np

class CarbonCalculator:
    def __init__(self):
        # 排放因子（严格遵循《可行性方案》2.1节公式参数）
        self.EF_N2O = 0.016  # kgN2O-N/kgTN（方案公式1）
        self.C_N2O_N2 = 44 / 28  # N2O与N2分子量比
        self.f_N2O = 265  # N2O温室效应指数（方案公式2）
        self.B0 = 0.25  # CH4产率系数（kgCH4/kgCOD，方案公式3）
        self.MCF = 0.003  # 正常工况CH4修正因子（方案公式3）
        self.f_CH4 = 28  # CH4温室效应指数（方案公式4）
        self.f_e = 0.9419  # 电耗碳排放因子（kgCO2/(kW·h)，方案公式5）
        self.EF_chemicals = {  # 药剂排放因子（方案公式7）
            "PAC": 1.62,
            "PAM": 1.5,
            "次氯酸钠": 0.92
        }

        # 各工艺单元能耗分配比例（根据方案表2）
        self.energy_distribution = {
            "预处理区": 0.3193,
            "生物处理区": 0.4453,
            "深度处理区": 0.1155,
            "泥处理区": 0.0507,
            "出水区": 0.0672,
            "除臭系统": 0.0267  # 新增除臭系统能耗占比
        }

    def calculate_direct_emissions(self, df):
        """计算N₂O、CH₄直接排放（基于《可行性方案》公式1-4）"""
        required_cols = ['处理水量(m³)', '进水TN(mg/L)', '出水TN(mg/L)', '进水COD(mg/L)', '出水COD(mg/L)']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"数据缺少必需列：{missing_cols}，请检查数据或列名映射！")

        if not isinstance(df, pd.DataFrame):
            raise TypeError("输入数据必须为pandas DataFrame格式")

        # 确保数值列正确转换
        for col in required_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # 处理缺失值
        df = df.fillna(0)

        # N₂O直接排放（生物处理区）
        df['N2O_emission'] = (
                df['处理水量(m³)'] * (df['进水TN(mg/L)'] - df['出水TN(mg/L)'])
                * self.EF_N2O * self.C_N2O_N2 / 1000  # 单位转换（mg→kg）
        )
        df['N2O_CO2eq'] = df['N2O_emission'] * self.f_N2O

        # CH4直接排放（预处理/污泥区）
        df['COD_removed'] = (
                df['处理水量(m³)'] * np.abs(df['进水COD(mg/L)'] - df['出水COD(mg/L)'])
                / 1000
        )
        df['CH4_emission'] = df['COD_removed'] * self.B0 * self.MCF
        df['CH4_CO2eq'] = df['CH4_emission'] * self.f_CH4

        return df

    def calculate_indirect_emissions(self, df):
        """计算能耗、药耗间接排放"""
        required_cols = ['电耗(kWh)', 'PAC投加量(kg)', 'PAM投加量(kg)', '次氯酸钠投加量(kg)']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"数据缺少必需列：{missing_cols}，请检查数据或列名映射！")

        # 处理缺失值
        df = df.fillna(0)

        # 能耗间接排放
        df['energy_CO2eq'] = df['电耗(kWh)'] * self.f_e

        # 药耗间接排放
        df['PAC_CO2eq'] = df['PAC投加量(kg)'] * self.EF_chemicals['PAC']
        df['PAM_CO2eq'] = df['PAM投加量(kg)'] * self.EF_chemicals['PAM']
        df['NaClO_CO2eq'] = df['次氯酸钠投加量(kg)'] * self.EF_chemicals['次氯酸钠']
        df['chemicals_CO2eq'] = df['PAC_CO2eq'] + df['PAM_CO2eq'] + df['NaClO_CO2eq']

        return df

    def calculate_unit_emissions(self, df):
        """按工艺单元拆分排放量（包含除臭系统）"""
        # 检查输入数据合法性
        required_cols = ['energy_CO2eq', 'N2O_CO2eq', 'CH4_CO2eq', 'chemicals_CO2eq', '处理水量(m³)']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"数据缺少必需列：{missing_cols}，请先执行直接/间接排放计算！")

        if not isinstance(df, pd.DataFrame):
            raise TypeError("输入数据必须为pandas DataFrame格式")

        # 处理缺失值
        df = df.fillna(0)

        # 按工艺单元分配碳排放
        df['pre_CO2eq'] = df['energy_CO2eq'] * self.energy_distribution["预处理区"]
        df['bio_CO2eq'] = df['N2O_CO2eq'] + df['CH4_CO2eq'] + df['energy_CO2eq'] * self.energy_distribution["生物处理区"]
        df['depth_CO2eq'] = df['chemicals_CO2eq'] + df['energy_CO2eq'] * self.energy_distribution["深度处理区"]
        df['sludge_CO2eq'] = df['energy_CO2eq'] * self.energy_distribution["泥处理区"]
        df['effluent_CO2eq'] = df['energy_CO2eq'] * self.energy_distribution["出水区"]
        # 新增除臭系统碳排放
        df['deodorization_CO2eq'] = df['energy_CO2eq'] * self.energy_distribution["除臭系统"]

        # 总排放与效率
        df['total_CO2eq'] = (df['pre_CO2eq'] + df['bio_CO2eq'] +
                             df['depth_CO2eq'] + df['sludge_CO2eq'] +
                             df['effluent_CO2eq'] + df['deodorization_CO2eq'])
        df['carbon_efficiency'] = df['处理水量(m³)'] / df['total_CO2eq'].replace(0, 1)  # 避免除零错误

        return df