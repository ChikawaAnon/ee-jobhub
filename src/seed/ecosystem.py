# -*- coding: utf-8 -*-
"""产业链关联企业种子数据（10 家）。

收录逻辑：已收录 190+ 家企业的上下游 / 合作方 / 甲乙方中，同样大量招聘
电气专业的企业。每家的 ee_notes 里写明与库内企业的产业链关系。
薪资均为公开渠道聚合口径，仅供参考。
"""
from .helpers import S

COMPANIES = [
    # ---------- 电池链上游（宁德/比亚迪/亿纬的供应商） ----------
    S("kedali", "科达利", "general", "高端制造", "民企", "电池精密结构件",
      apply_url="https://www.kedali.com.cn?以官网为准", official_site="https://www.kedali.com.cn",
      batch=["秋招"], status="未开启", positions=["电气工程师", "设备工程师", "自动化", "模具"],
      cities=["深圳", "惠州", "宁德", "德国/瑞典"], deadline_note="预计2026年9月",
      salary_text="本科转月约 9-12k×13",
      salary_structure="基本工资+绩效+年终，五险一金，上市公司",
      desc="电池精密结构件全球龙头（深圳），宁德/比亚迪/中创新航的核心供应商",
      ee_notes="电池链上游甲方：客户就是库里的宁德/亿纬/中创新航；产线自动化设备电气对口，跟着电池厂扩产走",
      tags=["S级对口", "广东有岗", "本科友好"]),
    S("tinci", "天赐材料", "general", "石化钢铁", "民企", "电解液/锂电材料",
      apply_url="https://tinci.com", official_site="https://tinci.com",
      batch=["秋招"], status="未开启", positions=["电气工程师", "仪表工程师", "设备管理"],
      cities=["广州", "江门", "全国基地"], deadline_note="预计2026年9月",
      salary_text="本科转月约 9-12k×13",
      salary_structure="基本工资+绩效+年终，五险一金，上市公司",
      desc="电解液全球龙头（广州总部），宁德/亿纬等电池厂的上游甲方",
      ee_notes="化工装置的电气/仪表岗位规范；广州总部+江门基地，电池链上游视角",
      tags=["高度相关", "广东有岗"]),

    # ---------- 机器人/具身智能产业链（关节/传感/视觉供应商） ----------
    S("orbbec", "奥比中光", "general", "机器人/具身智能", "民企", "3D视觉传感器",
      alias="Orbbec", apply_url="https://www.orbbec.com?以官网为准", official_site="https://www.orbbec.com",
      batch=["秋招", "实习"], status="未开启", positions=["电气工程师", "硬件研发", "测试", "光学"],
      cities=["深圳"], deadline_note="预计2026年9月（机器人视觉传感器「眼睛」龙头）",
      salary_text="本科转月约 12-16k×(13-15)",
      salary_structure="基本工资+绩效+年终，五险一金，科创板上市",
      desc="3D 视觉传感器龙头（深圳），优必选/众擎等机器人公司的「眼睛」供应商",
      ee_notes="具身智能链核心传感器：硬件测试/电气对口；服务库内机器人企业的共性供应商",
      tags=["S级对口", "广东有岗"]),
    S("pasini", "帕西尼感知", "general", "机器人/具身智能", "民企", "触觉传感器",
      alias="PaXini", apply_url="https://www.pasini.ai?以官网为准", official_site="https://www.pasini.ai",
      batch=["秋招", "实习"], status="未开启", positions=["电气工程师", "硬件研发", "传感器", "测试"],
      cities=["深圳"], deadline_note="具身智能触觉传感器头部创企，融资充裕",
      salary_text="本科约 12-16k×(13-15)，初创期权",
      salary_structure="基本工资+绩效+期权，五险一金",
      desc="机器人触觉传感器创企（深圳），人形机器人「皮肤」赛道头部",
      ee_notes="具身智能触觉链：传感器硬件/电气测试对口；初创小团队成长快",
      tags=["S级对口", "广东有岗"]),
    S("leaderdrive", "绿的谐波", "general", "机器人/具身智能", "民企", "谐波减速器",
      alias="Leaderdrive", apply_url="https://www.leaderdrive.cn?以官网为准", official_site="https://www.leaderdrive.cn",
      batch=["秋招"], status="未开启", positions=["电气工程师", "设备工程师", "测试"],
      cities=["苏州"], deadline_note="预计2026年9月（人形机器人关节减速器核心）",
      salary_text="本科转月约 10-14k×(13-14)",
      salary_structure="基本工资+绩效+年终，五险一金，科创板上市",
      desc="谐波减速器国产龙头（苏州），优必选/埃斯顿等机器人关节核心部件供应商",
      ee_notes="机器人关节链上游：减速器产线电气/测试设备电气对口；客户含库内机器人企业",
      tags=["S级对口", "高度相关"]),

    # ---------- 功率链（逆变器/电控的功率器件上游） ----------
    S("starpower", "斯达半导", "equipment", "电源设备", "民企", "IGBT功率模块",
      alias="StarPower", apply_url="https://www.powersemi.com", official_site="https://www.powersemi.com",
      batch=["秋招"], status="未开启", positions=["电气工程师", "测试工程师", "应用工程师", "设备"],
      cities=["嘉兴"], deadline_note="预计2026年9月（车规/光伏 IGBT 模块国产龙头）",
      salary_text="本科转月约 11-15k×(13-15)",
      salary_structure="基本工资+绩效+年终，五险一金，主板上市",
      desc="IGBT 功率模块国产龙头（嘉兴），阳光电源/汇川等库内企业的功率器件上游",
      ee_notes="电力电子的「心脏」赛道：功率模块测试/应用工程师对口电气；器件视角补全电力电子链",
      tags=["S级对口", "高度相关"]),

    # ---------- 家电/工具链上游（智能控制器 + 电机） ----------
    S("topband", "拓邦股份", "general", "高端制造", "民企", "智能控制器/电机",
      alias="Topband", apply_url="https://www.topband.com?以官网为准", official_site="https://www.topband.com",
      batch=["秋招"], status="未开启", positions=["电气工程师", "硬件研发", "电机研发", "测试"],
      cities=["深圳", "惠州", "越南"], deadline_note="预计2026年9月",
      salary_text="本科转月约 10-13k×13",
      salary_structure="基本工资+绩效+年终，五险一金，上市公司",
      desc="智能控制器+直流电机头部（深圳），美的/格力/工具大厂的上游供应商",
      ee_notes="家电/工具链上游：控制器硬件+电机研发电气对口；客户即库内家电企业",
      tags=["S级对口", "广东有岗"]),

    # ---------- 检测服务链（全行业甲乙方） ----------
    S("grgtest", "广电计量", "general", "高端制造", "国企", "第三方检测认证",
      apply_url="https://www.grgtest.com?以官网为准", official_site="https://www.grgtest.com",
      batch=["秋招", "春招"], status="未开启", positions=["电气测试工程师", "检测工程师", "设备管理"],
      cities=["广州", "全国实验室"], deadline_note="预计2026年9月（广州国资背景上市检测机构）",
      salary_text="本科转月约 8-11k×13",
      salary_structure="基本工资+绩效+年终，五险一金，国资背景上市公司",
      desc="第三方检测认证机构（广州国资），服务全部制造业企业（含库内各家）的电气安全/电磁兼容检测",
      ee_notes="制造业的「裁判员」：电气安全/EMC 检测岗位稳定不加班抖动少；广州国企背景",
      tags=["高度相关", "广东有岗", "央国企", "本科友好"]),

    # ---------- 成都电子测量（成都电子圈补充） ----------
    S("siglent", "鼎阳科技", "general", "ICT硬件", "民企", "电子测试测量仪器",
      alias="SIGLENT", apply_url="https://www.siglent.com?以官网为准", official_site="https://www.siglent.com",
      batch=["秋招"], status="未开启", positions=["硬件研发", "电气工程师", "测试"],
      cities=["成都", "深圳"], deadline_note="预计2026年9月（国产示波器头部）",
      salary_text="本科转月约 10-14k×13",
      salary_structure="基本工资+绩效+年终，五险一金，科创板上市",
      desc="示波器/频谱仪国产头部（成都），电子工程师的「工具箱」供应商",
      ee_notes="成都电子圈代表企业；硬件/测试岗电气电子复合对口；国产仪器替代趋势受益",
      tags=["高度相关", "本科友好"]),
]
