from dotenv import load_dotenv
import os
import pytz

# .env 파일에서 환경 변수를 로드합니다
load_dotenv()

# 환경 변수를 불러옵니다
TOKEN = os.getenv('DISCORD_TOKEN')
ANNOUNCEMENT_CHANNEL_ID = os.getenv('ANNOUNCEMENT_CHANNEL_ID')
ADMIN_ROLE_ID = os.getenv('ADMIN_ROLE_ID')
USER_IDS = os.getenv('USER_IDS').split(',')

# 환경 변수가 제대로 로드되었는지 확인합니다
if TOKEN is None:
    raise ValueError("DISCORD_TOKEN 환경 변수가 설정되지 않았습니다.")
if ANNOUNCEMENT_CHANNEL_ID is None:
    raise ValueError("ANNOUNCEMENT_CHANNEL_ID 환경 변수가 설정되지 않았습니다.")
if ADMIN_ROLE_ID is None:
    raise ValueError("ADMIN_ROLE_ID 환경 변수가 설정되지 않았습니다.")
if not USER_IDS:
    raise ValueError("USER_IDS 환경 변수가 설정되지 않았습니다.")

KST = pytz.timezone('Asia/Seoul')

# ANNOUNCEMENT_CHANNEL_ID, ADMIN_ROLE_ID 및 SYSTEM_USER_ID를 정수로 변환합니다
ANNOUNCEMENT_CHANNEL_ID = int(ANNOUNCEMENT_CHANNEL_ID)
ADMIN_ROLE_ID = int(ADMIN_ROLE_ID)