# EE JobHub · 电气专业秋招整合站

面向电气工程及自动化相关专业学生的校招信息整合工具。项目将公开招聘信息统一为结构化企业库，通过 FastAPI 提供查询与维护接口，前端使用原生 HTML/CSS/JavaScript，实现多维筛选、时间线、全文搜索、增量简报和新企业自动收录。

## 核心能力

- **垂直数据建模**：企业方向、城市、批次、届别、状态、对口度、薪资与来源链接统一管理。
- **爬虫与合并管线**：配置驱动的数据源适配、公司名归一化、公告匹配、自动收录和人工字段保护。
- **信息可靠性**：保留公开来源，支持链接体检、公告正文快照和人工修正。
- **自动化更新**：支持手动刷新、每日增量简报及 Windows 定时任务入口。
- **轻量全栈**：FastAPI 后端，原生前端，无前端构建步骤，支持导出单文件离线页面。

当前公开样例库包含 200+ 家企业的结构化记录；数据来自公开渠道，仅用于求职信息整理与工程学习，投递前应以企业官方公告为准。

## 架构

```text
公开招聘页面
    ↓
src/crawler/          抓取、解析、匹配、自动收录、合并
    ↓
data/companies.json   结构化企业库
    ↓
src/app.py            FastAPI 查询/维护接口
    ↓
web/                   原生前端：筛选、时间线、详情与简报
```

## 快速开始

```powershell
git clone https://github.com/ChikawaAnon/ee-jobhub.git
cd ee-jobhub
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -m uvicorn src.app:app --host 127.0.0.1 --port 8322
```

浏览器打开 <http://127.0.0.1:8322>。Windows 用户也可双击 `start.bat`。

## 目录

```text
src/               FastAPI、数据模型、存储、简报、链接检查
src/crawler/       抓取与匹配流水线
src/seed/          分方向维护的企业种子数据
web/               原生前端与 PWA 资源
data/              公开样例企业库和数据源配置
docs/outline.md    产品与数据结构设计
```

## 数据与安全边界

- 仓库不包含登录凭据、个人投递状态、服务器配置或历史快照。
- 写接口鉴权仅在本地提供 `data/auth.json` 时启用；该文件被忽略。
- 公开数据可能随时间失效，所有招聘信息以来源网站为准。

## License

MIT
