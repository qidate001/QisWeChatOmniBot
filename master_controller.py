import time
import random
import requests
import yaml
import os
import win32gui
import win32con
import win32process
import win32api

def load_config():
    with open("accounts.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def trigger_bot(port: int):
    """通知对应端口的 bot 干活"""
    try:
        res = requests.post(f"http://127.0.0.1:{port}/publish", timeout=5)
        if res.status_code == 200:
            print(f"🚀 已向端口 {port} 发送执行指令")
    except Exception as e:
        print(f"❌ 无法连接到端口 {port}: {e}")

def get_all_worker_pids(accounts):
    """读取所有配置的 PID 文件，返回一个 PID 列表"""
    pids = []
    for acc in accounts:
        pid_file = f"pid_{acc['port']}.txt"
        if os.path.exists(pid_file):
            with open(pid_file, "r") as f:
                try:
                    pids.append(int(f.read().strip()))
                except ValueError:
                    pass
    return pids

def switch_wechat_by_pid(target_pid: int, all_pids: list) -> bool:
    """通过 PID 找窗口，激活目标，最小化其他所有由 bot_worker 启动的微信"""
    
    # 收集窗口句柄：{pid: hwnd}
    pid_to_hwnd = {}
    
    def enum_windows_callback(hwnd, extra):
        if not win32gui.IsWindowVisible(hwnd):
            return
        
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        
        # 过滤：只找我们在 all_pids 里记录的进程，且窗口尺寸足够大（排除小窗口）
        if pid in all_pids:
            rect = win32gui.GetWindowRect(hwnd)
            width = rect[2] - rect[0]
            height = rect[3] - rect[1]
            if width > 500 and height > 500:
                pid_to_hwnd[pid] = hwnd
                
    win32gui.EnumWindows(enum_windows_callback, None)
    
    target_hwnd = pid_to_hwnd.get(target_pid)
    
    if not target_hwnd:
        print(f"❌ 未找到 PID 为 {target_pid} 的微信主窗口")
        return False
        
    # 1. 把其他微信窗口最小化
    for pid, hwnd in pid_to_hwnd.items():
        if pid != target_pid:
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            
    # 2. 把目标微信带到前台
    try:
        # 如果最小化了，先恢复
        if win32gui.IsIconic(target_hwnd):
            win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
            
        # 暴力置顶技巧：先最小化再恢复，或者用 AttachThreadInput
        # 这里用最简单的虚拟按键骗过 Windows 的防抢焦点机制
        win32api.keybd_event(win32con.VK_MENU, 0, 0, 0) # 按下 Alt
        win32gui.SetForegroundWindow(target_hwnd)
        win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0) # 松开 Alt
        
        print(f"✅ 已切换到 PID: {target_pid} 的微信窗口")
        return True
    except Exception as e:
        print(f"❌ 激活失败: {e}")
        return False

def main():
    config = load_config()
    sched = config["scheduler"]
    accounts = config["accounts"]
    
    min_minutes = sched["min_interval_minutes"]
    max_minutes = sched["max_interval_minutes"]
    timeout = sched["execution_timeout"]
    
    acc_min_sec = sched.get("account_interval_min_seconds", 10)
    acc_max_sec = sched.get("account_interval_max_seconds", 30)
    
    print("--- 多账号调度中心已启动 (PID 精准控制版) ---")
    
    while True:
        random.shuffle(accounts)
        print(f"\n================ 开始新一轮任务 ================")
        
        # 每一轮开始时，收集当前所有在跑的 bot 的 PID
        all_active_pids = get_all_worker_pids(accounts)
        
        if not all_active_pids:
            print("⚠️ 未发现任何活动的 bot_worker，请检查 PID 文件。休眠 1 分钟...")
            time.sleep(60)
            continue

        for account in accounts:
            name = account["name"]
            port = account["port"]
            pid_file = f"pid_{port}.txt"
            
            print(f"[{time.strftime('%H:%M:%S')}] 准备操作账号: {name}")
            
            if not os.path.exists(pid_file):
                print(f"⚠️ 找不到 {pid_file}，跳过。")
                continue
                
            with open(pid_file, "r") as f:
                target_pid = int(f.read().strip())
            
            if switch_wechat_by_pid(target_pid, all_active_pids):
                time.sleep(1.5)
                trigger_bot(port)
                
                print(f"⏳ 正在执行，请勿操作鼠标键盘 ({timeout} 秒)...")
                time.sleep(timeout)
                print(f"✅ {name} 操作周期结束")
            else:
                print(f"⚠️ 跳过 {name}，无法切换窗口")
            
            if account != accounts[-1]:
                wait_acc_sec = random.randint(acc_min_sec, acc_max_sec)
                print(f"💤 账号间冷却，随机沉睡 {wait_acc_sec} 秒...")
                time.sleep(wait_acc_sec)
                
        wait_seconds = random.randint(min_minutes * 60, max_minutes * 60)
        wait_mins = wait_seconds / 60
        print(f"\n💤 本轮所有账号已执行完毕，休眠 {wait_mins:.1f} 分钟，等待下一轮...")
        time.sleep(wait_seconds)

if __name__ == "__main__":
    main()