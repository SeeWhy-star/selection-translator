# Selection Translator

划词翻译工具，选中文字后按快捷键即可调用百度翻译 API 获取译文，结果以弹窗形式展示。

## 功能

- **Alt+Q** — 翻译当前选中的文本，译文弹窗显示在光标附近
- **Alt+Shift+Q** — 打开设置窗口，配置百度翻译 API 凭证和目标语言
- 支持翻译目标：简体中文 / 英文
- 系统托盘图标，右键可打开设置或退出
- 译文弹窗 12 秒后自动关闭，也可手动关闭或复制

## 安装

```bash
# 1. 克隆仓库
git clone https://github.com/SeeWhy-star/selection-translator.git
cd selection-translator

# 2. 创建虚拟环境并安装依赖
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt

# 3. 运行
.venv\Scripts\pythonw.exe main.py
```

首次运行会弹出设置窗口，需要填写百度翻译开放平台的 APP ID 和密钥（[申请地址](https://fanyi-api.baidu.com/)）。

## 打包

```bash
.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --windowed --name "SelectionTranslator" --collect-all pystray main.py
```

或直接运行 `build.bat`，打包产物在 `dist/` 目录下。

## 配置

配置文件保存在 `%APPDATA%/SelectionTranslator/config.json`，包含以下字段：

| 字段 | 说明 |
|------|------|
| `appid` | 百度翻译 APP ID（纯数字） |
| `secret_key` | 百度翻译密钥 |
| `target_lang` | 目标语言，`zh` 或 `en` |

## 依赖

- Python 3.10+
- pynput、pyperclip、pystray、Pillow、requests
