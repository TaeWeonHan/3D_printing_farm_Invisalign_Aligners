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
    조건에 따라 생성된 Job들을 임시 리스트에 저장 후 일정 수가 쌓이면 job_store에 전달
    """
    def __init__(self, env, shortage_cost, daily_events, satisfication, job_store):
        """
        __init__ 메서드 (생성자)
        -------------------------
        self.env: SimPy 환경 객체로, 시뮬레이션의 시간 흐름을 관리합니다.
        self.daily_events: 일별 이벤트 로그 리스트로, Job 생성 및 처리 관련 이벤트를 기록
        self.current_item_id: 새 Item(구 Job)의 고유 ID를 생성하기 위한 카운터 (초기값 0)
        self.current_job_id: 새 전문 job(구 Order)의 고유 ID를 생성하기 위한 카운터 (초기값 0)
        self.unit_shortage_cost: Item 할당 실패 시 발생하는 부족 비용 단위
        self.satisfication: 고객 만족도 계산을 위한 객체
        self.job_store: 생성된 Job들을 저장할 SimPy Store 객체
        self.temp_job_list: 생성된 Job들을 임시로 저장하는 리스트로, 일정 개수가 누적되면 job_store에 전달
        
        매개변수:
            env: SimPy 환경 객체
            shortage_cost: 부족 비용 단위
            daily_events: 일별 이벤트 로그 리스트
            satisfication: 고객 만족도 계산 객체
            job_store: Job들을 저장할 SimPy Store 객체
        """
        self.env = env
        self.daily_events = daily_events
        self.current_item_id = 0   # 새 Item(구 Job) ID 생성에 사용
        self.current_job_id = 0    # 새 전문 job(구 Order) ID 생성에 사용
        self.unit_shortage_cost = shortage_cost
        self.satisfication = satisfication
        self.job_store = job_store
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
            - 생성된 Job은 임시 리스트(temp_job_list)에 저장되며, 리스트 크기가 CUSTOMER["JOB_LIST_SIZE"]에 도달하면 job_store에 일괄 전달한 후 리스트를 초기화
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

            # 일정 수의 전문 job이 쌓이면 job_store에 넣음
            if len(self.temp_job_list) >= CUSTOMER["JOB_LIST_SIZE"]:
                self.daily_events.append(
                    f"{int(self.env.now % 24)}:{int((self.env.now % 1)*60):02d} - {len(self.temp_job_list)} jobs accumulated. Sending batch to printer."
                )
                for job_obj in self.temp_job_list:
                    self.job_store.put(job_obj)
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
    def __init__(self, env, printing_cost, daily_events, printer_id, washing_machine, job_store):
        """
        생성자 (__init__)
        env: SimPy 환경 객체 (시뮬레이션 시간 및 이벤트 관리)
        daily_events: 일별 이벤트 로그 리스트 (이벤트 기록용)
        printer_id: 프린터의 고유 식별자
        washing_machine: 인쇄 완료 후 job을 전달할 워싱 머신 객체
        unit_printing_cost: 인쇄 비용 단위
        job_store: 전문 job을 받는 SimPy Store 객체
        """
        self.env = env                          # SimPy 환경, 시간 관리
        self.daily_events = daily_events        # 이벤트 로그 저장 리스트
        self.printer_id = printer_id            # 프린터 식별자
        self.is_busy = False                    # 프린터 사용 상태 (초기: 미사용)
        self.washing_machine = washing_machine  # 워싱 머신 객체 (인쇄 후 job 전달용)
        self.unit_printing_cost = printing_cost # 인쇄 비용 단위
        self.job_store = job_store              # 전문 job 저장 store

    def process_jobs(self):
        """
        process_jobs 메서드
        job_store에서 전문 job을 받아서 process_job 프로세스를 실행.
        """
        while True:
            job = yield self.job_store.get()  # job_store에서 job 받아옴
            yield self.env.process(self.process_job(job))  # job 처리 프로세스 실행

    def process_job(self, job):
        """
        process_job 메서드
        전문 job을 세 단계로 처리함: seize → delay → release.
        """
        yield self.env.process(self.seize(job))   # 자원 할당 및 세팅 처리
        yield self.env.process(self.delay(job))   # 인쇄(프린트) 작업 처리
        yield self.env.process(self.release(job)) # 마무리(closing) 처리

    def seize(self, job):
        """
        seize 메서드
        자원 할당 및 세팅 단계.
        job.set_up_start에 세팅 시작 시간 기록, is_busy를 True로 설정.
        1시간 대기 후 job.set_up_end에 세팅 종료 시간 기록.
        """
        job.set_up_start = self.env.now      # 세팅 시작 시간 기록
        self.is_busy = True                  # 프린터 사용 중으로 변경
        self.daily_events.append(
            f"{int(self.env.now % 24)}:{int((self.env.now % 1) * 60):02d} - Job {job.job_id} is seizing Printer {self.printer_id} (Set up)."
        )
        yield self.env.timeout(1)            # 1시간 대기 (세팅 시간)
        job.set_up_end = self.env.now         # 세팅 종료 시간 기록

    def delay(self, job):
        """
        delay 메서드
        인쇄(프린트) 작업 진행 단계.
        job.print_start에 인쇄 시작 시간 기록, job.job_build_time만큼 대기 후 job.print_end에 인쇄 종료 시간 기록.
        """
        job.print_start = self.env.now        # 인쇄 시작 시간 기록
        self.daily_events.append(
            f"{int(self.env.now % 24)}:{int((self.env.now % 1) * 60):02d} - Job {job.job_id} is being printed on Printer {self.printer_id} (Print)."
        )
        yield self.env.timeout(job.job_build_time)  # 인쇄 시간만큼 대기
        job.print_end = self.env.now           # 인쇄 종료 시간 기록

    def release(self, job):
        """
        release 메서드
        마무리(closing) 단계 처리.
        job.closing_start에 마무리 시작 시간 기록, 1시간 대기 후 job.closing_end에 마무리 종료 시간 기록.
        비용 계산 후 DAILY_REPORTS에 기록, job을 워싱 머신에 전달하고 is_busy를 False로 변경.
        """
        job.closing_start = self.env.now      # 마무리 시작 시간 기록
        self.daily_events.append(
            f"{int(self.env.now % 24)}:{int((self.env.now % 1) * 60):02d} - Job {job.job_id} is closing on Printer {self.printer_id} (Closing)."
        )
        yield self.env.timeout(1)             # 1시간 대기 (마무리 시간)
        job.closing_end = self.env.now         # 마무리 종료 시간 기록

        # 인쇄 비용 계산 처리
        if PRINT_SIM_COST:
            Cost.cal_cost(job, "Printing cost")

        # 인쇄 작업 기록 DAILY_REPORTS에 추가
        DAILY_REPORTS.append({
            'job_id': job.job_id,
            'printer_id': self.printer_id,
            'set_up_start': job.set_up_start,
            'set_up_end': job.set_up_end,
            'start_time': job.print_start,
            'end_time': job.print_end,
            'closing_start': job.closing_start,
            'closing_end': job.closing_end,
            'process': 'Printing'
        })

        # 수정된 부분: 기존 assign_job() 대신 seize_1() 호출
        self.washing_machine.assign_job(job)
        self.is_busy = False  # 프린터 상태를 미사용으로 변경


class Proc_Washing:
    """
    세척(워싱) 작업 처리 클래스
    공통 대기열에 job을 저장하고, 워싱 머신 용량에 맞게 배치 처리하는 역할.
    """
    def __init__(self, env, washing_cost, daily_events, dry_machine):
        """
        생성자 (__init__)
        env: SimPy 환경 객체 (시간 및 이벤트 관리)
        daily_events: 일별 이벤트 로그 리스트
        unit_washing_cost: 세척 비용 단위
        dry_machine: 세척 후 job을 전달할 건조(Drying) 단계 객체
        machines_capa: 각 워싱 머신의 용량(WASHING_SIZE)을 담은 딕셔너리
        available_machines: 사용 가능한 워싱 머신 ID 리스트 (초기에는 모두 가용)
        common_queue: 모든 job을 저장할 공통 대기열
        """
        self.env = env                                # SimPy 환경, 시간 관리
        self.daily_events = daily_events              # 이벤트 로그 리스트
        self.unit_washing_cost = washing_cost         # 세척 비용 단위
        self.dry_machine = dry_machine                # 건조 단계 객체

        # 각 워싱 머신의 용량(WASHING_SIZE)을 설정값(WASHING_MACHINE)에서 추출해 딕셔너리로 저장
        self.machines_capa = {
            machine_id: WASHING_MACHINE[machine_id]["WASHING_SIZE"]
            for machine_id in WASHING_MACHINE.keys()
        }
        self.available_machines = list(WASHING_MACHINE.keys())  # 초기 가용 머신 ID 리스트
        self.common_queue = []  # 공통 대기열, job을 저장

    def assign_job(self, job):
        """
        assign_job 메서드
        공통 대기열에 job 추가 후, 머신 용량에 따라 배치 처리 시도.
        """
        self.common_queue.append(job)  # job을 대기열에 추가
        self.daily_events.append(
            f"{int(self.env.now % 24)}:{int((self.env.now % 1) * 60):02d} - Job {job.job_id} added to common Washing Queue. (Queue length: {len(self.common_queue)})"
        )
        self.matche_job_to_machine()  # 대기열에 충분한 job 있으면 배치 처리 시도

    def matche_job_to_machine(self):
        """
        try_process_jobs 메서드
        사용 가능한 각 워싱 머신에 대해, 대기열의 job 수가 해당 머신 용량 이상이면 배치 처리 시작.
        """
        # available_machines 리스트 복사 후 순회 (리스트 변경 방지)
        for machine_id in list(self.available_machines):
            capa = self.machines_capa[machine_id]  # 해당 머신의 용량
            if len(self.common_queue) >= capa:       # 대기열에 job 충분하면
                # 해당 머신 용량만큼 job을 대기열에서 꺼내 배치(job list) 생성
                jobs_batch = [self.common_queue.pop(0) for _ in range(capa)]
                self.daily_events.append(
                    f"{int(self.env.now % 24)}:{int((self.env.now % 1) * 60):02d} - Preparing batch { [o.job_id for o in jobs_batch] } for Washing Machine {machine_id}."
                )
                self.available_machines.remove(machine_id)  # 해당 머신 사용 중 처리
                self.env.process(self._washing_job(machine_id, jobs_batch))  # 배치 처리 프로세스 시작

    def _washing_job(self, machine_id, jobs_batch):
        """
        _washing_job 메서드 (내부 처리)
        지정된 워싱 머신(machine_id)에서 jobs_batch에 포함된 job들을
        1시간 동안 세척 처리한 후, 각 job을 건조 단계로 전달.
        처리 완료 후, 해당 머신을 다시 가용 상태로 전환.
        """
        self.daily_events.append(
            f"{int(self.env.now % 24)}:{int((self.env.now % 1) * 60):02d} - Washing Machine {machine_id} starts processing jobs { [o.job_id for o in jobs_batch] }."
        )
        washing_time = 1  # 1시간 동안 세척 처리
        yield self.env.timeout(washing_time)  # 세척 작업 시간 대기
        self.daily_events.append(
            f"{int(self.env.now % 24)}:{int((self.env.now % 1) * 60):02d} - Washing Machine {machine_id} finished processing jobs { [o.job_id for o in jobs_batch] }."
        )
        
        # 세척 완료 후, 각 job을 건조 단계로 전달 처리
        for job in jobs_batch:
            self.dry_machine.env.process(self.dry_machine._drying_job(job))
        
        self.available_machines.append(machine_id)  # 머신을 가용 상태로 복귀
        self.matche_job_to_machine()  # 대기열에 남은 job 처리 추가 시도


# Drying Process 클래스: 건조 작업을 관리
class Proc_Drying:
    def __init__(self, env, drying_cost, daily_events, post_processor):
        self.env = env                                # SimPy 환경 객체
        self.daily_events = daily_events              # 일별 이벤트 로그
        self.unit_drying_cost = drying_cost           # 건조 비용 단위
        self.post_processor = post_processor          # 후처리(PostProcessing) 객체 참조
        # 각 건조기를 simpy.Resource로 생성 (동시에 처리 가능한 전문 job 수는 DRY_MACHINE의 DRYING_SIZE 사용)
        self.machines = {
            machine_id: simpy.Resource(env, capacity=DRY_MACHINE[machine_id]["DRYING_SIZE"])
            for machine_id in DRY_MACHINE.keys()
        }
    
    def _drying_job(self, job):
        """
        개별 전문 job에 대해 여러 건조기(Resource) 중 사용 가능한 하나를 기다린 후,
        해당 건조기에서 건조 작업을 수행.
        """
        # 모든 건조기에 대해 동시에 자원 요청(request) 생성
        requests = {
            machine_id: machine.request()
            for machine_id, machine in self.machines.items()
        }
        
        # 여러 요청 중 하나라도 할당될 때까지 대기 (AnyOf 사용)
        result = yield simpy.AnyOf(self.env, requests.values())
        
        # 할당된 건조기(Resource)를 확인하고, 나머지 요청은 취소
        granted_machine_id = None
        for machine_id, req in requests.items():
            if req in result.events:
                granted_machine_id = machine_id
            else:
                req.cancel()
        """
        if granted_machine_id is None:
            self.daily_events.append(
                f"{int(self.env.now % 24)}:{int((self.env.now % 1) * 60):02d} - Job {job.job_id} did not get a Drying Machine!"
            )
            return
        """
        self.daily_events.append(
            f"{int(self.env.now % 24)}:{int((self.env.now % 1) * 60):02d} - Job {job.job_id} is being dried on Drying Machine {granted_machine_id}."
        )
        
        # 건조 시간 (예시: 1 시간)
        drying_time = 1
        yield self.env.timeout(drying_time)
        
        self.daily_events.append(
            f"{int(self.env.now % 24)}:{int((self.env.now % 1) * 60):02d} - Job {job.job_id} finished drying on Drying Machine {granted_machine_id}."
        )
        
        # 사용한 건조기 자원 해제
        self.machines[granted_machine_id].release(requests[granted_machine_id])
        
        # 건조 완료 후, 후처리(PostProcessing) 단계로 전문 job 전달
        self.post_processor.env.process(self.post_processor.process_job(job))
# PostProcessing 클래스: 후처리 작업을 관리
class Proc_PostProcessing:
    def __init__(self, env, post_processing_cost, daily_events, packaging):
        self.env = env  # SimPy 환경 객체
        self.daily_events = daily_events  # 일별 이벤트 로그 리스트
        self.unit_post_processing_cost = post_processing_cost
        self.packaging = packaging  # Packaging 객체 참조

        # 작업자 관리를 위한 SimPy Store를 생성 (초기에는 모든 작업자가 사용 가능)
        self.worker_store = simpy.Store(self.env, capacity=len(POST_PROCESSING_WORKER))
        for wid in POST_PROCESSING_WORKER.keys():
            self.worker_store.put(wid)

    def process_job(self, job):
        """
        전문 job(job) 안의 각 item을 순차적으로 개별 처리하고,
        모든 item의 후처리가 완료되면 전문 job을 Packaging 단계로 전달합니다.
        """
        self.daily_events.append(
            f"{int(self.env.now % 24)}:{int((self.env.now % 1)*60):02d} - Job {job.job_id} received for PostProcessing with {len(job.items)} items."
        )
        processed_items = []
        # 전문 job 안의 item들을 순차적으로 처리
        for item in job.items:
            # 각 item을 개별적으로 후처리 처리 (동시에 처리하지 않고 순서대로 진행)
            yield self.env.process(self._process_item(item))
            processed_items.append(item)
        # 모든 item 처리가 끝나면 전문 job의 items 목록을 갱신
        job.items = processed_items
        self.daily_events.append(
            f"{int(self.env.now % 24)}:{int((self.env.now % 1)*60):02d} - All items in Job {job.job_id} finished PostProcessing. Sending job to Packaging."
        )
        # 후처리 완료된 전문 job을 Packaging 단계로 전달
        self.packaging.assign_job(job)

    def _process_item(self, item):
        """
        개별 item에 대해 사용 가능한 작업자(worker)를 기다렸다가 후처리 작업을 수행합니다.
        """
        # 사용 가능한 작업자(worker)를 기다림 (Store에서 get)
        worker_id = yield self.worker_store.get()
        self.daily_events.append(
            f"{int(self.env.now % 24)}:{int((self.env.now % 1)*60):02d} - Item {item.item_id} starts PostProcessing on Worker {worker_id}."
        )
        # 후처리 시간 만큼 대기 (item.post_processing_time은 시간 단위)
        yield self.env.timeout(item.post_processing_time)
        self.daily_events.append(
            f"{int(self.env.now % 24)}:{int((self.env.now % 1)*60):02d} - Item {item.item_id} finished PostProcessing on Worker {worker_id}."
        )
        if PRINT_SIM_COST:
            Cost.cal_cost(item, "Post Processing cost")
        # 처리 완료 후 작업자를 다시 반납
        yield self.worker_store.put(worker_id)

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
    job_store = simpy.Store(simpy_env)
    
    # Satisfication, Packaging, PostProcessing, Drying, Washing, Customer, Display 생성
    satisfication = Satisfication(simpy_env, daily_events)
    packaging = Proc_Packaging(simpy_env, COST_TYPES[0]['PACKAGING_COST'], daily_events, satisfication)
    post_processor = Proc_PostProcessing(simpy_env, COST_TYPES[0]['POSTPROCESSING_COST'], daily_events, packaging)
    dry_machine = Proc_Drying(simpy_env, COST_TYPES[0]['DRYING_COST'], daily_events, post_processor)
    washing_machine = Proc_Washing(simpy_env, COST_TYPES[0]['WASHING_COST'], daily_events, dry_machine)
    customer = Customer(simpy_env, COST_TYPES[0]['SHORTAGE_COST'], daily_events, satisfication, job_store)
    display = Display(simpy_env, daily_events)
    
    # Printer 생성 시 order_store와 washing_machine (즉, Washing.assign_order 호출) 전달
    printers = [
        Proc_Printer(simpy_env, COST_TYPES[0]['PRINTING_COST'], daily_events, pid, washing_machine, job_store)
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
        simpy_env.process(printer.process_jobs())