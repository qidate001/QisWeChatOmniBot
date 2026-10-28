import sys
import time
import threading
import yaml
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

# 确保控制台输出中文不乱码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from omni_bot_sdk.bot import Bot

# 全局变量存储当前 bot 实例和插件
bot_instance = None
plugin_instance = None
current_port = 0

def execute_fq(action_type="publish"):
    if not plugin_instance:
        print("[警告] 插件尚未加载完成，忽略指令")
        return
    print(f"\n[{time.strftime('%H:%M:%S')}] 收到指令，开始执行: {action_type}")
    try:
        if action_type == "publish":
            # 1. 删除旧朋友圈
            plugin_instance._delete_latest_moment()
            time.sleep(1.0)
            
            # 2. 发布新朋友圈（不传参数，让插件内部自己去素材库随机抽）
            plugin_instance._publish_new_moment()
            
    except Exception as e:
        print(f"❌ 执行出错: {e}")
        import traceback
        traceback.print_exc()

class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        action_type = self.path.strip("/") or "publish"
        self.send_response(200)
        self.end_headers()
        self.wfile.write(f"Triggered {action_type}".encode())
        # 新开线程执行，避免阻塞 HTTP 响应
        threading.Thread(target=execute_fq, args=(action_type,)).start()

    def log_message(self, format, *args):
        pass # 屏蔽 HTTP 默认的 log 输出

def main():
    global bot_instance, plugin_instance, current_port
    
    if len(sys.argv) < 2:
        print("用法: python bot_worker.py <account_name>")
        sys.exit(1)
        
    target_account = sys.argv[1]
    
    # 读取总配置
    with open("accounts.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
        
    account_cfg = next((a for a in config["accounts"] if a["name"] == target_account), None)
    if not account_cfg:
        print(f"未找到账号配置: {target_account}")
        sys.exit(1)
        
    current_port = account_cfg["port"]
    print(f"正在启动 [{target_account}]，分配端口: {current_port}")

    # 生成针对该账号的临时 config.yaml
    bot_config = {
        "dbkey": account_cfg["dbkey"],
        "mqtt": {"host": "127.0.0.1", "port": 1883, "client_id": f"omni_{current_port}"},
        "plugins": {
            "moments-plugin": {
                "enabled": True,
                "priority": 900,
                "template_dir": "templates",
                "confidence": 0.85,
                "media_dir": "media",                    # 修复：补齐逗号
                "copywriting_file": "copywriting.txt"    # 修复：补齐逗号
            }
        }
    }
    temp_config_path = f"config_{current_port}.yaml"
    with open(temp_config_path, "w", encoding="utf-8") as f:
        yaml.dump(bot_config, f, allow_unicode=True)

    # 启动 HTTP 服务
    server = HTTPServer(('127.0.0.1', current_port), RequestHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"[{target_account}] HTTP 接口已就绪: http://127.0.0.1:{current_port}")
    
    # 启动 Bot
    bot_instance = Bot(config_path=temp_config_path)
    bot_thread = threading.Thread(target=bot_instance.start, daemon=True)
    bot_thread.start()

    print("等待 Bot 启动，请稍候...")
    while not bot_instance.is_running:
        time.sleep(1)
        
    # 挂载插件
    for p in bot_instance.plugin_manager.plugins:
        if p.get_plugin_name() == "moments-plugin":
            plugin_instance = p
            break
            
    # ====== 获取并保存 PID ======
    wx_pid = bot_instance.user_info.pid
    print(f"[{target_account}] 绑定的微信进程 PID: {wx_pid}")
    
    with open(f"pid_{current_port}.txt", "w") as f:
        f.write(str(wx_pid))

    print(f"✅ [{target_account}] Bot 已全部就绪，等待主控指令...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n[{target_account}] 正在退出...")
        bot_instance.teardown()

if __name__ == "__main__":
    main()