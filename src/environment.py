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
     
# Customer 클래스: 지속적으로 Job(작업)을 생성
class Customer:
    def __init__(self, env, shortage_cost, daily_events, satisfication, job_store):
        self.env = env  # SimPy 환경 객체
        self.daily_events = daily_events  # 일별 이벤트 로그 리스트
        self.current_job_id = 0  # Job ID 초기값
        self.last_assigned_printer = -1  # 마지막으로 할당된 프린터 ID
        self.unit_shortage_cost = shortage_cost  # Shortage cost
        self.satisfication = satisfication
        self.job_store = job_store  # simpy.Store 객체 추가

    def create_jobs_continuously(self):
        """지속적으로 Job을 생성하고 프린터에 할당"""
        job_list = []
        while True:
            # SIM_TIME 이후에는 Job 생성 중단
            if self.env.now >= SIM_TIME * 24:
                break

            # 현재 날짜 계산
            day = int(self.env.now // 24) + 1

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
                job_list.append(job)

            
            else:
                # Shortage cost 발생: 적합한 프린터가 없을 때
                self.daily_events.append(
                    f"Job {job.job_id} could not be assigned: No suitable printer available (Job size: {job.volume:.2f})"
                )
                # Shortage cost 발생
                job.shortage = 1  # Shortage는 한 번에 한 프린터가 부족할 때 1로 설정
                
                Cost.cal_cost(job, "Shortage cost")
                
                # 고객 만족도 계산
                self.satisfication.cal_satisfication(job, self.env.now)
            
            # dispatching rule 적용 후 total_job_list에 job_list 추가
            if len(job_list) == JOB_LOT_SIZE:
                
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
                for job_item in next_process_job_list:
                    # 비동기로 job_store에 넣는다.
                    self.job_store.put(job_item)
                job_list.clear()

            # 다음 Job 생성 간격 (지수 분포 사용)
            interval = np.random.exponential(JOB_CREATION_INTERVAL)
            yield self.env.timeout(interval)

# Printer 클래스: 프린터의 작업 처리
class Printer:
    def __init__(self, env, printing_cost, daily_events, printer_id, post_processor, job_store):
        self.env = env
        self.daily_events = daily_events
        self.printer_id = printer_id
        self.is_busy = False
        self.post_processor = post_processor
        self.unit_printing_cost = printing_cost
        self.job_store = job_store  # simpy.Store 객체

    def process_jobs(self):
        while True:
            # job_store에서 job이 들어올 때까지 blocking
            job = yield self.job_store.get()
            self.is_busy = True
            start_time = self.env.now
            self.daily_events.append(
                f"{int(self.env.now % 24)}:{int((self.env.now % 1) * 60):02d} - Job {job.job_id} is printed on Printer {self.printer_id} (Print)"
            )
            Cost.cal_cost(job, "Printing cost")
            yield self.env.timeout(job.build_time / 60)
            end_time = self.env.now
            self.is_busy = False
            self.daily_events.append(
                f"{int(self.env.now % 24)}:{int((self.env.now % 1) * 60):02d} - Job {job.job_id} is finishing on Printer {self.printer_id} (Print)"
            )
            DAILY_REPORTS.append({
                'job_id': job.job_id,
                'printer_id': self.printer_id,
                'start_time': start_time,
                'end_time': end_time,
                'process': 'Printing'
            })
            self.post_processor.assign_job(job)

# PostProcessing 클래스: 후처리 작업을 관리
class PostProcessing:
    def __init__(self, env, post_processing_cost, daily_events, packaging):
        self.env = env  # SimPy 환경 객체
        self.daily_events = daily_events  # 일별 이벤트 로그 리스트
        self.workers = {worker_id: {"is_busy": False} for worker_id in POST_PROCESSING_WORKER.keys()}
        self.queue = []  # 대기열
        self.packaging = packaging  # Packaging 객체 참조
        self.unit_post_processing_cost = post_processing_cost

    def assign_job(self, job):
        """작업자에게 Job을 할당"""
        for worker_id, worker in self.workers.items():
            if not worker["is_busy"]:
                worker["is_busy"] = True
                self.daily_events.append(
                    f"{int(self.env.now % 24)}:{int((self.env.now % 1) * 60):02d} - Job {job.job_id} is starting on Worker {worker_id} (Post-processing)"
                )
                self.env.process(self.process_job(worker_id, job))
                return True
        self.queue.append(job)  # 모든 작업자가 바쁠 경우 대기열에 추가
        return False

    def process_job(self, worker_id, job):
        """Job 처리"""
        start_time = self.env.now
        yield self.env.timeout(job.post_processing_time)  # 후처리 시간 대기
        end_time = self.env.now
        self.daily_events.append(
            f"{int(self.env.now % 24)}:{int((self.env.now % 1) * 60):02d} - Job {job.job_id} is finishing on Worker {worker_id} (Post-processing)"
        )
        # DAILY_REPORTS에 기록
        DAILY_REPORTS.append({
            'job_id': job.job_id,
            'worker_id': worker_id,
            'start_time': start_time,
            'end_time': end_time,
            'process': 'Post-Processing'
        })
        # Post Processing 비용 계산
        Cost.cal_cost(job, "Post Processing cost")
        self.workers[worker_id]["is_busy"] = False

        # 후처리 완료 후 포장 작업에 전달
        self.packaging.assign_job(job)

        # 대기열에 Job이 있으면 다음 작업 처리
        if self.queue:
            next_job = self.queue.pop(0)
            self.env.process(self.process_job(worker_id, next_job))

# Packaging 클래스: 포장 작업을 관리
class Packaging:
    def __init__(self, env, packaging_cost, daily_events, satisfication):
        self.env = env  # SimPy 환경 객체
        self.daily_events = daily_events  # 일별 이벤트 로그 리스트
        self.workers = {worker_id: {"is_busy": False} for worker_id in PACKAGING_MACHINE.keys()}
        self.unit_packaging_cost = packaging_cost
        self.queue = []  # 대기열
        self.satisfication = satisfication

    def assign_job(self, job):
        """포장 작업자에게 Job을 할당"""
        for worker_id, worker in self.workers.items():
            if not worker["is_busy"]:
                worker["is_busy"] = True
                self.daily_events.append(
                    f"{int(self.env.now % 24)}:{int((self.env.now % 1) * 60):02d} - Job {job.job_id} is starting on Worker {worker_id} (Packaging)"
                )
                self.env.process(self.process_job(worker_id, job))
                return True
        self.queue.append(job)  # 모든 작업자가 바쁠 경우 대기열에 추가
        return False

    def process_job(self, worker_id, job):
        """Job 포장 처리"""
        start_time = self.env.now
        yield self.env.timeout(job.packaging_time / 60)  # 포장 시간을 시간 단위로 변환
        end_time = self.env.now
        self.daily_events.append(
            f"{int(end_time % 24)}:{int((end_time % 1) * 60):02d} - Job {job.job_id} is finishing on Worker {worker_id} (Packaging) & End_Time: s{end_time: .4f}"
        )
        # DAILY_REPORTS에 기록
        DAILY_REPORTS.append({
            'job_id': job.job_id,
            'worker_id': worker_id,
            'start_time': start_time,
            'end_time': end_time,
            'process': 'Packaging'
        })
        # Packaging 비용 계산
        Cost.cal_cost(job, "Packaging cost")

        # 고객 만족도 계산
        self.satisfication.cal_satisfication(job, end_time)
        self.workers[worker_id]["is_busy"] = False

        # 대기열에서 다음 Job 처리
        if self.queue:
            next_job = self.queue.pop(0)
            self.env.process(self.process_job(worker_id, next_job))

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
        self.build_time = int(round(self.volume / (config["BUILD_SPEED"] 
                                         * 3.14 
                                         * (config["FILAMENT_DIAMETER"]/2)**2
                                         )))  # 제작 시간
        self.post_processing_time = np.mean([self.height, self.width, self.depth]) // (config["POST_PROCESSING_TIME_COEFFICIENT"])  # 후처리 시간

        if self.volume <= (LENGHT_RANGE["WIDTH"]["MAX"] * LENGHT_RANGE["HEIGHT"]["MAX"] * LENGHT_RANGE["DEPTH"]["MAX"])/2:
            self.packaging_time = np.random.randint(*config["SMALL_PACKAGING_TIME_RANGE"])  # 포장 시간

        elif ((LENGHT_RANGE["WIDTH"]["MAX"] * LENGHT_RANGE["HEIGHT"]["MAX"] * LENGHT_RANGE["DEPTH"]["MAX"])/2 + 1 
              <= self.volume 
              <= (LENGHT_RANGE["WIDTH"]["MAX"] * LENGHT_RANGE["HEIGHT"]["MAX"] * LENGHT_RANGE["DEPTH"]["MAX"])):
            self.packaging_time = np.random.randint(*config["LARGE_PACKAGING_TIME_RANGE"])  # 포장 시간
        
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
            DAILY_COST_REPORT[cost_type] += (instance.volume + instance.build_time) * COST_TYPES[0]['PRINTING_COST']  # Example formula
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

# 환경 생성 함수
def create_env(daily_events):
    simpy_env = simpy.Environment()

    # simpy.Store를 사용하여 Job 대기열 생성 (무제한 크기)
    job_store = simpy.Store(simpy_env)
    
    satisfication = Satisfication(simpy_env, daily_events)
    packaging = Packaging(simpy_env, COST_TYPES[0]['PACKAGING_COST'], daily_events, satisfication)
    post_processor = PostProcessing(simpy_env, COST_TYPES[0]['POSTPROCESSING_COST'], daily_events, packaging)
    customer = Customer(simpy_env, COST_TYPES[0]['SHORTAGE_COST'], daily_events, satisfication, job_store)
    display = Display(simpy_env, daily_events)
    
    # 각 프린터 생성 시 job_store 전달
    printers = [
        Printer(simpy_env, COST_TYPES[0]['PRINTING_COST'], daily_events, pid, post_processor, job_store)
        for pid in PRINTERS.keys()
    ]

    return simpy_env, packaging, post_processor, customer, display, printers, daily_events, satisfication



def simpy_event_processes(simpy_env, packaging, post_processor, customer, display, printers, daily_events):
    """
    SimPy 이벤트 프로세스를 설정합니다.
    """
    # Day 추적 및 Job 생성 프로세스 추가
    simpy_env.process(display.track_days())
    simpy_env.process(customer.create_jobs_continuously())

    # 각 프린터의 작업 처리 프로세스 추가
    for printer in printers:
        simpy_env.process(printer.process_jobs())
