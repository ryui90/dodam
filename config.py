import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
DB_PATH = os.getenv("DB_PATH", "bot_data.db")

# 서버 대표 컬러 (연초록 -> 노랑)
COLOR_MAIN = 71aeff
COLOR_SUB = cf98ff
GRADIENT_START = (113, 174, 255)  # 연초록 RGB
GRADIENT_END = (207, 152, 255)     # 노랑 RGB

# 프로필 카드용 폰트 (한글 지원 폰트 필요 - README 참고)
FONT_BOLD_PATH = "assets/fonts/NotoSansKR-Bold.ttf"
FONT_REGULAR_PATH = "assets/fonts/NotoSansKR-Regular.ttf"

# 포인트 환산: 음성 5분(300초)당 100포인트, 채팅 1회당 1포인트
VOICE_POINT_PER_SECOND = 100 / 300
CHAT_POINT_PER_MESSAGE = 1
