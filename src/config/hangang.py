import requests

# 한강 물 온도 API 클래스
class Hangang:
    ENDPOINT = "https://api.hangang.life/"

    def request(self):
        response = requests.get(self.ENDPOINT, headers={'User-Agent': 'Renyu106/Hangang-API'})  # verify=True는 기본값
        if response.status_code == 200:
            try:
                json_response = response.json()
                return json_response
            except ValueError:
                return None
        else:
            return None

    def get_info(self):
        response = self.request()
        if response and 'STATUS' in response and response['STATUS'] == "OK":
            hangang_data = response['DATAs']['DATA']['HANGANG']
            if '선유' in hangang_data:
                data = hangang_data['선유']
                return {
                    'status': "ok",
                    'temp': data['TEMP'],
                    'last_update': data['LAST_UPDATE'],
                    'ph': data['PH']
                }
            else:
                return {
                    'status': "error",
                    'msg': "선유 데이터를 찾을 수 없습니다."
                }
        else:
            return {
                'status': "error",
                'msg': "API를 불러오는데 실패했습니다."
            }