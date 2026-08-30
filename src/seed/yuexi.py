# -*- coding: utf-8 -*-
"""粤西（湛江/茂名/阳江/肇庆）中大型雇主补充（4 家 + 存量企业城市补充）。

粤西工业以钢铁/石化/造纸/冶金/风电装备为主，电气岗位集中在厂区供配电、
设备维护、自动化产线。这些岗位多随集团统一招聘，本文件收录粤西本地
实体，投递入口走对应集团招聘平台。
"""
from .helpers import S

COMPANIES = [
    S("zhongke-refining", "中科炼化", "general", "石化钢铁", "央企", "炼油化工",
      alias="中科（广东）炼化", apply_url="https://job.sinopec.com", official_site="https://www.sinopecgroup.com",
      batch=["秋招", "春招"], status="未开启", positions=["电气工程师", "仪表", "设备", "装置运行"],
      cities=["湛江东海岛"], deadline_note="随中国石化全国统招（约9月下旬-10月报名），志愿选广东石化/中科炼化",
      salary_text="转月约 8-12k+驻地补贴，年总包 12-17w",
      salary_structure="基本工资+岗位/夜班/驻地补贴+年终，五险二金，央企福利",
      desc="中石化最大新建炼化一体化基地之一（湛江东海岛，2000万吨炼油+120万吨乙烯）",
      ee_notes="粤西电气待遇天花板级：炼化厂供配电/电气仪表需求大；走中石化统考，湛江本地就业首选",
      tags=["S级对口", "央国企", "广东有岗", "本科友好"]),
    S("guanhao", "冠豪高新", "general", "高端制造", "国企", "特种纸制造",
      alias="中国纸业冠豪", apply_url="https://campus.guanhao.com?以官网为准", official_site="https://www.guanhao.com",
      batch=["秋招"], status="未开启", positions=["电气工程师", "设备工程师", "自动化", "仪表"],
      cities=["湛江东海岛", "珠海"], deadline_note="预计2026年9-10月（央企诚通集团旗下上市公司校招）",
      salary_text="转月约 8-11k×13",
      salary_structure="基本工资+绩效+年终，五险一金，央企控股上市",
      desc="特种纸（无碳纸/热敏纸）亚洲龙头，湛江东海岛新基地",
      ee_notes="造纸产线电气/设备/自动化对口；湛江本地少有的上市央企实体，稳定",
      tags=["高度相关", "央国企", "广东有岗", "本科友好"]),
    S("guangqing", "广青科技", "general", "石化钢铁", "民企", "镍合金/不锈钢冶炼",
      alias="广东广青金属", apply_url="https://campus.gdqingke.com?以官网为准", official_site="https://www.gdqingke.com",
      batch=["秋招"], status="未开启", positions=["电气工程师", "仪表工程师", "设备管理", "自动化"],
      cities=["阳江高新区"], deadline_note="预计2026年9-10月（青山控股与广新控股合资）",
      salary_text="转月约 9-13k+倒班/驻地补贴",
      salary_structure="基本工资+绩效+倒班补贴+年终，五险一金",
      desc="阳江高新区龙头冶炼企业（镍合金/不锈钢，青山系），厂区电气需求大",
      ee_notes="粤西民企待遇第一梯队；冶炼厂供配电/仪表/传动电气岗位多，倒班有补贴；阳江本地就业优选",
      tags=["S级对口", "广东有岗", "本科友好"]),
    S("leoch", "理士国际电源", "newenergy", "电池", "民企", "铅酸/锂电池",
      alias="LEOCH", apply_url="https://campus.leoch.com?以官网为准", official_site="https://www.leoch.com",
      batch=["秋招"], status="未开启", positions=["电气工程师", "设备工程师", "自动化"],
      cities=["肇庆", "全国基地"], deadline_note="预计2026年9月",
      salary_text="本科转月约 8-11k×13",
      salary_structure="基本工资+绩效+年终，五险一金，港股上市",
      desc="铅酸/锂电池大型制造商（肇庆基地）",
      ee_notes="电池厂电气/设备岗对口；肇庆基地，粤西北就近选择",
      tags=["高度相关", "广东有岗", "本科友好"]),
]
