import time
import os
import random
import cv2
import numpy as np
import pyautogui
import pyperclip
from pydantic import BaseModel
from omni_bot_sdk.plugins.interface import Plugin, PluginExcuteContext

# 1. 更新配置类
class MomentsPluginConfig(BaseModel):
    enabled: bool = True
    priority: int = 900
    template_dir: str = "templates"
    confidence: float = 0.85
    media_dir: str = "media"                 # 素材文件夹
    copywriting_file: str = "copywriting.txt" # 文案文本

class MomentsPlugin(Plugin):
    name = "moments-plugin"
    priority = 900

    def __init__(self, bot=None):
        super().__init__(bot)
        self.priority = getattr(self.plugin_config, "priority", self.__class__.priority)
        self.template_dir = getattr(self.plugin_config, "template_dir", "templates")
        self.confidence = getattr(self.plugin_config, "confidence", 0.85)
        self.media_dir = getattr(self.plugin_config, "media_dir", "media")
        self.copywriting_file = getattr(self.plugin_config, "copywriting_file", "copywriting.txt")

    def get_priority(self) -> int:
        return self.priority

    # ---------- 视觉定位 ----------
    def _find_on_screen(self, template_name, timeout=8):
        template_path = os.path.join(self.template_dir, template_name)
        template = cv2.imread(template_path)
        if template is None:
            self.logger.error(f"找不到模板图: {template_path}")
            return None
        h, w = template.shape[:2]
        deadline = time.time() + timeout
        while time.time() < deadline:
            screen = np.array(pyautogui.screenshot())
            screen_gray = cv2.cvtColor(screen, cv2.COLOR_RGB2GRAY)
            template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
            result = cv2.matchTemplate(screen_gray, template_gray, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            if max_val >= self.confidence:
                return max_loc[0] + w // 2, max_loc[1] + h // 2
            time.sleep(0.3)
        return None

    def _click_on(self, template_name, timeout=8):
        pos = self._find_on_screen(template_name, timeout)
        if pos:
            pyautogui.click(*pos)
            time.sleep(0.6)
            return True
        return False

    # ---------- 删除上一条朋友圈 ----------
    def _delete_latest_moment(self):
        self.logger.info("开始删除上一条朋友圈...")
        if not self._click_on("discover.png"):
            self.logger.error("找不到发现入口")
            return False
        if not self._click_on("moments_entry.png"):
            self.logger.error("找不到朋友圈入口")
            return False
        time.sleep(1.5)
        if not self._click_on("my_avatar.png", timeout=5):
            self.logger.error("找不到自己的头像/名字入口")
            return False
        time.sleep(1.5)
        if not self._click_on("delete_menu.png", timeout=6):
            self.logger.error("找不到朋友圈的菜单按钮")
            return False
        
        time.sleep(0.5)
        pyautogui.press("down")
        pyautogui.press("enter")
        
        time.sleep(1.5)
        if self._click_on("confirm_delete.png", timeout=5):
            self.logger.info("已成功点击确认删除")
        else:
            self.logger.warning("视觉没找到确认删除按钮，尝试盲按回车作为备选...")
            pyautogui.press("enter")
            
        time.sleep(1.0)
        self.logger.info("删除流程结束")
        return True

    # ---------- 获取随机素材和文案 ----------
    def _get_random_material(self):
        # 获取随机文案
        content = "自动发布测试"
        if os.path.exists(self.copywriting_file):
            with open(self.copywriting_file, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]
                if lines:
                    content = random.choice(lines)

        # 获取随机媒体文件 (图片或视频)
        media_path = None
        if os.path.exists(self.media_dir):
            files = [f for f in os.listdir(self.media_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.mp4', '.mov'))]
            if files:
                media_path = os.path.abspath(os.path.join(self.media_dir, random.choice(files)))
        
        return content, media_path

    # ---------- 发布新朋友圈 (支持媒体) ----------
    def _publish_new_moment(self, content=None, media_path=None):
        # 如果没传参，自动去抽
        if content is None and media_path is None:
            content, media_path = self._get_random_material()
            
        self.logger.info(f"准备发布: 文案='{content}', 媒体='{media_path}'")

        # 获取相机按钮坐标
        camera_pos = self._find_on_screen("camera.png", timeout=6)
        if not camera_pos:
            self.logger.error("找不到相机按钮，发布失败")
            return False

        if media_path and os.path.exists(media_path):
            # ======== 发带图/视频的朋友圈 ========
            self.logger.info("检测到素材，执行单击相机流程...")
            pyautogui.click(*camera_pos)
            time.sleep(1.5)  # 等待 Windows 文件选择框弹出

            # 用剪贴板输入路径（避免中文和空格输入失败）
            pyperclip.copy(media_path)
            time.sleep(0.2)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.5)
            pyautogui.press('enter')  # 确定选择文件
            
            self.logger.info("文件已选择，等待加载完成...")
            time.sleep(3.0)  # 等待图片/视频加载

        else:
            # ======== 发纯文字的朋友圈 (长按) ========
            self.logger.info("无素材，执行长按相机发纯文字...")
            pyautogui.moveTo(camera_pos[0], camera_pos[1])
            pyautogui.mouseDown()
            time.sleep(0.8)
            pyautogui.mouseUp()
            time.sleep(1.5) # 等待文字界面加载

        # 无论是单图还是纯文字，接下来都要输入文案
        self.logger.info("正在输入文案...")
        pyperclip.copy(content)
        time.sleep(0.2)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(1.0)

        # ======== 点击发表 ========
        if self._click_on("publish.png", timeout=5):
            self.logger.info("已点击发表按钮")
        else:
            self.logger.warning("未找到发表按钮，尝试 Ctrl+Enter")
            pyautogui.hotkey('ctrl', 'enter')
            
        time.sleep(1.0)
        self.logger.info("发布流程结束")
        return True

    # ---------- 必须实现的抽象方法 ----------
    async def handle_message(self, context: PluginExcuteContext) -> None:
        message = context.get_message()
        content = getattr(message, "content", "") or ""
        # 这里留个简单的消息触发，但由于我们用 HTTP 控制，通常不会走到这里
        if "发朋友圈" in content:
            self._delete_latest_moment()
            time.sleep(1.0)
            self._publish_new_moment()
            context.should_stop = True

    def get_plugin_name(self) -> str:
        return self.name

    def get_plugin_description(self) -> str:
        return "自动删除上一条朋友圈并发布随机的图文/视频朋友圈"

    @classmethod
    def get_plugin_config_schema(cls):
        return MomentsPluginConfig