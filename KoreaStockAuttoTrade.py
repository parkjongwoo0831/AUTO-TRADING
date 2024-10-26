import requests
import json
import datetime
import time
import yaml

# config.yaml 파일에서 설정 값을 불러옵니다.
with open('config.yaml', encoding='UTF-8') as f:
    _cfg = yaml.load(f, Loader=yaml.FullLoader)

# 필요한 설정 값들을 config.yaml 파일에서 불러와 저장합니다.
APP_KEY = _cfg['APP_KEY']  # API 키
APP_SECRET = _cfg['APP_SECRET']  # API 비밀 키
ACCESS_TOKEN = ""  # API 접근 토큰, 빈 문자열로 초기화 후 추후 발급 받음
CANO = _cfg['CANO']  # 계좌 번호
ACNT_PRDT_CD = _cfg['ACNT_PRDT_CD']  # 계좌 제품 코드
DISCORD_WEBHOOK_URL = _cfg['DISCORD_WEBHOOK_URL']  # 디스코드 웹훅 URL
URL_BASE = _cfg['URL_BASE']  # API URL 기본 경로

# 디스코드 메시지를 보내는 함수
def send_message(msg):
    """디스코드 메세지 전송"""
    now = datetime.datetime.now()  # 현재 시간을 가져옴
    message = {"content": f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] {str(msg)}"}  # 시간과 함께 메시지 구성
    requests.post(DISCORD_WEBHOOK_URL, data=message)  # 디스코드로 메시지 전송
    print(message)

# API 토큰을 발급받는 함수
def get_access_token():
    """토큰 발급"""
    headers = {"content-type": "application/json"}  # 요청 헤더 설정
    body = {"grant_type": "client_credentials", "appkey": APP_KEY, "appsecret": APP_SECRET}  # API 인증 정보
    PATH = "oauth2/tokenP"  # 토큰 발급 경로
    URL = f"{URL_BASE}/{PATH}"  # API 호출 URL
    res = requests.post(URL, headers=headers, data=json.dumps(body))  # API 호출
    ACCESS_TOKEN = res.json()["access_token"]  # 응답에서 access_token을 받아옴
    return ACCESS_TOKEN

# 데이터를 암호화하기 위한 해시 키 생성 함수
def hashkey(datas):
    """암호화"""
    PATH = "uapi/hashkey"  # 해시 키 생성 경로
    URL = f"{URL_BASE}/{PATH}"  # API 호출 URL
    headers = {
        'content-Type': 'application/json',
        'appKey': APP_KEY,
        'appSecret': APP_SECRET,
    }
    res = requests.post(URL, headers=headers, data=json.dumps(datas))  # API 호출
    hashkey = res.json()["HASH"]  # 응답에서 해시 키를 받아옴
    return hashkey

# 특정 종목의 현재가를 조회하는 함수
def get_current_price(code="005930"):
    """현재가 조회"""
    PATH = "uapi/domestic-stock/v1/quotations/inquire-price"  # 현재가 조회 경로
    URL = f"{URL_BASE}/{PATH}"  # API 호출 URL
    headers = {
        "Content-Type": "application/json",
        "authorization": f"Bearer {ACCESS_TOKEN}",  # 접근 토큰 추가
        "appKey": APP_KEY,
        "appSecret": APP_SECRET,
        "tr_id": "FHKST01010100"  # 현재가 조회 트랜잭션 ID
    }
    params = {
        "fid_cond_mrkt_div_code": "J",  # 주식 시장 구분 코드 (J는 코스피)
        "fid_input_iscd": code,  # 조회할 종목 코드
    }
    res = requests.get(URL, headers=headers, params=params)  # API 호출
    return int(res.json()['output']['stck_prpr'])  # 현재가 반환

# 변동성 돌파 전략을 기반으로 매수 목표가를 계산하는 함수
def get_target_price(code="005930"):
    """변동성 돌파 전략으로 매수 목표가 조회"""
    PATH = "uapi/domestic-stock/v1/quotations/inquire-daily-price"  # 일일 가격 조회 경로
    URL = f"{URL_BASE}/{PATH}"  # API 호출 URL
    headers = {
        "Content-Type": "application/json",
        "authorization": f"Bearer {ACCESS_TOKEN}",  # 접근 토큰 추가
        "appKey": APP_KEY,
        "appSecret": APP_SECRET,
        "tr_id": "FHKST01010400"  # 일일 가격 조회 트랜잭션 ID
    }
    params = {
        "fid_cond_mrkt_div_code": "J",  # 주식 시장 구분 코드
        "fid_input_iscd": code,  # 종목 코드
        "fid_org_adj_prc": "1",  # 원본 조정 가격 여부
        "fid_period_div_code": "D"  # 기간 코드 (D는 일간)
    }
    res = requests.get(URL, headers=headers, params=params)  # API 호출
    stck_oprc = int(res.json()['output'][0]['stck_oprc'])  # 오늘 시가
    stck_hgpr = int(res.json()['output'][1]['stck_hgpr'])  # 전일 고가
    stck_lwpr = int(res.json()['output'][1]['stck_lwpr'])  # 전일 저가
    target_price = stck_oprc + (stck_hgpr - stck_lwpr) * 0.5  # 변동성 돌파 목표가 계산
    return target_price

# 주식 잔고를 조회하는 함수
def get_stock_balance():
    """주식 잔고조회"""
    PATH = "uapi/domestic-stock/v1/trading/inquire-balance"  # 잔고 조회 경로
    URL = f"{URL_BASE}/{PATH}"  # API 호출 URL
    headers = {
        "Content-Type": "application/json",
        "authorization": f"Bearer {ACCESS_TOKEN}",  # 접근 토큰 추가
        "appKey": APP_KEY,
        "appSecret": APP_SECRET,
        "tr_id": "TTTC8434R",  # 잔고 조회 트랜잭션 ID
        "custtype": "P",  # 고객 타입 (P는 개인)
    }
    params = {
        "CANO": CANO,
        "ACNT_PRDT_CD": ACNT_PRDT_CD,
        "AFHR_FLPR_YN": "N",
        "OFL_YN": "",
        "INQR_DVSN": "02",
        "UNPR_DVSN": "01",
        "FUND_STTL_ICLD_YN": "N",
        "FNCG_AMT_AUTO_RDPT_YN": "N",
        "PRCS_DVSN": "01",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": ""
    }
    res = requests.get(URL, headers=headers, params=params)  # API 호출
    stock_list = res.json()['output1']  # 보유 주식 목록
    evaluation = res.json()['output2']  # 평가 금액 및 손익 정보
    stock_dict = {}  # 주식 보유 내역을 저장할 딕셔너리
    send_message(f"====주식 보유잔고====")
    for stock in stock_list:
        if int(stock['hldg_qty']) > 0:  # 보유 수량이 0보다 크면
            stock_dict[stock['pdno']] = stock['hldg_qty']  # 종목 코드와 보유 수량 저장
            send_message(f"{stock['prdt_name']}({stock['pdno']}): {stock['hldg_qty']}주")
            time.sleep(0.1)
    send_message(f"주식 평가 금액: {evaluation[0]['scts_evlu_amt']}원")
    time.sleep(0.1)
    send_message(f"평가 손익 합계: {evaluation[0]['evlu_pfls_smtl_amt']}원")
    time.sleep(0.1)
    send_message(f"총 평가 금액: {evaluation[0]['tot_evlu_amt']}원")
    time.sleep(0.1)
    send_message(f"=================")
    return stock_dict

# 현금 잔고를 조회하는 함수
def get_balance():
    """현금 잔고조회"""
    PATH = "uapi/domestic-stock/v1/trading/inquire-psbl-order"  # 주문 가능 잔고 조회 경로
    URL = f"{URL_BASE}/{PATH}"  # API 호출 URL
    headers = {
        "Content-Type": "application/json",
        "authorization": f"Bearer {ACCESS_TOKEN}",  # 접근 토큰 추가
        "appKey": APP_KEY,
        "appSecret": APP_SECRET,
        "tr_id": "TTTC8908R",  # 잔고 조회 트랜잭션 ID
        "custtype": "P",  # 고객 타입
    }
    params = {
        "CANO": CANO,
        "ACNT_PRDT_CD": ACNT_PRDT_CD,
        "PDNO": "005930",  # 특정 종목을 지정할 수 있음
        "ORD_UNPR": "50000",  # 지정가 주문 단가
        "ORD_DVSN": "01",  # 주문 구분
        "CMA_EVLU_AMT_ICLD_YN": "Y",  # CMA 평가 금액 포함 여부
        "OVRS_ICLD_YN": "Y"  # 해외 주식 포함 여부
    }
    res = requests.get(URL, headers=headers, params=params)  # API 호출
    cash = res.json()['output1'][0]['dnca_tot_amt']  # 현금 잔고 반환
    send_message(f"주문 가능 현금 잔고: {cash}원")
    return int(cash)


def buy(code="005930", qty="1"):
    """주식 시장가 매수"""
    # 매수 요청을 보낼 API의 경로 설정
    PATH = "uapi/domestic-stock/v1/trading/order-cash"
    URL = f"{URL_BASE}/{PATH}"  # 기본 URL과 PATH를 결합하여 전체 URL 생성
    
    # 매수 요청에 필요한 데이터 설정
    data = {
        "CANO": CANO,  # 고객 계좌 번호
        "ACNT_PRDT_CD": ACNT_PRDT_CD,  # 계좌 상품 코드
        "PDNO": code,  # 종목 코드 (기본값: 삼성전자)
        "ORD_DVSN": "01",  # 주문 구분 코드 (시장가 주문)
        "ORD_QTY": str(int(qty)),  # 주문 수량
        "ORD_UNPR": "0",  # 주문 가격 (0은 시장가 주문)
    }
    
    # 요청 헤더 설정
    headers = {
        "Content-Type": "application/json",  # 데이터 형식 설정
        "authorization": f"Bearer {ACCESS_TOKEN}",  # 인증 토큰
        "appKey": APP_KEY,  # 앱 키
        "appSecret": APP_SECRET,  # 앱 비밀 키
        "tr_id": "TTTC0802U",  # 거래 ID (매수용)
        "custtype": "P",  # 고객 유형 (개인)
        "hashkey": hashkey(data)  # 해시키(데이터 암호화)
    }
    
    # 매수 요청을 POST 방식으로 전송
    res = requests.post(URL, headers=headers, data=json.dumps(data))
    
    # 응답 코드가 '0'이면 매수 성공
    if res.json()['rt_cd'] == '0':
        send_message(f"[매수 성공]{str(res.json())}")  # 성공 메시지 전송
        return True
    else:
        send_message(f"[매수 실패]{str(res.json())}")  # 실패 메시지 전송
        return False

def sell(code="005930", qty="1"):
    """주식 시장가 매도"""
    # 매도 요청을 보낼 API의 경로 설정
    PATH = "uapi/domestic-stock/v1/trading/order-cash"
    URL = f"{URL_BASE}/{PATH}"  # 기본 URL과 PATH를 결합하여 전체 URL 생성
    
    # 매도 요청에 필요한 데이터 설정
    data = {
        "CANO": CANO,  # 고객 계좌 번호
        "ACNT_PRDT_CD": ACNT_PRDT_CD,  # 계좌 상품 코드
        "PDNO": code,  # 종목 코드 (기본값: 삼성전자)
        "ORD_DVSN": "01",  # 주문 구분 코드 (시장가 주문)
        "ORD_QTY": qty,  # 주문 수량
        "ORD_UNPR": "0",  # 주문 가격 (0은 시장가 주문)
    }
    
    # 요청 헤더 설정
    headers = {
        "Content-Type": "application/json",  # 데이터 형식 설정
        "authorization": f"Bearer {ACCESS_TOKEN}",  # 인증 토큰
        "appKey": APP_KEY,  # 앱 키
        "appSecret": APP_SECRET,  # 앱 비밀 키
        "tr_id": "TTTC0801U",  # 거래 ID (매도용)
        "custtype": "P",  # 고객 유형 (개인)
        "hashkey": hashkey(data)  # 해시키(데이터 암호화)
    }
    
    # 매도 요청을 POST 방식으로 전송
    res = requests.post(URL, headers=headers, data=json.dumps(data))
    
    # 응답 코드가 '0'이면 매도 성공
    if res.json()['rt_cd'] == '0':
        send_message(f"[매도 성공]{str(res.json())}")  # 성공 메시지 전송
        return True
    else:
        send_message(f"[매도 실패]{str(res.json())}")  # 실패 메시지 전송
        return False

# 자동매매 시작
try:
    ACCESS_TOKEN = get_access_token()  # 인증 토큰 발급

    # 매수 희망 종목 리스트 설정
    symbol_list = ["005930", "035720", "000660", "069500"]  
    bought_list = []  # 매수 완료된 종목 리스트
    total_cash = get_balance()  # 보유 현금 조회
    stock_dict = get_stock_balance()  # 보유 주식 조회
    for sym in stock_dict.keys():  # 보유 주식에서 매수한 종목 리스트 생성
        bought_list.append(sym)

    target_buy_count = 3  # 매수할 종목 수
    buy_percent = 0.33  # 종목당 매수 금액 비율
    buy_amount = total_cash * buy_percent  # 종목별 주문 금액 계산
    soldout = False  # 매도 완료 플래그

    send_message("===국내 주식 자동매매 프로그램을 시작합니다===")
    
    while True:  # 무한 루프 시작
        t_now = datetime.datetime.now()  # 현재 시간
        t_9 = t_now.replace(hour=9, minute=0, second=0, microsecond=0)  # 오전 9시
        t_start = t_now.replace(hour=9, minute=5, second=0, microsecond=0)  # 오전 9시 5분
        t_sell = t_now.replace(hour=15, minute=15, second=0, microsecond=0)  # 오후 3시 15분
        t_exit = t_now.replace(hour=15, minute=20, second=0, microsecond=0)  # 오후 3시 20분
        today = datetime.datetime.today().weekday()  # 오늘의 요일
        
        # 주말이면 프로그램 종료
        if today == 5 or today == 6:  
            send_message("주말이므로 프로그램을 종료합니다.")
            break
        
        # 오전 9시 ~ 오전 9시 5분 사이에 잔여 수량 매도
        if t_9 < t_now < t_start and soldout == False:
            for sym, qty in stock_dict.items():  # 보유 주식 매도
                sell(sym, qty)
            soldout = True  # 매도 완료 플래그 설정
            bought_list = []  # 매수한 종목 리스트 초기화
            stock_dict = get_stock_balance()  # 보유 주식 정보 갱신
        
        # 오전 9시 5분 ~ 오후 3시 15분 사이에 매수
        if t_start < t_now < t_sell:
            for sym in symbol_list:  # 매수 희망 종목 리스트 순회
                if len(bought_list) < target_buy_count:  # 매수할 종목 수에 도달하지 않은 경우
                    if sym in bought_list:  # 이미 매수한 종목이면 건너뜀
                        continue
                    
                    target_price = get_target_price(sym)  # 매수 목표가 조회
                    current_price = get_current_price(sym)  # 현재가 조회
                    
                    # 현재가가 목표가를 초과하면 매수 시도
                    if target_price < current_price:
                        buy_qty = 0  # 매수할 수량 초기화
                        buy_qty = int(buy_amount // current_price)  # 매수 수량 계산
                        if buy_qty > 0:  # 매수할 수량이 0보다 크면
                            send_message(f"{sym} 목표가 달성({target_price} < {current_price}) 매수를 시도합니다.")
                            result = buy(sym, buy_qty)  # 매수 요청
                            if result:  # 매수 성공 시
                                soldout = False  # 매도 완료 플래그 초기화
                                bought_list.append(sym)  # 매수한 종목 리스트에 추가
                                get_stock_balance()  # 보유 주식 정보 갱신
                    time.sleep(1)  # 1초 대기
            time.sleep(1)  # 1초 대기
            
            # 30분에 잔고 조회
            if t_now.minute == 30 and t_now.second <= 5: 
                get_stock_balance()  # 보유 주식 정보 갱신
                time.sleep(5)  # 5초 대기
        
        # 오후 3시 15분 ~ 오후 3시 20분 사이에 일괄 매도
        if t_sell < t_now < t_exit:
            if soldout == False:  # 매도 완료되지 않은 경우
                stock_dict = get_stock_balance()  # 보유 주식 조회
                for sym, qty in stock_dict.items():  # 보유 주식 매도
                    sell(sym, qty)
                soldout = True  # 매도 완료 플래그 설정
                bought_list = []  # 매수한 종목 리스트 초기화
                time.sleep(1)  # 1초 대기
        
        # 오후 3시 20분 이후 프로그램 종료
        if t_exit < t_now:  
            send_message("프로그램을 종료합니다.")
            break

except Exception as e:
    send_message(f"[오류 발생]{e}")  # 오류 발생 시 메시지 전송
    time.sleep(1)  # 1초 대기
