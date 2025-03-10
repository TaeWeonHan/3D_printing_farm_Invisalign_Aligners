import simpy
import numpy as np
from config_Simpy import *  # 설정 파일 (JOB_TYPES, PRINTERS, PRINTERS_INVEN 등)
from log_simpy import *  # 로그 파일 (DAILY_EVENTS 등)
from dispatching_method import *
import time
# Display 클래스: 시뮬레이션 시간(일 단위)을 추적하고 일별 보고서를 기록
# Display 클래스: 시뮬레이션 시간(일 단위)을 추적하고 일별 보고서를 기록
class Display:
    """
    Display 클래스
    ----------------
    시뮬레이션 시간(일 단위)을 추적하고, 매일 발생하는 이벤트와 보고서를 daily_events 리스트에 기록하는 역할
    """
    def __init__(self, env, daily_events):
        """
        __init__ 메서드 (생성자)
        -------------------------
        self.env: SimPy 환경 객체로, 시뮬레이션 시간과 이벤트 스케줄링을 관리
        self.daily_events: 일별 이벤트 로그를 저장하는 리스트로, 각 일(day)마다 발생한 이벤트를 기록
        
        매개변수:
            env: SimPy 환경 객체
            daily_events: 일별 이벤트 로그 리스트
        """
        self.env = env
        self.daily_events = daily_events

    def track_days(self):
        """
        track_days 메서드
        --------------------
        현재 시뮬레이션 시간을 일(day) 단위로 계산하여, 매 24시간(1일)마다 일별 보고서 제목을 daily_events에 기록
        
        동작:
            - 현재 시간을 24로 나누어 일(day)을 계산
            - 계산된 day를 이용해 보고서 제목 문자열을 daily_events 리스트에 추가
            - 24시간 후에 다시 실행되도록 대기(timeout)
        """
        while True:
            day = int(self.env.now // 24) + 1  # 현재 시뮬레이션 시간을 일 단위로 계산
            self.daily_events.append(f"\n===== Day {day} Report: =====")  # 일별 보고서 제목 추가
            yield self.env.timeout(24)  # 24시간(1일)마다 실행


# Job 클래스: 전문 job(작업)의 속성을 정의
class Job:
    """
    Job 클래스
    ----------------
    전문 job(작업)의 속성을 정의하는 클래스
    각 Job은 여러 Item(구 job)을 포함할 수 있으며, 생성 시점, 제작 시간(job_build_time), 그리고 워싱 시간(pallet_washing_time) 등을 설정
    """
    def __init__(self, job_id, items, create_time):
        """
        __init__ 메서드 (생성자)
        -------------------------
        self.job_id: Job의 고유 식별자(ID)입니다.
        self.items: 이 Job에 포함될 Item(구 Job)들의 리스트로, 초기에는 빈 리스트로 시작
        self.create_time: Job이 생성된 시점을 기록합니다.
        self.job_build_time: Job의 인쇄(제작) 시간으로, 현재 고정값 1로 설정
        self.pallet_washing_time: Job의 세척(워싱) 시간으로, JOB_TYPES["DEFAULT"]["WASHING_RANGE"] 내의 무작위 정수로 결정
        
        매개변수:
            job_id: 생성될 Job의 ID
            items: Job에 포함될 Item 리스트 (초기에는 빈 리스트)
            create_time: Job이 생성된 시각 (SimPy 시간)
        """
        self.job_id = job_id
        self.items = items  # 전문 job에 포함된 Item(구 Job) 리스트 (초기에는 빈 리스트)
        self.create_time = create_time  # 전문 job 생성 시점
        self.build_time = None       
        self.washing_time = None     
        self.drying_time = None      
        self.packaging_time = None 


# Customer 클래스: 지속적으로 전문 job(작업)을 생성
class Customer:
    """
    Customer 클래스
    ----------------
    지속적으로 전문 job(작업)을 생성하는 역할을 담당
    고객은 정해진 간격으로 Job을 생성하고, 각 Job에 대해 여러 Item을 추가하며,
    조건에 따라 생성된 Job들을 임시 리스트에 저장 후 일정 수가 쌓이면 printer_store에 전달
    """
    def __init__(self, env, shortage_cost, daily_events, satisfication, printer_store):
        """
        __init__ 메서드 (생성자)
        -------------------------
        self.env: SimPy 환경 객체로, 시뮬레이션의 시간 흐름을 관리합니다.
        self.daily_events: 일별 이벤트 로그 리스트로, Job 생성 및 처리 관련 이벤트를 기록
        self.current_item_id: 새 Item(구 Job)의 고유 ID를 생성하기 위한 카운터 (초기값 0)
        self.current_job_id: 새 전문 job(구 Order)의 고유 ID를 생성하기 위한 카운터 (초기값 0)
        self.unit_shortage_cost: Item 할당 실패 시 발생하는 부족 비용 단위
        self.satisfication: 고객 만족도 계산을 위한 객체
        self.printer_store: 생성된 Job들을 저장할 SimPy Store 객체
        self.temp_job_list: 생성된 Job들을 임시로 저장하는 리스트로, 일정 개수가 누적되면 printer_store에 전달
        
        매개변수:
            env: SimPy 환경 객체
            shortage_cost: 부족 비용 단위
            daily_events: 일별 이벤트 로그 리스트
            satisfication: 고객 만족도 계산 객체
            printer_store: Job들을 저장할 SimPy Store 객체
        """
        self.env = env
        self.daily_events = daily_events
        self.current_item_id = 0   # 새 Item(구 Job) ID 생성에 사용
        self.current_job_id = 0    # 새 전문 job(구 Order) ID 생성에 사용
        self.unit_shortage_cost = shortage_cost
        self.satisfication = satisfication
        self.printer_store = printer_store
        self.temp_job_list = []  # 누적된 전문 job들을 임시로 저장

    def create_jobs_continuously(self):
        """
        create_jobs_continuously 메서드
        -----------------------------------
        시뮬레이션 기간(SIM_TIME * 24 시간) 동안 지속적으로 Job(작업)을 생성하는 프로세스
        
        동작:
            - 현재 시뮬레이션 시간이 종료시간에 도달할 때까지 무한 루프를 수행
            - 각 Job 생성 시, 현재 시간을 기반으로 일(day)을 계산하고, Job 생성 이벤트를 daily_events에 기록
            - 각 Job 내부에 CUSTOMER["ITEM_SIZE"] 만큼의 Item을 생성하고, 각 Item에 대해 사이즈 조건을 확인하여 적절히 할당하거나 부족 상황을 기록
            - 생성된 Job은 임시 리스트(temp_job_list)에 저장되며, 리스트 크기가 CUSTOMER["JOB_LIST_SIZE"]에 도달하면 printer_store에 일괄 전달한 후 리스트를 초기화
            - 각 Job 생성 후 일정 간격(interval, 여기서는 5시간) 동안 대기
        """
        while True:
            if self.env.now >= SIM_TIME * 24:
                break

            day = int(self.env.now // 24) + 1

            # 고객이 전문 job 객체 생성 (빈 Item 리스트와 함께)
            new_job = Job(self.current_job_id, [], self.env.now)
            self.current_job_id += 1
            self.daily_events.append(
                f"{int(self.env.now % 24)}:{int((self.env.now % 1)*60):02d} - Job {new_job.job_id} created at time {new_job.create_time:.2f}."
            )

            # 전문 job 내부에서 CUSTOMER["ITEM_SIZE"]만큼 Item 생성 후 추가
            for _ in range(CUSTOMER["ITEM_SIZE"]):
                item = Item(self.env, self.current_item_id, JOB_TYPES["DEFAULT"], job_id=new_job.job_id)
                self.current_item_id += 1

                # JOB_LOG (이제 ITEM_LOG) 기록: 부모 전문 job의 ID와 생성된 Item의 ID 기록
                ITEM_LOG.append({
                    'day': day,
                    'job_id': new_job.job_id,   # 전문 job의 ID
                    'item_id': item.item_id,      # 생성된 Item의 ID
                    'width': item.width,
                    'height': item.height,
                    'depth': item.depth,
                    'create_time': item.create_time,
                    'volume': item.volume,
                    'build_time': item.build_time,
                    'post_processing_time': item.post_processing_time,
                    'packaging_time': item.packaging_time
                })

                # 생성된 Item이 프린터 크기 조건에 부합하면 Job에 추가, 아니면 부족 처리
                if (item.width <= PRINTERS_SIZE["WIDTH"] and
                    item.height <= PRINTERS_SIZE["HEIGHT"] and
                    item.depth <= PRINTERS_SIZE["DEPTH"]):
                    new_job.items.append(item)
                
                else:
                    self.daily_events.append(f"Item {item.item_id} could not be assigned: No suitable printer available (Item size: {item.volume:.2f})")
                    item.shortage = 1
                    if PRINT_SIM_COST:
                        Cost.cal_cost(item, "Shortage cost")
                    if PRINT_SATISFICATION:
                        self.satisfication.cal_satisfication(item, self.env.now)
            
            # 생성된 전문 job을 임시 리스트에 추가
            self.temp_job_list.append(new_job)

            # 일정 수의 전문 job이 쌓이면 printer_store에 넣음
            if len(self.temp_job_list) >= CUSTOMER["JOB_LIST_SIZE"]:
                self.daily_events.append(
                    f"{int(self.env.now % 24)}:{int((self.env.now % 1)*60):02d} - {len(self.temp_job_list)} jobs accumulated. Sending batch to printer."
                )
                for job_obj in self.temp_job_list:
                    self.printer_store.put(job_obj)
                self.temp_job_list.clear()

            interval = 5
            yield self.env.timeout(interval)

# Printer 클래스: 프린터의 작업 처리
class Proc_Printer:
    """
    프린터 작업 처리 클래스
    전문 job을 받아서 세 단계(자원 할당/세팅 → 인쇄 → 마무리)로 처리한 후,
    워싱 머신으로 전달하는 역할.
    """
    def __init__(self, env, printing_cost, daily_events, printer_id, washing_machine, printer_store, washing_store):
        """
        생성자 (__init__)
        env: SimPy 환경 객체 (시뮬레이션 시간 및 이벤트 관리)
        daily_events: 일별 이벤트 로그 리스트 (이벤트 기록용)
        printer_id: 프린터의 고유 식별자
        washing_machine: 인쇄 완료 후 job을 전달할 워싱 머신 객체
        unit_printing_cost: 인쇄 비용 단위
        printer_store: printer클래스에서 job을 받는 SimPy Store 객체
        washing_store: washing클래스에서 job을 받는 SimPy Store 객체체
        """
        self.env = env                          # SimPy 환경, 시간 관리
        self.daily_events = daily_events        # 이벤트 로그 저장 리스트
        self.printer_id = printer_id            # 프린터 식별자
        self.is_busy = False                    # 프린터 사용 상태 (초기: 미사용)
        self.washing_machine = washing_machine  # 워싱 머신 객체 (인쇄 후 job 전달용)
        self.unit_printing_cost = printing_cost # 인쇄 비용 단위
        self.printer_store = printer_store      # printer job 저장 store
        self.washing_store = washing_store      # washing job 저장 store


    def seize(self):
        """
        seize 메서드
        printer_store에서 전문 job을 받아서 delay 프로세스를 실행.
        """
        while True:
            job = yield self.printer_store.get()
            # 각 item의 build_time 합산하여 job.job_build_time으로 설정 (None이면 기본값 1 사용)
            
            total_build_time = 0
            for item in job.items:
                # 만약 item의 build_time이 None이 아니라면 해당 값을 사용합니다.
                if item.build_time is not None:
                    total_build_time += item.build_time
                # build_time이 None이라면 기본값인 1을 더합니다.
                else:
                    item.build_time = 1
                    total_build_time += item.build_time

            # 계산된 총 build_time을 job의 속성으로 할당합니다.
            job.job_build_time = total_build_time
                        
            yield self.env.process(self.delay(job))

    def delay(self, job):
        """
        한 주문(Job)을 처리하는 프로세스.
        주문 내 모든 Job의 build_time 합산값(order_build_time)만큼 대기하며 인쇄 작업을 모사.
        """
        self.is_busy = True  # 주문 처리 시작
        
        # Set-up 단계
        set_up_start = self.env.now
        self.daily_events.append(
            f"{int(self.env.now % 24)}:{int((self.env.now % 1) * 60):02d} - Job {job.job_id} is starting setup on Printer {self.printer_id}."
        )
        yield self.env.timeout(1)
        set_up_end = self.env.now
        
        # Build 단계 (계산된 build_time 만큼 대기)
        start_time = self.env.now
        self.daily_events.append(
            f"{int(self.env.now % 24)}:{int((self.env.now % 1) * 60):02d} - Job {job.job_id} is printing on Printer {self.printer_id} for {job.job_build_time} time units."
        )
        yield self.env.timeout(job.job_build_time)
        end_time = self.env.now
        
        # Closing 단계
        closing_start = self.env.now
        self.daily_events.append(
            f"{int(self.env.now % 24)}:{int((self.env.now % 1) * 60):02d} - Job {job.job_id} is closing on Printer {self.printer_id}."
        )
        yield self.env.timeout(1)
        closing_end = self.env.now

        if PRINT_SIM_COST:
            Cost.cal_cost(job, "Printing cost")

        DAILY_REPORTS.append({
            'order_id': job.job_id,  # job_id로 표기
            'printer_id': self.printer_id,
            'set_up_start': set_up_start,
            'set_up_end': set_up_end,
            'start_time': start_time,
            'end_time': end_time,
            'closing_start': closing_start,
            'closing_end': closing_end,
            'process': 'Printing'
        })

        # release 메서드를 호출하여 프린터 상태 해제 및 Washing 단계로 전달
        self.release(job)
        
    def release(self, job):
        """
        machine을 해제하고 washing_machine으로 job을 넘기는 작업.
        """
        self.is_busy = False
        self.daily_events.append(
            f"{int(self.env.now % 24)}:{int((self.env.now % 1)*60):02d} - Printer {self.printer_id} is now available."
        )
        self.washing_store.put(job)

class Proc_Washing:
    """
    워싱(세척) 작업 처리 클래스
    - washing_store에 넣은 job들을 seize 프로세스에서 각 워싱 머신의 capacity(용량)만큼 꺼내어 배치(batch)를 구성.
    - 배치가 완성되면 delay 프로세스를 통해 한 번에 세척 작업을 진행하고, 세척 완료 후 Drying 단계로 job들을 전달.
    """
    def __init__(self, env, washing_cost, daily_events, dry_machine, washing_store, drying_store):
        """
        생성자 (__init__)
        :env: SimPy 환경 객체로, 시뮬레이션의 시간 흐름과 이벤트 스케줄링을 관리합니다.
        :washing_cost: 세척 비용 단위로, 비용 계산에 사용됩니다.
        :daily_events: 일별 이벤트 로그 리스트로, 작업 진행 상황을 기록하는 데 사용됩니다.
        :dry_machine: 세척 후 job들을 전달할 건조(Drying) 단계 객체입니다.
        :washing_store: Printer나 다른 프로세스에서 전달된 job들이 임시로 저장되는 Store로, 세척 작업을 위한 입력 버퍼 역할을 합니다.
        :drying_store: 건조 단계에서 사용될 Store 객체로, 세척 후 job을 전달하기 위한 별도의 저장 공간(여기서는 필요에 따라 사용 가능)
        
        내부적으로 __init__에서는 다음을 수행합니다.
          - 전달받은 SimPy 환경, 비용, 로그, 건조 단계 객체, 그리고 washing_store와 drying_store를 멤버 변수에 저장.
          - WASHING_MACHINE 전역 설정(예: { 0: {"WASHING_SIZE": 2}, 1: {"WASHING_SIZE": 2} })을 참조하여,
            각 워싱 머신의 용량(capacity), 현재 배치(batch: 아직 처리되지 않은 job들의 리스트), busy 여부(is_busy)를 관리하는 딕셔너리(self.machines)를 생성.
          - 모든 워싱 머신이 즉시 job 할당을 받지 못할 경우를 대비하여, 대기열(waiting_queue)을 초기화합니다.
        """
        self.env = env                                # SimPy 환경, 시간 관리
        self.daily_events = daily_events              # 이벤트 로그 리스트
        self.unit_washing_cost = washing_cost         # 세척 비용 단위
        self.dry_machine = dry_machine                # 건조 단계 객체
        self.washing_store = washing_store            # job을 저장하는 washing Store
        self.drying_store = drying_store              # job을 저장하는 drying Store
        # 각 워싱 머신의 용량 정보를 WASHING_MACHINE 설정에서 추출
        # 예를 들어, WASHING_MACHINE = { 0: {"WASHING_SIZE": 2}, 1: {"WASHING_SIZE": 2} }
        self.machines = {
            machine_id: {
                "capacity": WASHING_MACHINE[machine_id]["WASHING_SIZE"],
                "batch": [],           # 해당 머신에 할당된 job들의 리스트
                "is_busy": False       # 현재 머신이 작업 중인지 여부
            }
            for machine_id in WASHING_MACHINE.keys()
        }
        
        # 모든 머신이 busy일 경우를 위한 대기열
        self.waiting_queue = []

    def seize(self):
        """
        seize 메서드:
        - washing_store에서 job을 가져와, 사용 가능한(즉, busy가 아니고 배치가 capacity 미만인) 머신에 즉시 할당합니다.
        - 만약 할당할 수 있는 머신이 없다면 waiting_queue에 추가합니다.
        """
        while True:
            job = yield self.washing_store.get()
            assigned = False

            for machine_id, machine in self.machines.items():
                if not machine["is_busy"] and len(machine["batch"]) < machine["capacity"]:
                    machine["batch"].append(job)
                    self.daily_events.append(
                        f"{int(self.env.now % 24)}:{int((self.env.now % 1)*60):02d} - Job {job.job_id} assigned to Washing Machine {machine_id}. Batch: {[j.job_id for j in machine['batch']]}"
                    )
                    assigned = True
                    # 배치가 머신의 capacity에 도달하면 바로 배치 처리를 시작합니다.
                    if len(machine["batch"]) == machine["capacity"]:
                        machine["is_busy"] = True
                        current_batch = machine["batch"]
                        machine["batch"] = []  # 배치 초기화
                        self.env.process(self.delay(machine_id, current_batch))
                    break

            if not assigned:
                self.waiting_queue.append(job)
                self.daily_events.append(
                    f"{int(self.env.now % 24)}:{int((self.env.now % 1)*60):02d} - All Washing Machines busy/full. Job {job.job_id} added to waiting queue."
                )

    def delay(self, machine_id, jobs_batch):
        """
        delay 메서드:
        - 지정된 워싱 머신(machine_id)에서 모인 jobs_batch를 한 번에 처리합니다.
        - 각 job의 washing_time이 없으면 기본값 1을 사용하며, 배치 내 최대 washing_time을 처리 시간으로 결정합니다.
        - 세척 완료 후 각 job을 건조 단계로 전달한 후, release()를 호출하여 해당 머신을 free 상태로 전환하고 waiting_queue의 job들을 재할당합니다.
        """
        # 각 job에 washing_time이 없으면 기본값 1 할당
        for job in jobs_batch:
            if not hasattr(job, "washing_time") or job.washing_time is None:
                job.washing_time = 1
        washing_time = sum(job.washing_time for job in jobs_batch)
        self.daily_events.append(
            f"{int(self.env.now % 24)}:{int((self.env.now % 1)*60):02d} - Washing Machine {machine_id} starts processing batch {[job.job_id for job in jobs_batch]} for {washing_time} time units."
        )
        yield self.env.timeout(washing_time)
        self.daily_events.append(
            f"{int(self.env.now % 24)}:{int((self.env.now % 1)*60):02d} - Washing Machine {machine_id} finished processing batch."
        )

        # 처리 완료 후 release()를 호출하여 waiting_queue의 job 재할당 등 후처리 실행
        self.release(machine_id, jobs_batch)

    def release(self, machine_id, jobs_batch):
        """
        release 메서드:
        - 지정된 워싱 머신(machine_id)을 free 상태로 전환합니다다.
        - 세척 완료된 jobs_batch의 각 job을 건조(Drying) 단계로 전달합니다.
        - 이후, 머신이 free인 경우 waiting_queue에 있는 job들을 해당 머신의 배치에 재할당합니다.
        - 만약 재할당 후 배치가 capacity에 도달하면, 새로운 delay() 프로세스를 실행하여 해당 배치를 처리합니다.
        """
        # 해당 머신을 free 상태로 전환
        self.machines[machine_id]["is_busy"] = False
        
        # 세척 완료된 job들을 건조 단계로 전달
        for job in jobs_batch:
            self.drying_store.put(job)
        
        # 머신이 free이고 배치에 여유가 있을 때, waiting_queue에서 job을 가져와 배치에 추가
        while self.waiting_queue and (not self.machines[machine_id]["is_busy"]) and (len(self.machines[machine_id]["batch"]) < self.machines[machine_id]["capacity"]):
            waiting_job = self.waiting_queue.pop(0)
            self.machines[machine_id]["batch"].append(waiting_job)
            self.daily_events.append(
                f"{int(self.env.now % 24)}:{int((self.env.now % 1)*60):02d} - After processing, waiting Job {waiting_job.job_id} assigned to Washing Machine {machine_id}. Batch: {[j.job_id for j in self.machines[machine_id]['batch']]}"
            )
        # 만약 재할당한 배치가 capacity에 도달하고 머신이 free 상태라면 delay()를 실행하여 배치 처리
        if (not self.machines[machine_id]["is_busy"]) and (len(self.machines[machine_id]["batch"]) == self.machines[machine_id]["capacity"]):
            self.machines[machine_id]["is_busy"] = True
            current_batch = self.machines[machine_id]["batch"]
            self.machines[machine_id]["batch"] = []
            self.env.process(self.delay(machine_id, current_batch))


# Drying Process 클래스: 건조 작업을 관리
class Proc_Drying:
    """
    건조(Drying) 작업 처리 클래스
    - drying_store에 넣은 job들을 seize() 메서드에서 각 건조 머신의 capacity(용량)만큼 꺼내어 배치(batch)를 구성합니다.
    - 배치가 완성되면 delay() 메서드를 통해 한 번에 건조 작업을 진행하고,
      건조 완료 후 release()를 통해 각 job을 후속 단계(PostProcessing)로 전달하며, waiting_queue의 job들을 재할당합니다.
    """
    def __init__(self, env, drying_cost, daily_events, post_processor, drying_store):
        """
        생성자 (__init__)
        :env: SimPy 환경 객체로, 시뮬레이션의 시간 흐름과 이벤트 스케줄링을 관리합니다.
        :drying_cost: 건조 비용 단위로, 비용 계산에 사용됩니다.
        :daily_events: 일별 이벤트 로그 리스트로, 작업 진행 상황을 기록하는 데 사용됩니다.
        :post_processor: 건조 작업 완료 후 job들을 전달할 후처리(PostProcessing) 단계 객체입니다.
        :drying_store: Printer나 다른 프로세스에서 전달된 job들이 임시로 저장되는 Store로, 건조 작업을 위한 입력 버퍼 역할을 합니다.
        
        내부적으로 __init__에서는 다음을 수행합니다.
          - 전달받은 SimPy 환경, 비용, 로그, 후처리 객체, 그리고 drying_store를 멤버 변수에 저장합니다.
          - DRY_MACHINE 전역 설정(예: { 0: {"DRYING_SIZE": 3}, 1: {"DRYING_SIZE": 3} })을 참조하여,
            각 건조 머신의 용량(capacity), 현재 배치(batch: 아직 처리되지 않은 job들의 리스트), busy 여부(is_busy)를 관리하는 딕셔너리(self.machines)를 생성합니다.
          - 모든 건조 머신이 즉시 job 할당을 받지 못할 경우를 대비하여, 대기열(waiting_queue)을 초기화합니다.
        """
        self.env = env                                # SimPy 환경 객체
        self.daily_events = daily_events              # 일별 이벤트 로그 리스트
        self.unit_drying_cost = drying_cost           # 건조 비용 단위
        self.post_processor = post_processor           # 후처리(PostProcessing) 객체
        self.drying_store = drying_store               # 건조 작업을 위한 입력 버퍼 역할 Store
        
        # DRY_MACHINE 전역 설정을 참조하여 각 건조 머신의 capacity, batch, busy 상태를 관리하는 딕셔너리 생성
        # 예: DRY_MACHINE = { 0: {"DRYING_SIZE": 3}, 1: {"DRYING_SIZE": 3} }
        self.machines = {
            machine_id: {
                "capacity": DRY_MACHINE[machine_id]["DRYING_SIZE"],
                "batch": [],         # 해당 머신에 할당된 job들의 리스트
                "is_busy": False     # 현재 머신이 작업 중인지 여부
            }
            for machine_id in DRY_MACHINE.keys()
        }
        
        # 모든 건조 머신이 busy일 경우 대기시킬 job들을 위한 대기열
        self.waiting_queue = []

    def seize(self):
        """
        seize 메서드:
        - drying_store에서 job을 가져와, 사용 가능한(즉, busy가 아니고 배치가 capacity 미만인) 건조 머신에 즉시 할당합니다.
        - 만약 할당할 수 있는 건조 머신이 없다면 waiting_queue에 추가합니다.
        """
        while True:
            job = yield self.drying_store.get()
            assigned = False

            for machine_id, machine in self.machines.items():
                if not machine["is_busy"] and len(machine["batch"]) < machine["capacity"]:
                    machine["batch"].append(job)
                    self.daily_events.append(
                        f"{int(self.env.now % 24)}:{int((self.env.now % 1)*60):02d} - Job {job.job_id} assigned to Drying Machine {machine_id}. Batch: {[j.job_id for j in machine['batch']]}"
                    )
                    assigned = True
                    # 배치가 머신의 capacity에 도달하면 바로 배치 처리를 시작합니다.
                    if len(machine["batch"]) == machine["capacity"]:
                        machine["is_busy"] = True
                        current_batch = machine["batch"]
                        machine["batch"] = []  # 배치 초기화
                        self.env.process(self.delay(machine_id, current_batch))
                    break

            if not assigned:
                self.waiting_queue.append(job)
                self.daily_events.append(
                    f"{int(self.env.now % 24)}:{int((self.env.now % 1)*60):02d} - All Drying Machines busy/full. Job {job.job_id} added to waiting queue."
                )

    def delay(self, machine_id, jobs_batch):
        """
        delay 메서드:
        - 지정된 건조 머신(machine_id)에서 모인 jobs_batch를 한 번에 처리합니다.
        - 각 job의 drying_time이 없으면 기본값 1을 사용하며, 배치 내 총 drying_time(합산)을 처리 시간으로 결정합니다.
        - 건조 작업이 완료되면 release()를 호출하여 해당 머신을 free 상태로 전환하고, waiting_queue의 job들을 재할당합니다.
        """
        # 각 job에 drying_time이 없으면 기본값 1 할당
        for job in jobs_batch:
            if not hasattr(job, "drying_time") or job.drying_time is None:
                job.drying_time = 1
        drying_time = sum(job.drying_time for job in jobs_batch)
        self.daily_events.append(
            f"{int(self.env.now % 24)}:{int((self.env.now % 1)*60):02d} - Drying Machine {machine_id} starts processing batch {[job.job_id for job in jobs_batch]} for {drying_time} time units."
        )
        yield self.env.timeout(drying_time)
        self.daily_events.append(
            f"{int(self.env.now % 24)}:{int((self.env.now % 1)*60):02d} - Drying Machine {machine_id} finished processing batch."
        )
        # 처리 완료 후 release()를 호출하여 후속 처리를 진행합니다.
        self.release(machine_id, jobs_batch)

    def release(self, machine_id, jobs_batch):
        """
        release 메서드:
        - 지정된 건조 머신(machine_id)을 free 상태로 전환하고, 해당 머신의 배치(batch)를 명시적으로 비웁니다.
        - 건조 완료된 jobs_batch의 각 job을 후처리(PostProcessing) 단계로 전달합니다.
        - 이후, 머신이 free인 경우 waiting_queue에 있는 job들을 해당 머신의 배치에 재할당하고,
          만약 재할당 후 배치가 capacity에 도달하면, 새로운 delay() 프로세스를 실행하여 해당 배치를 처리합니다.
        """
        # 해당 머신을 free 상태로 전환하고 배치를 초기화합니다.
        self.machines[machine_id]["is_busy"] = False
        self.machines[machine_id]["batch"] = []
        
        # 건조 완료된 job들을 후처리 단계로 전달합니다.
        for job in jobs_batch:
            self.post_processor.env.process(self.post_processor.process_job(job))
        
        # 머신이 free인 경우, waiting_queue에서 job들을 가져와 배치에 추가합니다.
        while (self.waiting_queue and 
               (not self.machines[machine_id]["is_busy"]) and 
               (len(self.machines[machine_id]["batch"]) < self.machines[machine_id]["capacity"])):
            waiting_job = self.waiting_queue.pop(0)
            self.machines[machine_id]["batch"].append(waiting_job)
            self.daily_events.append(
                f"{int(self.env.now % 24)}:{int((self.env.now % 1)*60):02d} - After processing, waiting Job {waiting_job.job_id} assigned to Drying Machine {machine_id}. Batch: {[j.job_id for j in self.machines[machine_id]['batch']]}"
            )
        # 만약 재할당한 배치가 capacity에 도달하고 머신이 free 상태라면 delay()를 실행하여 배치 처리
        if (not self.machines[machine_id]["is_busy"]) and (len(self.machines[machine_id]["batch"]) == self.machines[machine_id]["capacity"]):
            self.machines[machine_id]["is_busy"] = True
            current_batch = self.machines[machine_id]["batch"]
            self.machines[machine_id]["batch"] = []
            self.env.process(self.delay(machine_id, current_batch))
            
# PostProcessing 클래스: 후처리 작업을 관리
class Proc_PostProcessing:
    """
    PostProcessing 클래스
    -----------------------
    drying 단계에서 전달된 job(여러 item 포함)을 받아, 각 item에 대해 후처리 작업을 수행합니다.
    각 item은 사용 가능한 작업자에게 즉시 할당되며, 모든 작업자가 바쁘면 대기열에 저장됩니다.
    후처리 완료된 item은 Packaging 단계로 바로 전달됩니다.
    """
    def __init__(self, env, post_processing_cost, daily_events, packaging):
        """
        __init__ 메서드 (생성자)
        -------------------------
        env: SimPy 환경 객체 (시뮬레이션 시간 및 이벤트 관리)
        post_processing_cost: 후처리 비용 단위
        daily_events: 일별 이벤트 로그 리스트 (이벤트 기록용)
        packaging: Packaging 단계 객체 참조 (후처리 완료된 item 전달용)
        """
        self.env = env
        self.daily_events = daily_events
        # 각 작업자의 사용 가능 여부를 관리 (POST_PROCESSING_WORKER의 키 사용)
        self.workers = {worker_id: {"is_busy": False} for worker_id in POST_PROCESSING_WORKER.keys()}
        self.queue = []  # 모든 작업자가 바쁠 때 후처리할 item들을 저장하는 대기열
        self.packaging = packaging  # Packaging 객체 참조
        self.unit_post_processing_cost = post_processing_cost

    def seize(self, job):
        """
        seize 메서드
        ------------------
        drying 단계에서 전달된 job을 받아, job 내의 각 item에 대해 후처리 작업을 할당합니다.
        사용 가능한 작업자가 있으면 바로 후처리 프로세스(delay)를 시작하고,
        만약 모든 작업자가 사용 중이면 해당 item은 대기열에 저장됩니다.
        
        매개변수:
            job: 후처리할 item들을 포함한 job 객체
        """
        # job 내의 각 item에 대해 후처리 작업 할당 시도
        for item in job.items:
            assigned = False
            for worker_id, worker in self.workers.items():
                if not worker["is_busy"]:
                    # 사용 가능한 작업자를 찾으면 busy 상태로 변경하고 delay 프로세스 시작
                    self.workers[worker_id]["is_busy"] = True
                    self.env.process(self.delay(worker_id, item))
                    assigned = True
                    break
            if not assigned:
                # 모든 작업자가 바쁘면 해당 item을 대기열에 추가
                self.daily_events.append(
                    f"{int(self.env.now % 24)}:{int((self.env.now % 1) * 60):02d} - All workers busy. Item {item.item_id} of Job {item.job_id} added to waiting queue."
                )
                self.queue.append(item)

    def delay(self, worker_id, item):
        """
        delay 메서드
        -------------------
        개별 item의 후처리 작업을 수행하기 위해, item의 후처리 시간만큼 대기하는 프로세스입니다.
        delay가 완료되면 release 메서드를 호출하여 후처리 완료 후의 후속 작업을 처리합니다.
        후처리 완료 로그 기록 및 DAILY_REPORTS에 기록      
        매개변수:
            worker_id: 작업을 수행할 작업자의 ID
            item: 후처리 대상 item (job에 속한 item) 객체
        """
        start_time = self.env.now
        self.daily_events.append(
            f"{int(self.env.now % 24)}:{int((self.env.now % 1) * 60):02d} - Item {item.item_id} of Job {item.job_id} is starting on Worker {worker_id} (Post-processing)"
        )
        # item의 후처리 시간 설정 (없으면 기본값 1)
        if not hasattr(item, "post_processing_time") or item.post_processing_time is None:
            item.post_processing_time = 1
        # 후처리 시간만큼 대기 (delay)
        yield self.env.timeout(item.post_processing_time)
        end_time = self.env.now
        self.daily_events.append(
            f"{int(self.env.now % 24)}:{int((self.env.now % 1) * 60):02d} - Item {item.item_id} of Job {item.job_id} is finishing on Worker {worker_id} (Post-processing)"
        )
        # delay가 완료되면 release 메서드 호출
        yield self.env.process(self.release(worker_id, item, start_time, end_time))

    def release(self, worker_id, item, start_time, end_time):
        """
        release 메서드
        -------------------
        delay가 완료된 후 호출되며, 다음 작업들을 수행합니다.
          - 후처리 비용 계산
          - 해당 작업자를 해제(비어 있는 상태로 전환)
          - 후처리 완료된 item을 Packaging 단계로 전달
          - 대기열에 저장된 item이 있다면, 사용 가능한 작업자에게 할당
          
        매개변수:
            worker_id: 작업을 수행한 작업자의 ID
            item: 후처리 완료된 item 객체
            start_time: 해당 item의 후처리 시작 시간
            end_time: 해당 item의 후처리 완료 시간
        """
        DAILY_REPORTS.append({
            'job_id': item.job_id,
            'item_id': item.item_id,
            'worker_id': worker_id,
            'start_time': start_time,
            'end_time': end_time,
            'process': 'Post-Processing'
        })
        # 후처리 비용 계산
        Cost.cal_cost(item, "Post Processing cost")
        # 작업 완료 후 해당 작업자를 해제(비어 있는 상태로 전환)
        self.workers[worker_id]["is_busy"] = False
        # 후처리 완료된 item을 Packaging 단계로 전달
        self.packaging.assign_item(item)
        # 대기열에 있는 item이 있다면, 사용 가능한 작업자에게 할당
        if self.queue:
            next_item = self.queue.pop(0)
            for wid, worker in self.workers.items():
                if not worker["is_busy"]:
                    self.workers[wid]["is_busy"] = True
                    self.env.process(self.delay(wid, next_item))
                    break

# Packaging 클래스: 포장 작업을 관리
class Proc_Packaging:
    def __init__(self, env, packaging_cost, daily_events, satisfication):
        self.env = env  # SimPy 환경 객체 
        self.daily_events = daily_events  # 일별 이벤트 로그 리스트
        self.unit_packaging_cost = packaging_cost
        # 포장 작업자를 관리하는 딕셔너리 (PACKAGING_MACHINE의 키 사용)
        self.workers = {worker_id: {"is_busy": False} for worker_id in PACKAGING_MACHINE.keys()}
        self.queue = []  # 대기 중인 전문 job들을 저장할 큐
        self.satisfication = satisfication

    def assign_job(self, job):
        """
        PostProcessing이 완료된 전문 job을 받아, 즉시 포장 작업을 할당하거나,
        사용 가능한 작업자가 없으면 대기열에 추가합니다.
        """
        self.daily_events.append(
            f"{int(self.env.now % 24)}:{int((self.env.now % 1)*60):02d} - Job {job.job_id} sent to Packaging."
        )
        assigned = False
        # 사용 가능한 작업자를 탐색
        for worker_id, worker in self.workers.items():
            if not worker["is_busy"]:
                worker["is_busy"] = True
                self.env.process(self.process_job(job, worker_id))
                assigned = True
                break
        if not assigned:
            self.queue.append(job)

    def process_job(self, job, worker_id):
        """
        전문 job 전체에 대해 포장 작업을 수행하는 프로세스.
        예시에서는 포장 시간은 1 시간으로 고정되어 있으며,
        포장 비용은 전문 job 내 모든 Item의 부피 총합에 따라 산정합니다.
        """
        start_time = self.env.now
        packaging_time = 1  # 포장 시간 (예시)
        self.daily_events.append(
            f"{int(self.env.now % 24)}:{int((self.env.now % 1)*60):02d} - Job {job.job_id} starts Packaging on Worker {worker_id}."
        )
        yield self.env.timeout(packaging_time)
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
            total_volume = sum(item.volume for item in job.items)
            if total_volume >= 25:
                cost = 2 * self.unit_packaging_cost
            else:
                cost = 1 * self.unit_packaging_cost
            DAILY_COST_REPORT["Packaging cost"] += cost

        if PRINT_SATISFICATION:
            # 포장 완료 후 만족도 관련 추가 처리 (필요시 구현)
            pass

        # 포장 작업자 해제 후, 대기열에 있는 전문 job 처리
        self.workers[worker_id]["is_busy"] = False
        if self.queue:
            next_job = self.queue.pop(0)
            self.workers[worker_id]["is_busy"] = True
            self.env.process(self.process_job(next_job, worker_id))


# Job 클래스: Job의 속성을 정의
class Item:
    def __init__(self, env, item_id, config, job_id=None):
        self.env = env
        self.item_id = item_id
        self.job_id = job_id
        self.create_time = env.now
        self.height = np.random.randint(*config["HEIGHT_RANGE"])
        self.width = np.random.randint(*config["WIDTH_RANGE"])
        self.depth = np.random.randint(*config["DEPTH_RANGE"])
        self.volume = self.height * self.width * self.depth
        
        # 각 단계별 처리 시간 (빌드, 후처리)
        self.build_time = None      
        self.post_processing_time = None  
        
        # 기타 속성 (예: 비용, due date 등 필요시 추가)
        self.due_date = None
        
        # 비용 항목 초기화
        self.printing_cost = 0
        self.post_processing_cost = 0
        self.packaging_cost = 0
        self.delivery_cost = 0
        self.shortage_cost = 0
        self.shortage = 0


class Cost:
    def cal_cost(instance, cost_type):
        if cost_type == "Holding cost":
            DAILY_COST_REPORT[cost_type] += instance.unit_holding_cost * instance.on_hand_inventory * (
                instance.env.now - instance.holding_cost_last_updated)
        elif cost_type == "Printing cost":
            DAILY_COST_REPORT[cost_type] += instance.job_build_time * COST_TYPES[0]['PRINTING_COST']
        elif cost_type == "Post Processing cost":
            DAILY_COST_REPORT[cost_type] += instance.post_processing_time * COST_TYPES[0]['POSTPROCESSING_COST']
        elif cost_type == "Delivery cost":
            DAILY_COST_REPORT[cost_type] += 1
        elif cost_type == "Packaging cost":
            if instance.volume >= 25:
                DAILY_COST_REPORT[cost_type] += 2 * COST_TYPES[0]['PACKAGING_COST']
            else:
                DAILY_COST_REPORT[cost_type] += 1 * COST_TYPES[0]['PACKAGING_COST']
        elif cost_type == "Shortage cost":
            DAILY_COST_REPORT[cost_type] += instance.shortage * COST_TYPES[0]['SHORTAGE_COST']


    def update_cost_log():
        COST_LOG.append(0)
        for key in DAILY_COST_REPORT.keys():
            COST_LOG[-1] += DAILY_COST_REPORT[key]
        return COST_LOG[-1]

    def clear_cost():
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
    printer_store = simpy.Store(simpy_env)
    washing_store = simpy.Store(simpy_env)
    drying_store = simpy.Store(simpy_env)
    
    # Satisfication, Packaging, PostProcessing, Drying, Washing, Customer, Display 생성
    satisfication = Satisfication(simpy_env, daily_events)
    packaging = Proc_Packaging(simpy_env, COST_TYPES[0]['PACKAGING_COST'], daily_events, satisfication)
    post_processor = Proc_PostProcessing(simpy_env, COST_TYPES[0]['POSTPROCESSING_COST'], daily_events, packaging)
    dry_machine = Proc_Drying(simpy_env, COST_TYPES[0]['DRYING_COST'], daily_events, post_processor, drying_store)
    washing_machine = Proc_Washing(simpy_env, COST_TYPES[0]['WASHING_COST'], daily_events, dry_machine, washing_store, drying_store)
    customer = Customer(simpy_env, COST_TYPES[0]['SHORTAGE_COST'], daily_events, satisfication, printer_store)
    display = Display(simpy_env, daily_events)
    
    # Printer 생성 시 order_store와 washing_machine (즉, Washing.assign_order 호출) 전달
    printers = [
        Proc_Printer(simpy_env, COST_TYPES[0]['PRINTING_COST'], daily_events, pid, washing_machine, printer_store, washing_store)
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
    simpy_env.process(customer.create_jobs_continuously())

    # 각 Printer의 주문 처리 프로세스 실행
    for printer in printers:
        simpy_env.process(printer.seize())