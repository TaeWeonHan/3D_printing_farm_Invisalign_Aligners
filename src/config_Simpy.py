import numpy as np  # numpy 모듈로 수정
import random

#### 시뮬레이션 설정 ###########################################################
# SIM_TIME: 시뮬레이션이 진행될 총 기간 (일 단위)
# 예시: SIM_TIME = 7 -> 시뮬레이션이 7일 동안 진행됨
#### Job 생성 파라미터 설정 ####################################################
# JOB_ARRIVAL_RATE: 포아송 분포의 λ 값, 단위 시간당 평균 Job 발생 수를 의미함
# JOB_INTERVAL: Job 생성 간격 (시간 단위), 기본은 24시간 (하루에 한 번 Job 생성)
# JOB_CREATION_INTERVAL: Job 생성 간격의 평균값 (시간 단위)
#### 주문 관련 설정 ###########################################################
# ORDER_CYCLE: 주문이 반복되는 주기, 매일 주문이 발생하도록 설정 (일 단위)
# ORDER_QUANTITY_RANGE: 주문 수량의 최소 및 최대 범위를 지정 (랜덤 값으로 생성)
#### Job의 속성 정의 ##########################################################
# JOB_TYPES: Job의 속성 정의 사전, 기본 Job 유형의 다양한 속성 범위를 포함함
# - VOLUME_RANGE: Job 볼륨의 최소/최대 범위 (예: 1에서 45)
# - BUILD_TIME_RANGE: Job 제작 시간 범위 (예: 1에서 5일)
# - POST_PROCESSING_TIME_RANGE: 후처리 시간 범위
# - PACKAGING_TIME_RANGE: 포장 시간 범위
#### 후처리 작업자 설정 ########################################################
# POST_PROCESSING_WORKER: 작업자 정보 설정, 각 작업자의 ID를 포함
# 작업자가 동시에 처리할 수 있는 Job은 1개로 제한됨
#### 수요량 설정 ##############################################################
# DEMAND_QTY_MIN: 하루 수요량의 최소값
# DEMAND_QTY_MAX: 하루 수요량의 최대값
# DEMAND_QTY_FUNC(): 하루 수요량을 결정하는 함수, 최소값과 최대값 사이에서 랜덤 선택
#### 3D 프린터 정보 설정 #######################################################
# PRINTERS: 각 프린터의 정보 설정 (ID와 최대 처리 용량)
# PRINTERS_INVEN: 각 프린터별 Job 대기열을 저장하는 리스트

# 시뮬레이션 설정
SIM_TIME = 2  # 시뮬레이션 기간 (일 단위)

# Job 생성 파라미터 설정
JOB_CREATION_INTERVAL = 3  # 평균 1시간 간격으로 Job 생성

# MIN, MAX RANGE / 단위: mm
RANGE_CONTROLLA = {
    "LENGHT_RANGE" : {
        "WIDTH": {
            "MIN": 10,
            "MAX": 15
        },
        "HEIGHT": {
            "MIN": 10,
            "MAX": 15
        },
        "DEPTH": {
            "MIN": 10,
            "MAX": 15
        }
    },
    "TIME_RANGE" : {
        "SMALL_PACKAGING_TIME": {
            "MIN": 10,
            "MAX": 20
        },
        "LARGE_PACKAGING_TIME": {
            "MIN": 20,
            "MAX": 30
        }
        ,"WASHING_TIME": {
            "MIN": 10,
            "MAX": 15
        }
    }
}


# Job의 속성 정의
JOB_TYPES = {
    "DEFAULT": {
        "WIDTH_RANGE": (RANGE_CONTROLLA["LENGHT_RANGE"]["WIDTH"]["MIN"], RANGE_CONTROLLA["LENGHT_RANGE"]["WIDTH"]["MAX"]), # 단위: mm
        "HEIGHT_RANGE": (RANGE_CONTROLLA["LENGHT_RANGE"]["HEIGHT"]["MIN"], RANGE_CONTROLLA["LENGHT_RANGE"]["HEIGHT"]["MAX"]), # 단위: mm
        "DEPTH_RANGE": (RANGE_CONTROLLA["LENGHT_RANGE"]["DEPTH"]["MIN"], RANGE_CONTROLLA["LENGHT_RANGE"]["DEPTH"]["MAX"]), # 단위: mm
        "POST_PROCESSING_TIME_COEFFICIENT": 30,  # 후처리 시간 범위
        "SMALL_PACKAGING_TIME_RANGE": (RANGE_CONTROLLA["TIME_RANGE"]["SMALL_PACKAGING_TIME"]["MIN"], RANGE_CONTROLLA["TIME_RANGE"]["SMALL_PACKAGING_TIME"]["MAX"]),  # SMALL 제품 포장시간 범위
        "LARGE_PACKAGING_TIME_RANGE": (RANGE_CONTROLLA["TIME_RANGE"]["LARGE_PACKAGING_TIME"]["MIN"], RANGE_CONTROLLA["TIME_RANGE"]["LARGE_PACKAGING_TIME"]["MAX"]),  # LARGE 제품 포장시간 범위
        "FILAMENT_DIAMETER": 1.75,
        "BUILD_SPEED": 3600,
        "WASHING_RANGE": (RANGE_CONTROLLA["TIME_RANGE"]["WASHING_TIME"]["MIN"], RANGE_CONTROLLA["TIME_RANGE"]["WASHING_TIME"]["MAX"])
    }
}

SATISFICATION_TYPE = {
    "POSITIVE" : 1,
    "NEGATIVE" : -0.1
}

COST_TYPES = {
    0: {
        'HOLDING_COST': 0.1,
        'PRINTING_COST': 1,
        'WASHING_COST': 1,
        'DRYING_COST': 1,
        'POSTPROCESSING_COST': 1,
        'PACKAGING_COST': 1,
        'DELIVERY_COST': 1,
        'SHORTAGE_COST' : 1
    }
}

CUSTOMER = {
    "JOB_LIST_SIZE": 2,
     "ITEM_SIZE": 2
     }

# 3D 프린터 정보 설정, VOL: WIDTH * HEIGHT * DEPTH / 단위: mm
PRINTERS = {
    0: {"ID": 0}, 
    1: {"ID": 1},
    2: {"ID": 2},
    3: {"ID": 3},
    4: {"ID": 4}
}

# unit: mm
PRINTERS_SIZE = {"VOL": 669130000, "WIDTH": 1540, "HEIGHT": 790, "DEPTH": 550, "SET_UP": 10, "CLOSING": 30}

BATCH_TIMEOUT = 1

WASHING_MACHINE = {
    0: {"ID": 0, "WASHING_SIZE": 3},
    1: {"ID": 1, "WASHING_SIZE": 3}
}

DRY_MACHINE = {
    0: {"ID": 0, "DRYING_SIZE": 3},
    1: {"ID": 1, "DRYING_SIZE": 3}
}

POST_PROCESSING_WORKER = {
    0: {"ID": 0},
    1: {"ID": 1},
    2: {"ID": 2},
    3: {"ID": 3},
    4: {"ID": 4},
    5: {"ID": 5}
}

PACKAGING_MACHINE = {
    0: {"ID": 0},
    1: {"ID": 1},
    2: {"ID": 2}
}

DISPATCHING_RULE = {
    "FIFO" : False,
    "LIFO" : False,
    "SPT" : True,
    "LPT" : False,
    "EDD" : False
}

PRINT_SATISFICATION = True
VISUALIZATION = True
PRINT_SIM_EVENTS = True
PRINT_SIM_COST = True  # True로 설정하면 비용이 출력됨, False로 설정하면 출력되지 않음