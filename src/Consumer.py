# Consumer.py
import simpy
import numpy as np
from config_Simpy import *
from log_simpy import *

class Job:
    def __init__(self, job_id, items, create_time):
        self.job_id = job_id
        self.items = items  # 전문 job에 포함된 Item 리스트
        self.create_time = create_time
        self.job_build_time = 1
        self.pallet_washing_time = np.random.randint(JOB_TYPES["DEFAULT"]["WASHING_RANGE"])

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
        
        # 제작, 후처리, 포장 시간 (예시)
        self.build_time = 1
        self.post_processing_time = 1
        if self.volume <= (RANGE_CONTROLLA["LENGHT_RANGE"]["WIDTH"]["MAX"] *
                           RANGE_CONTROLLA["LENGHT_RANGE"]["HEIGHT"]["MAX"] *
                           RANGE_CONTROLLA["LENGHT_RANGE"]["DEPTH"]["MAX"]) / 2:
            self.packaging_time = 1
        else:
            self.packaging_time = 1
        
        self.due_date = self.create_time + self.build_time + self.post_processing_time + self.packaging_time
        
        # 비용 항목 초기화
        self.printing_cost = 0
        self.post_processing_cost = 0
        self.packaging_cost = 0
        self.delivery_cost = 0
        self.shortage_cost = 0
        self.shortage = 0

class Customer:
    def __init__(self, env, shortage_cost, daily_events, satisfication, job_store):
        self.env = env
        self.daily_events = daily_events
        self.current_item_id = 0
        self.current_job_id = 0
        self.unit_shortage_cost = shortage_cost
        self.satisfication = satisfication
        self.job_store = job_store
        self.temp_job_list = []  # 임시로 쌓은 전문 job 리스트

    def create_jobs_continuously(self):
        while True:
            if self.env.now >= SIM_TIME * 24:
                break

            day = int(self.env.now // 24) + 1

            # 새로운 전문 job 생성 (빈 Item 리스트와 함께)
            new_job = Job(self.current_job_id, [], self.env.now)
            self.current_job_id += 1
            self.daily_events.append(
                f"{int(self.env.now % 24)}:{int((self.env.now % 1)*60):02d} - Job {new_job.job_id} created at time {new_job.create_time:.2f}."
            )

            # 전문 job 내에 CUSTOMER["ITEM_SIZE"]만큼 Item 생성
            for _ in range(CUSTOMER["ITEM_SIZE"]):
                item = Item(self.env, self.current_item_id, JOB_TYPES["DEFAULT"], job_id=new_job.job_id)
                self.current_item_id += 1

                ITEM_LOG.append({
                    'day': day,
                    'job_id': new_job.job_id,
                    'item_id': item.item_id,
                    'width': item.width,
                    'height': item.height,
                    'depth': item.depth,
                    'create_time': item.create_time,
                    'volume': item.volume,
                    'build_time': item.build_time,
                    'post_processing_time': item.post_processing_time,
                    'packaging_time': item.packaging_time
                })

                # 프린터 사이즈 제약 조건 체크 (예시)
                if (item.width <= PRINTERS_SIZE["WIDTH"] and
                    item.height <= PRINTERS_SIZE["HEIGHT"] and
                    item.depth <= PRINTERS_SIZE["DEPTH"]):
                    new_job.items.append(item)
                else:
                    self.daily_events.append(
                        f"Item {item.item_id} could not be assigned: No suitable printer available (Item size: {item.volume:.2f})"
                    )
                    item.shortage = 1
                    if PRINT_SIM_COST:
                        Cost.cal_cost(item, "Shortage cost")
                    if PRINT_SATISFICATION:
                        self.satisfication.cal_satisfication(item, self.env.now)
            
            self.temp_job_list.append(new_job)

            # 일정 수의 전문 job이 쌓이면 job_store에 배치
            if len(self.temp_job_list) >= CUSTOMER["JOB_LIST_SIZE"]:
                self.daily_events.append(
                    f"{int(self.env.now % 24)}:{int((self.env.now % 1)*60):02d} - {len(self.temp_job_list)} jobs accumulated. Sending batch to printer."
                )
                for job_obj in self.temp_job_list:
                    self.job_store.put(job_obj)
                self.temp_job_list.clear()

            interval = 5  # 생성 간격 (시간 단위)
            yield self.env.timeout(interval)
