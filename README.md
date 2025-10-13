# PyInspur - 浪潮考勤自动化脚本

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)

一个用于浪潮考勤的自动化签到/签退脚本。

## 目录

- [快速开始](#快速开始)
  - [安装步骤](#安装步骤)
- [使用说明](#使用说明)
  - [主要功能](#主要功能)
  - [操作菜单](#操作菜单)
  - [获取坐标](#获取坐标)

## 快速开始

### 安装步骤

1. **克隆项目**
```bash
git clone https://github.com/skyunix/pyinspur.git
cd pyinspur
```

2. **创建虚拟环境**
```bash
# 使用 Python 内置的 venv 模块创建虚拟环境
python -m venv .venv

# 激活虚拟环境
# Windows:
.venv\Scripts\activate

# macOS/Linux:
source .venv/bin/activate
```

3. **安装依赖**
```bash
# 安装生产依赖（必需）
pip install -r requirements.txt
```

4. **开始使用**

```bash
python main.py
```

### 获取公司坐标

推荐使用以下工具获取坐标：
- [高德地图坐标拾取器](https://lbs.amap.com/tools/picker)
- [百度地图坐标拾取器](https://api.map.baidu.com/lbsapi/getpoint/)

## 项目结构

```
pyinspur/
├── main.py                 # 主程序入口
├── conf/                   # 配置文件目录
│   └── config.example.yml  # 配置模板
├── inspur/                 # 核心功能模块
│   ├── __init__.py
│   ├── config_manager.py   # 配置管理
│   ├── inspur_client.py    # 考勤客户端
│   ├── login_manager.py    # 登录流程
│   └── user_manager.py     # 用户管理
├── utils/                  # 工具模块
│   ├── __init__.py
│   ├── common_utils.py     # 通用工具
│   ├── constants.py        # 常量定义
│   └── logger.py           # 日志工具
├── requirements.txt        # 项目依赖
└── README.md               # 说明文档
```

---

**注意**：本工具仅供学习和个人使用，请遵守相关法律法规和公司规定。