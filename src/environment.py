import simpy
import numpy as np
from config_Simpy import *  # 설정 파일 (JOB_TYPES, PRINTERS, PRINTERS_INVEN 등)
from log_simpy import *  # 로그 파일 (DAILY_EVENTS 등)
from dispatching_method import *

# Display 클래스: 시뮬레이션 시간(일 단위)을 추적하고 일별 보고서를 기록
class Display:
    def __init__(self, env, daily_events):
        self.env = env  # SimPy 환경 객체
        self.daily_events = daily_events  # 일별 이벤트 로그 리스트

    def track_days(self):
        """현재 날짜를 추적하여 DAILY_EVENTS에 기록"""
        while True:
            day = int(self.env.now // 24) + 1  # 현재 시뮬레이션 시간을 일 단위로 계산
            self.daily_events.append(f"\n===== Day {day} Report: =====")  # 일별 보고서 제목 추가
            yield self.env.timeout(24)  # 24시간(1일)마다 실행

class Order:
    def __init__(self, order_id, jobs):
        self.order_id = order_id
        self.jobs = jobs  # 이 주문에 포함된 Job 리스트
        # 필요에 따라 생성 시각 등 추가 정보를 기록할 수 있음.
        self.create_time = jobs[0].create_time if jobs else None
        # order_build_time: 주문 내 모든 Job의 build_time의 합
        self.order_build_time = 1
        # pallet washing hours
        self.pallet_washing_time = np.random.randint(JOB_TYPES["DEFAULT"]["WASHING_RANGE"])

# Customer 클래스: 지속적으로 Job(작업)을 생성
class Customer:
    def __init__(self, env, shortage_cost, daily_events, satisfication, order_store):
        self.env = env
        self.daily_events = daily_events
        self.current_job_id = 0   # Job ID 생성에 사용 (Order 내 Job마다 부여)
        self.current_order_id = 0 # Order ID 생성에 사용
        self.unit_shortage_cost = shortage_cost
        self.satisfication = satisfication
        self.order_store = order_store  # simpy.Store 혹은 큐
        self.temp_order_list = []       # 누적된 주문(Order)들을 임시로 저장

    def create_orders_continuously (self):
        """지속적으로 Job을 생성하고 프린터에 할당"""

        while True:
            # SIM_TIME 이후에는 Job 생성 중단
            if self.env.now >= SIM_TIME * 24:
                break

            # 현재 날짜 계산
            day = int(self.env.now // 24) + 1
            
            # 한 주문을 위해 JOB_SIZE 개의 Job을 동시에 생성
            order_jobs = []

            for _ in range(CUSTOMER["JOB_SIZE"]):

                # Job 생성
                job = Job(self.env, self.current_job_id, JOB_TYPES["DEFAULT"])
                self.current_job_id += 1

                # JOB_LOG에 Job 기록 추가
                JOB_LOG.append({
                    'day': day,
                    'job_id': job.job_id,
                    'width': job.width,
                    'height': job.height,
                    'depth': job.depth,
                    'create_time': job.create_time,
                    'volume': job.volume,
                    'build_time': job.build_time,
                    'post_processing_time': job.post_processing_time,
                    'packaging_time': job.packaging_time
                })

                if (job.width <= PRINTERS_SIZE["WIDTH"] and job.height <= PRINTERS_SIZE["HEIGHT"] and job.depth <= PRINTERS_SIZE["DEPTH"]):
                    order_jobs.append(job)

                
                else:
                    # Shortage cost 발생: 적합한 프린터가 없을 때
                    self.daily_events.append(
                        f"Job {job.job_id} could not be assigned: No suitable printer available (Job size: {job.volume:.2f})"
                    )
                    # Shortage cost 발생
                    job.shortage = 1  # Shortage는 한 번에 한 프린터가 부족할 때 1로 설정
                    
                    if PRINT_SIM_COST:
                        Cost.cal_cost(job, "Shortage cost")
                    
                    if PRINT_SATISFICATION:
                        # 고객 만족도 계산
                        self.satisfication.cal_satisfication(job, self.env.now)
            
            # 생성된 JOB_SIZE 개의 Job들을 하나의 Order 객체로 묶음
            new_order = Order(self.current_order_id, order_jobs)
            self.current_order_id += 1
            '''
            self.daily_events.append(
                f"{int(self.env.now % 24)}:{int((self.env.now % 1)*60):02d} - Order {new_order.order_id} created with {len(order_jobs)} jobs."
            )
            '''
            self.temp_order_list.append(new_order)

            # 만약 누적된 주문이 ORDER_LIST_SIZE 만큼 모였으면 order_store에 배치로 넣기
            if len(self.temp_order_list) >= CUSTOMER["ORDER_LIST_SIZE"]:
                self.daily_events.append(
                    f"{int(self.env.now % 24)}:{int((self.env.now % 1)*60):02d} - {len(self.temp_order_list)} orders accumulated. Sending batch to printer."
                )
                for order_item in self.temp_order_list:
                    # 비동기로 order_store에 넣음
                    self.order_store.put(order_item)
                self.temp_order_list.clear()

            '''
            # dispatching rule 적용 후 total_job_list에 job_list 추가
            if len(job_list) == CUSTOMER["ORDER_LIST_SIZE"]:
                
                if DISPATCHING_RULE["FIFO"]:
                    next_process_job_list = FIFO(job_list)
                
                elif DISPATCHING_RULE["LIFO"]:
                    next_process_job_list = LIFO(job_list)
                    
                elif DISPATCHING_RULE["SPT"]:
                    next_process_job_list = SPT(job_list)
                    
                elif DISPATCHING_RULE["LPT"]:
                    next_process_job_list = LPT(job_list)
                    
                elif DISPATCHING_RULE["EDD"]:
                    next_process_job_list = EDD(job_list)
                else:
                    next_process_job_list = job_list  # 기본값 또는 다른 방법을 사용할 경우
                
                next_process_job_list = job_list
                for job_item in next_process_job_list:
                    # 비동기로 job_store에 넣는다.
                    self.job_store.put(job_item)
                job_list.clear()
                '''
            
            # 다음 Job 생성 간격 (지수 분포 사용)
            interval = 5
            yield self.env.timeout(interval)

# Printer 클래스: 프린터의 작업 처리
class Printer:
    def __init__(self, env, printing_cost, daily_events, printer_id, washing_machine, order_store):
        self.env = env
        self.daily_events = daily_events
        self.printer_id = printer_id
        self.is_busy = False
        self.washing_machine = washing_machine
        self.unit_printing_cost = printing_cost
        self.order_store = order_store  # 주문을 받는 store

    def process_orders(self):
        while True:
            # order_store에서 하나의 주문(Order) 객체를 받음
            order = yield self.order_store.get()
            '''
            self.daily_events.append(
                f"{int(self.env.now % 24)}:{int((self.env.now % 1)*60):02d} - Order {order.order_id} is received on Printer {self.printer_id}."
            )
            '''
            # 주문을 순차적으로 처리하도록 SimPy 프로세스로 감싸기
            yield self.env.process(self.process_order(order))

    def process_order(self, order):
        """
        한 주문(Order)을 처리하는 프로세스.
        주문 내 모든 Job의 build_time 합산값(order_build_time)만큼 대기하며 인쇄 작업을 모사.
        """
        self.is_busy = True  # 주문 처리 시작
        
        # set up 단계
        set_up_start = self.env.now
        self.daily_events.append(
            f"{int(self.env.now % 24)}:{int((self.env.now % 1)*60):02d} - Order {order.order_id} is printing on Printer {self.printer_id} (Set up)."
        )
        yield self.env.timeout(1)
        set_up_end = self.env.now

        # build 단계
        start_time = self.env.now
        self.daily_events.append(
            f"{int(self.env.now % 24)}:{int((self.env.now % 1)*60):02d} - Order {order.order_id} is printed on Printer {self.printer_id} (Print)."
        )
        yield self.env.timeout(order.order_build_time)
        end_time = self.env.now

        # closing 단계
        closing_start = self.env.now
        self.daily_events.append(
            f"{int(self.env.now % 24)}:{int((self.env.now % 1)*60):02d} - Order {order.order_id} is closing for {PRINTERS_SIZE['CLOSING']} min on Printer {self.printer_id} (Closing)."
        )
        yield self.env.timeout(1)
        closing_end = self.env.now
        
        # 비용 계산 (필요시)
        if PRINT_SIM_COST:
            Cost.cal_cost(order, "Printing cost")
        '''
        self.daily_events.append(
            f"{int(self.env.now % 24)}:{int((self.env.now % 1)*60):02d} - Order {order.order_id} finished printing on Printer {self.printer_id}."
        )
        '''
        DAILY_REPORTS.append({
            'order_id': order.order_id,
            'printer_id': self.printer_id,
            'set_up_start': set_up_start,
            'set_up_end': set_up_end,
            'start_time': start_time,
            'end_time': end_time,
            'closing_start': closing_start,
            'closing_end': closing_end,
            'process': 'Printing'
        })

        # 인쇄가 완료된 주문은 Washing 단계의 공통 대기열에 할당
        self.washing_machine.assign_order(order)

        self.is_busy = False  # 주문 처리가 끝나면 busy 상태 해제

# Washing Process 클래스: 세척 작업을 관리
class Washing:
    def __init__(self, env, washing_cost, daily_events, dry_machine):
        self.env = env                        # SimPy 환경 객체
        self.daily_events = daily_events      # 일별 이벤트 로그
        self.unit_washing_cost = washing_cost # 워싱 비용 단위
        self.dry_machine = dry_machine        # Drying 객체 참조
        
        # 각 워싱 머신의 용량(WASHING_SIZE)을 저장한 딕셔너리
        self.machines_capa = {
            machine_id: WASHING_MACHINE[machine_id]["WASHING_SIZE"]
            for machine_id in WASHING_MACHINE.keys()
        }
        # 사용 가능한 워싱 머신의 ID를 관리 (초기에는 모두 가용)
        self.available_machines = list(WASHING_MACHINE.keys())
        # 모든 주문을 담는 공통 대기열
        self.common_queue = []

    def assign_order(self, order):
        """
        공통 대기열에 주문(order)을 추가하고,
        가용 머신에서 해당 대기열의 주문 수가 머신의 용량만큼 쌓였다면 처리 시작.
        """
        self.common_queue.append(order)
        self.daily_events.append(
            f"{int(self.env.now % 24)}:{int((self.env.now % 1) * 60):02d} - Order {order.order_id} added to common Washing Queue. (Queue length: {len(self.common_queue)})"
        )
        self.try_process_orders()

    def try_process_orders(self):
        """
        가용 머신들에 대해, 공통 대기열의 주문 수가 해당 머신의 용량 이상이면
        배치 처리 프로세스를 시작.
        """
        # available_machines를 복사하여 순회 (처리 도중 available_machines가 바뀔 수 있으므로)
        for machine_id in list(self.available_machines):
            capa = self.machines_capa[machine_id]
            if len(self.common_queue) >= capa:
                # 공통 대기열에서 해당 머신 용량만큼의 주문을 꺼냄 (배치)
                orders_batch = [self.common_queue.pop(0) for _ in range(capa)]
                self.daily_events.append(
                    f"{int(self.env.now % 24)}:{int((self.env.now % 1) * 60):02d} - Preparing batch { [o.order_id for o in orders_batch] } for Washing Machine {machine_id}."
                )
                # 해당 머신을 사용 중으로 표시
                self.available_machines.remove(machine_id)
                # 배치 처리 프로세스 시작
                self.env.process(self._washing_job(machine_id, orders_batch))

    def _washing_job(self, machine_id, orders_batch):
        """
        지정된 machine_id의 워싱 머신에서 orders_batch에 포함된 주문들을 배치로 처리.
        """
        self.daily_events.append(
            f"{int(self.env.now % 24)}:{int((self.env.now % 1) * 60):02d} - Washing Machine {machine_id} starts processing orders { [o.order_id for o in orders_batch] }."
        )
        # 워싱 시간 (예: 분 단위의 난수 생성 후 시간 단위로 변환)
        washing_time = 1
        
        yield self.env.timeout(washing_time)
        self.daily_events.append(
            f"{int(self.env.now % 24)}:{int((self.env.now % 1) * 60):02d} - Washing Machine {machine_id} finished processing orders { [o.order_id for o in orders_batch] }."
        )
        
        # 워싱 완료 후 각 주문을 건조 단계로 전달
        for order in orders_batch:
            self.dry_machine.env.process(self.dry_machine._drying_job(order))

        
        # 배치 처리가 끝난 머신을 다시 가용 상태로 복귀시킴
        self.available_machines.append(machine_id)
        # 혹시 대기열에 남은 주문이 있다면 추가 처리 시도
        self.try_process_orders()


# Drying Process 클래스: 건조 작업을 관리
class Drying:
    def __init__(self, env, drying_cost, daily_events, post_processor):
        self.env = env                                # SimPy 환경 객체
        self.daily_events = daily_events              # 일별 이벤트 로그
        self.unit_drying_cost = drying_cost           # 건조 비용 단위
        self.post_processor = post_processor          # 후처리(PostProcessing) 객체 참조
        # 각 건조기를 simpy.Resource로 생성 (동시에 처리 가능한 주문 수는 DRY_MACHINE의 DRYING_SIZE 사용)
        self.machines = {
            machine_id: simpy.Resource(env, capacity=DRY_MACHINE[machine_id]["DRYING_SIZE"])
            for machine_id in DRY_MACHINE.keys()
        }
    
    def _drying_job(self, order):
        """
        개별 주문에 대해 여러 건조기(Resource) 중 사용 가능한 하나를 기다린 후, 해당 건조기에서 건조 작업을 수행.
        """
        # 모든 건조기에 대해 동시에 자원 요청(request) 생성
        requests = {
            machine_id: machine.request()
            for machine_id, machine in self.machines.items()
        }
        
        # 여러 요청 중 하나라도 할당될 때까지 대기 (AnyOf를 사용)
        result = yield simpy.AnyOf(self.env, requests.values())
        
        # 할당된 건조기(Resource)를 확인하고, 나머지 요청은 취소
        granted_machine_id = None
        for machine_id, req in requests.items():
            if req in result.events:
                granted_machine_id = machine_id
            else:
                req.cancel()
        
        if granted_machine_id is None:
            # 이 경우는 발생하지 않아야 합니다.
            self.daily_events.append(
                f"{int(self.env.now % 24)}:{int((self.env.now % 1) * 60):02d} - Order {order.order_id} did not get a Drying Machine!"
            )
            return
        
        self.daily_events.append(
            f"{int(self.env.now % 24)}:{int((self.env.now % 1) * 60):02d} - Order {order.order_id} is being dried on Drying Machine {granted_machine_id}."
        )
        
        # 건조 시간 (예시로 10분 ~ 15분 사이의 난수; 필요에 따라 config에서 범위를 가져오도록 수정)
        drying_time = 1
        yield self.env.timeout(drying_time)  # 분 단위를 시간 단위로 변환하여 대기
        
        self.daily_events.append(
            f"{int(self.env.now % 24)}:{int((self.env.now % 1) * 60):02d} - Order {order.order_id} finished drying on Drying Machine {granted_machine_id}."
        )
        
        # 사용한 건조기 자원 해제
        self.machines[granted_machine_id].release(requests[granted_machine_id])
        
        # 건조 완료 후, 후처리(PostProcessing) 단계로 주문 전달
        self.post_processor.env.process(self.post_processor.process_order(order))

# PostProcessing 클래스: 후처리 작업을 관리
class PostProcessing:
    def __init__(self, env, post_processing_cost, daily_events, packaging):
        self.env = env  # SimPy 환경 객체
        self.daily_events = daily_events  # 일별 이벤트 로그 리스트
        self.unit_post_processing_cost = post_processing_cost
        self.packaging = packaging  # Packaging 객체 참조

        # 작업자 관리를 위한 SimPy Store를 생성 (초기에는 모든 작업자가 사용 가능)
        self.worker_store = simpy.Store(self.env, capacity=len(POST_PROCESSING_WORKER))
        for wid in POST_PROCESSING_WORKER.keys():
            self.worker_store.put(wid)

    def process_order(self, order):
        """
        order 안의 각 job을 순차적으로 개별 처리하고,
        모든 job의 후처리가 완료되면 order를 Packaging 단계로 전달합니다.
        """
        self.daily_events.append(
            f"{int(self.env.now % 24)}:{int((self.env.now % 1)*60):02d} - Order {order.order_id} received for PostProcessing with {len(order.jobs)} jobs."
        )
        processed_jobs = []
        # order 내의 job을 순차적으로 처리
        for job in order.jobs:
            # 각 job을 개별적으로 후처리 처리 (동시에 처리하지 않고 순서대로 진행)
            yield self.env.process(self._process_job(job))
            processed_jobs.append(job)
        # 모든 job 처리가 끝나면 order의 job 목록을 갱신
        order.jobs = processed_jobs
        self.daily_events.append(
            f"{int(self.env.now % 24)}:{int((self.env.now % 1)*60):02d} - All jobs in Order {order.order_id} finished PostProcessing. Sending order to Packaging."
        )
        # 후처리 완료된 order를 Packaging 단계로 전달
        self.packaging.assign_order(order)

    def _process_job(self, job):
        """
        개별 job에 대해 사용 가능한 작업자(worker)를 기다렸다가 후처리 작업을 수행합니다.
        """
        # 사용 가능한 작업자(worker)를 기다림 (Store에서 get)
        worker_id = yield self.worker_store.get()
        self.daily_events.append(
            f"{int(self.env.now % 24)}:{int((self.env.now % 1)*60):02d} - Job {job.job_id} starts PostProcessing on Worker {worker_id}."
        )
        # 후처리 시간 만큼 대기 (job.post_processing_time은 시간 단위)
        yield self.env.timeout(job.post_processing_time)
        self.daily_events.append(
            f"{int(self.env.now % 24)}:{int((self.env.now % 1)*60):02d} - Job {job.job_id} finished PostProcessing on Worker {worker_id}."
        )
        if PRINT_SIM_COST:
            Cost.cal_cost(job, "Post Processing cost")
        # 처리 완료 후 작업자를 다시 반납
        yield self.worker_store.put(worker_id)


# Packaging 클래스: 포장 작업을 관리
class Packaging:
    def __init__(self, env, packaging_cost, daily_events, satisfication):
        self.env = env  # SimPy 환경 객체 
        self.daily_events = daily_events  # 일별 이벤트 로그 리스트
        # 기존 방식: 작업자별 상태 플래그 및 큐
        self.workers = {worker_id: {"is_busy": False} for worker_id in PACKAGING_MACHINE.keys()}
        self.unit_packaging_cost = packaging_cost
        self.queue = []  # 대기열
        self.satisfication = satisfication

    def assign_job(self, job):
        """개별 job을 작업자에게 할당 (기존 메서드)"""
        for worker_id, worker in self.workers.items():
            if not worker["is_busy"]:
                worker["is_busy"] = True
                self.daily_events.append(
                    f"{int(self.env.now % 24)}:{int((self.env.now % 1)*60):02d} - Job {job.job_id} starts Packaging on Worker {worker_id}."
                )
                self.env.process(self.process_job(worker_id, job))
                return True
        self.queue.append(job)
        return False

    def process_job(self, worker_id, job):
        """개별 job의 Packaging 작업 처리"""
        start_time = self.env.now
        yield self.env.timeout(job.packaging_time)  # 포장 시간을 시간 단위로 변환하여 대기
        end_time = self.env.now
        self.daily_events.append(
            f"{int(end_time % 24)}:{int((end_time % 1)*60):02d} - Job {job.job_id} finished Packaging on Worker {worker_id}."
        )
        DAILY_REPORTS.append({
            'job_id': job.job_id,
            'worker_id': worker_id,
            'start_time': start_time,
            'end_time': end_time,
            'process': 'Packaging'
        })
        if PRINT_SIM_COST:
            Cost.cal_cost(job, "Packaging cost")
        if PRINT_SATISFICATION:
            self.satisfication.cal_satisfication(job, end_time)
        self.workers[worker_id]["is_busy"] = False

        # 대기열에 job이 있으면 바로 다음 작업 처리
        if self.queue:
            next_job = self.queue.pop(0)
            self.env.process(self.process_job(worker_id, next_job))

    def assign_order(self, order):
        """
        PostProcessing이 완료된 order를 받아,
        order 안의 모든 job을 Packaging 단계로 할당합니다.
        """
        self.daily_events.append(
            f"{int(self.env.now % 24)}:{int((self.env.now % 1)*60):02d} - Order {order.order_id} is sent to Packaging with {len(order.jobs)} jobs."
        )
        for job in order.jobs:
            self.assign_job(job)

# Job 클래스: Job의 속성을 정의
class Job:
    def __init__(self, env, job_id, config):
        self.env = env  # SimPy 환경 객체
        self.job_id = job_id  # Job ID
        self.create_time = env.now  # Job 생성 시간 기록   
        self.height = np.random.randint(*config["HEIGHT_RANGE"])
        self.width = np.random.randint(*config["WIDTH_RANGE"])
        self.depth = np.random.randint(*config["DEPTH_RANGE"])
        self.volume = (
                         self.height
                       * self.width
                       * self.depth
                       )# Job 볼륨
        
        # Printer class time
        self.build_time = 1
        # Post processsing, washing, air drying class time
        self.post_processing_time = 1  # 후처리 시간

        # Packaging time
        if self.volume <= (RANGE_CONTROLLA["LENGHT_RANGE"]["WIDTH"]["MAX"] * RANGE_CONTROLLA["LENGHT_RANGE"]["HEIGHT"]["MAX"] * RANGE_CONTROLLA["LENGHT_RANGE"]["DEPTH"]["MAX"])/2:
            self.packaging_time = 1  # 포장 시간

        elif ((RANGE_CONTROLLA["LENGHT_RANGE"]["WIDTH"]["MAX"] * RANGE_CONTROLLA["LENGHT_RANGE"]["HEIGHT"]["MAX"] * RANGE_CONTROLLA["LENGHT_RANGE"]["DEPTH"]["MAX"])/2 + 1 
              <= self.volume 
              <= (RANGE_CONTROLLA["LENGHT_RANGE"]["WIDTH"]["MAX"] * RANGE_CONTROLLA["LENGHT_RANGE"]["HEIGHT"]["MAX"] * RANGE_CONTROLLA["LENGHT_RANGE"]["DEPTH"]["MAX"])):
            self.packaging_time = 1  # 포장 시간
        
        # Job Due Date    
        self.due_date = self.create_time + self.build_time + self.post_processing_time + self.packaging_time

        # 추가: 비용 항목들 초기화
        self.printing_cost = 0
        self.post_processing_cost = 0
        self.packaging_cost = 0
        self.delivery_cost = 0
        self.shortage_cost = 0
        self.shortage = 0  # 부족 수량 (Shortage Cost 계산용)


class Cost:
    # Class for managing costs in the simulation
    def cal_cost(instance, cost_type):
        """
        Calculate and log different types of costs.
        """

        if cost_type == "Holding cost":
            # Calculate holding cost
            DAILY_COST_REPORT[cost_type] += instance.unit_holding_cost * instance.on_hand_inventory * (
                instance.env.now - instance.holding_cost_last_updated)
        elif cost_type == "Printing cost":
            # Calculate processing cost
            DAILY_COST_REPORT[cost_type] += instance.order_build_time * COST_TYPES[0]['PRINTING_COST']  # Example formula
        elif cost_type == "Post Processing cost":
            # Calculate delivery cost
            DAILY_COST_REPORT[cost_type] += instance.post_processing_time * COST_TYPES[0]['POSTPROCESSING_COST']  # Example formula
        elif cost_type == "Delivery cost":
            # Calculate order cost
            DAILY_COST_REPORT[cost_type] += 1  # $1 for delivery cost
        elif cost_type == "Packaging cost":
            # Calculate order cost
            if instance.volume >= 25:
                DAILY_COST_REPORT[cost_type] += 2 * COST_TYPES[0]['PACKAGING_COST'] # $2 for packaging if volume >= 25
            else:
                DAILY_COST_REPORT[cost_type] += 1 * COST_TYPES[0]['PACKAGING_COST'] # $1 for packaging if volume < 25
        elif cost_type == "Shortage cost":
            # Calculate shortage cost
            DAILY_COST_REPORT[cost_type] += instance.shortage * COST_TYPES[0]['SHORTAGE_COST']  # Example: $1 per shortage


    def update_cost_log():
        """
        Update the cost log at the end of each day.
        """
        COST_LOG.append(0)
        # Update daily total cost
        for key in DAILY_COST_REPORT.keys():
            COST_LOG[-1] += DAILY_COST_REPORT[key]

        return COST_LOG[-1]

    def clear_cost():
        """
        Clear the daily cost report.
        """
        # Clear daily report
        for key in DAILY_COST_REPORT.keys():
            DAILY_COST_REPORT[key] = 0

class Satisfication:
    def __init__(self, env, daily_events):
        self.env = env
        self.daily_events = daily_events
        self.total_satisfication = 0

    def cal_satisfication(self, job, end_time):
        
        """고객 만족도 계산 및 기록"""
        if job.create_time is not None and end_time is not None and (job.create_time != end_time):
            satisfication = SATISFICATION_TYPE["POSITIVE"] / (end_time - job.create_time)
            self.total_satisfication += satisfication
            self.daily_events.append(
                f"Job {job.job_id}: Satisfication calculated as {satisfication:.4f}\nTotal Satisfication: {self.total_satisfication: .4f}"
            )
        
        elif job.create_time == end_time:
            satisfication = SATISFICATION_TYPE["NEGATIVE"]
            self.total_satisfication += satisfication
            self.daily_events.append(
                f"Job {job.job_id}: No printer assigned, satisfication set to {satisfication:.4f}\nTotal Satisfication: {self.total_satisfication: .4f}"
            )

        SATISFICATION_LOG.append(self.total_satisfication)

# 환경 생성 함수 (create_env)
def create_env(daily_events):
    simpy_env = simpy.Environment()

    # 주문(order)을 위한 store (배치 단위로 들어갈 예정)
    order_store = simpy.Store(simpy_env)
    
    # Satisfication, Packaging, PostProcessing, Drying, Washing, Customer, Display 생성
    satisfication = Satisfication(simpy_env, daily_events)
    packaging = Packaging(simpy_env, COST_TYPES[0]['PACKAGING_COST'], daily_events, satisfication)
    post_processor = PostProcessing(simpy_env, COST_TYPES[0]['POSTPROCESSING_COST'], daily_events, packaging)
    dry_machine = Drying(simpy_env, COST_TYPES[0]['DRYING_COST'], daily_events, post_processor)
    washing_machine = Washing(simpy_env, COST_TYPES[0]['WASHING_COST'], daily_events, dry_machine)
    customer = Customer(simpy_env, COST_TYPES[0]['SHORTAGE_COST'], daily_events, satisfication, order_store)
    display = Display(simpy_env, daily_events)
    
    # Printer 생성 시 order_store와 washing_machine (즉, Washing.assign_order 호출) 전달
    printers = [
        Printer(simpy_env, COST_TYPES[0]['PRINTING_COST'], daily_events, pid, washing_machine, order_store)
        for pid in PRINTERS.keys()
    ]

    return simpy_env, packaging, dry_machine, washing_machine, post_processor, customer, display, printers, daily_events, satisfication


# SimPy 이벤트 프로세스를 설정하는 함수 (simpy_event_processes)
def simpy_event_processes(simpy_env, packaging, post_processor, customer, display, printers, daily_events):
    """
    시뮬레이션의 주요 프로세스를 스케줄링합니다.
    
    - display.track_days(): 매일의 보고서를 기록합니다.
    - customer.create_orders_continuously(): 지속적으로 주문(Order)을 생성합니다.
    - 각 Printer의 process_orders(): order_store에 들어온 주문을 인쇄(Printing) 처리합니다.
    
    Drying 단계에서 PostProcessing, 그리고 PostProcessing에서 Packaging으로 order가 자동 전달됩니다.
    """
    # 날짜 추적 프로세스 실행 (매일 보고서 기록)
    simpy_env.process(display.track_days())
    
    # Customer가 지속적으로 주문을 생성하는 프로세스 실행
    simpy_env.process(customer.create_orders_continuously())

    # 각 Printer의 주문 처리 프로세스 실행
    for printer in printers:
        simpy_env.process(printer.process_orders())