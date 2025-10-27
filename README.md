# PyInspur - 浪潮考勤自动化脚本

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)

一个用于浪潮考勤的自动化签到/签退脚本。

## 快速开始

### 安装 uv

```bash
# 使用 pip 安装
pip install uv

# 或者参考官方文档的其他安装方式
# https://docs.astral.sh/uv/
```

### 安装步骤

1. **克隆项目**
```bash
git clone https://github.com/skyunix/pyinspur.git
cd pyinspur
```

2. **使用 uv 创建虚拟环境并安装依赖**
```bash
# 使用 uv 创建虚拟环境并安装所有依赖
uv sync
```

3. **开始使用**

```bash
uv run main.py
```

4.  **获取公司坐标**

推荐使用以下工具获取坐标：
- [高德地图坐标拾取器](https://lbs.amap.com/tools/picker)

## 项目结构

```
pyinspur/
├── main.py                 # 主程序入口
├── pyproject.toml          # 项目配置和依赖声明
├── uv.lock                 # 依赖锁定文件
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
└── README.md               # 说明文档
```

## 常用 uv 命令

```bash
# 添加新依赖
uv add package-name

# 删除依赖
uv remove package-name

# 更新所有依赖
uv lock --upgrade

# 更新特定依赖
uv lock --upgrade-package package-name

# 查看已安装的包
uv pip list
```

---

**注意**：本工具仅供学习和个人使用，请遵守相关法律法规和公司规定.