# 📱 Qis WeChat Omni Bot (齐的微信 Omni 机器人)

基于 [`omni-bot-sdk`](https://github.com/cscnk52/omni-bot-sdk) 视觉识别底层，结合 `PyAutoGUI` 与多进程/多线程调度，实现的多微信账号朋友圈自动化托管工具。

## ✨ 功能特性

- **🔄 全自动“删旧发新”**：自动导航至个人相册，删除最新一条朋友圈，并发布新的动态。
- **🖼️ 智能素材库**：自动从本地 `media/` 文件夹随机抽取一张图片或一个视频，并从 `copywriting.txt` 中随机匹配一句文案。
- **🖥️ 多账号无缝切换**：基于 Windows PID（进程 ID）精准控制微信窗口，自动将目标账号带到前台，其他账号最小化，互不干扰。
- **⏱️ 拟人化随机调度**：
  - 支持配置轮次之间的随机沉睡时间（如 30~40 分钟）。
  - 支持配置账号之间的随机冷却时间（如 15~45 秒），极大降低风控概率。
- **🌐 HTTP 接口控制**：每个微信实例独立启动 HTTP 服务，主控中心通过 HTTP 接口下发指令，解耦度高，扩展性强。

## 🏗️ 架构说明

本项目由三个核心部分组成：
1. **`bot_worker.py`**：独立的后台执行器。绑定单个微信账号的 `dbkey` 和端口，启动 `omni-bot-sdk` 并监听 HTTP 指令。
2. **`moments_plugin/`**：`omni-bot-sdk` 的自定义插件。负责执行具体的视觉寻找、点击、粘贴文案和发布逻辑。
3. **`master_controller.py`**：主控调度中心。读取全局配置文件，轮询切换各个微信窗口（通过 PID），并发送 HTTP 触发指令。

## ⚠️ 前置要求与免责声明

> 🚨 **重要提示**：任何微信自动化操作均存在被腾讯风控、限制或封号的风险。**请务必使用小号进行测试！** 本项目仅供 Python 自动化技术学习与交流，严禁用于商业营销、发广告等行为。因使用本工具导致的账号异常，作者概不负责。

在开始之前，请确保你的环境满足：
- **操作系统**：Windows 10 / 11
- **Python**：3.12.x
- **微信版本**：4.0.6.33 （`omni-bot-sdk` 目前仅支持该版本，请勿升级）
- **必备工具**：`NanoMQ`（用于提供本地 MQTT 服务）

## 🚀 快速开始

### 1. 安装依赖
克隆本项目后，创建虚拟环境并安装依赖：

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# 安装本地插件
cd moments_plugin
pip install -e .
cd ..
```

### 2. 准备底层环境
1. 参考 [`omni-bot-sdk` 文档](https://github.com/weixin-omni/omni-bot-sdk)，使用工具获取你各个微信账号的 `dbkey`。
2. 启动本地 MQTT 服务（NanoMQ），默认监听 `1883` 端口：
   ```bash
   nanomq start
   ```

### 3. 配置文件与素材
1. 复制配置模板并修改：
   ```bash
   cp accounts.example.yaml accounts.yaml
   ```
   将你的各个微信账号的 `dbkey` 填入 `accounts.yaml`，并分配独立的端口（如 9876, 9877）。
2. 在项目根目录创建 `media` 文件夹和 `copywriting.txt` 文件：
   - 往 `media` 里放几张图片（`.jpg`, `.png`）或视频（`.mp4`）。
   - 在 `copywriting.txt` 里每行写一句文案。

### 4. 准备视觉模板图 (Templates)
这是视觉识别的关键。请在 `templates/` 目录下放入以下截图（分辨率需与你运行时的屏幕一致）：
- `discover.png`：微信左侧边栏“发现”图标
- `moments_entry.png`：发现页的“朋友圈”入口
- `my_avatar.png`：朋友圈页面顶部，你自己的头像
- `delete_menu.png`：朋友圈动态右下角的 `...` 菜单图标
- `confirm_delete.png`：删除弹窗中的“删除”按钮
- `camera.png`：朋友圈页面右上角的“相机”图标
- `publish.png`：编辑页面的“发表”按钮

*(注：图片尽量裁剪得小且精准，不包含过多背景)*

### 5. 启动系统
你需要开启多个终端窗口：

**终端 1：启动微信大号的 Worker**
```bash
venv\Scripts\activate
python bot_worker.py "微信大号"
```

**终端 2：启动微信小号的 Worker**
```bash
venv\Scripts\activate
python bot_worker.py "微信小号"
```

**终端 3：启动主控调度器**
```bash
venv\Scripts\activate
python master_controller.py
```

主控器会根据 `accounts.yaml` 中的配置，自动把微信窗口拉起，通知对应的 Worker 执行“删旧发新”，并按照设定的随机间隔循环执行。

## 📄 License
[MIT License](LICENSE)