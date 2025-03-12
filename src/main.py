from config_Simpy import *  # 시뮬레이션 설정 및 구성 정보
import environment as env  # 환경 생성 및 프로세스 정의 (수정된 create_env와 simpy_event_processes 포함)
from log_simpy import *  # 로그 및 이벤트 기록
import pandas as pd  # 데이터 분석 및 저장
import visualization

# Step 1: 환경 및 객체 초기화
# 수정된 create_env는 아래 순서대로 반환합니다.
# (simpy_env, packaging, dry_machine, washing_machine, post_processor, customer, display, printers, daily_events, satisfication)
(simpy_env, packaging, dry_machine, washing_machine, post_processor, 
 customer, display, printers, daily_events, satisfication) = env.create_env(DAILY_EVENTS)

# Step 2: SimPy 이벤트 프로세스 설정
# (PostProcessing는 Drying에서 호출되고, Packaging는 PostProcessing 내부로 전달되므로 별도 실행은 필요하지 않습니다.)
env.simpy_event_processes(simpy_env, packaging, post_processor, customer, display, printers, washing_machine, dry_machine, daily_events)

# Step 3: 시뮬레이션 실행 (하루 단위)
for day in range(SIM_TIME):
    simpy_env.run(until=simpy_env.now + 24)

    if PRINT_SIM_EVENTS:
        print(f"\n===== Daily Event Log for Day {day + 1} =====")
        for log in daily_events:
            print(log)
    if PRINT_SIM_COST:
        print(f"\n===== Daily Cost Report for Day {day + 1} =====")
        for cost_type, cost_value in DAILY_COST_REPORT.items():
            print(f"{cost_type}: ${cost_value:.2f}")
    print(f"\n===== JOB LOG for Day {day + 1} =====")
    for job in ITEM_LOG:
        if job['day'] == day + 1:
            print(f"Item {job['job_id']}-{job['item_id']} | Width: {job['width']} x Height: {job['height']} x Depth: {job['depth']} = Volume: {job['volume']:.2f} | "
                  f"Creation Time: {job['create_time']:.4f} | "
                  f"Build Time: {job['build_time']} | Post-Processing Time: {job['post_processing_time']}")
    if PRINT_SATISFICATION:
        print(f"\n===== Total Satisfication for Day {day + 1}: {satisfication.total_satisfication:.4f} =====\n")

    daily_events.clear()
    env.Cost.clear_cost()

# 추가 작업 처리: 아직 처리 중인 주문이나 대기열이 있다면 (예: Customer의 order_store, Washing의 common_queue, Packaging의 queue, Packaging 작업자)
day = SIM_TIME + 1
while (customer.job_store.items or washing_machine.common_queue or packaging.queue or 
       any(worker["is_busy"] for worker in packaging.workers.values())):
    simpy_env.run(until=simpy_env.now + 24)

    if PRINT_SIM_EVENTS:
        print(f"\n===== Additional Daily Event Log for Day {day} =====")
        for log in daily_events:
            print(log)
    if PRINT_SIM_COST:
        print(f"\n===== Additional Cost Report for Day {day} =====")
        for cost_type, cost_value in DAILY_COST_REPORT.items():
            print(f"{cost_type}: ${cost_value:.2f}")
    print(f"\n===== ITEM LOG for Additional Day {day} =====")
    for job in ITEM_LOG:
        if job['day'] == day:
            print(f"Job {job['job_id']} | Volume: {job['volume']:.2f} | "
                  f"Build Time: {job['build_time']} | Post-Processing Time: {job['post_processing_time']}")
    if PRINT_SATISFICATION:
        print(f"\n===== Total Satisfication for Day {day}: {satisfication.total_satisfication:.4f} =====\n")

    daily_events.clear()
    env.Cost.clear_cost()
    day += 1

# 시뮬레이션 종료 후 전체 JOB_LOG 출력
print("\n============= Final ITEM LOG =============")
for job in ITEM_LOG:
    print(f"Day {job['day']} | Item {job['job_id']}-{job['item_id']} | Volume: {job['volume']:.2f} | "
          f"Build Time: {job['build_time']} | Post-Processing Time: {job['post_processing_time']}")

# DAILY_REPORTS 데이터를 DataFrame으로 변환 및 CSV 파일로 저장
print(DAILY_REPORTS)
export_Daily_Report = []
for record in DAILY_REPORTS:
    if record['process'] == 'Printing':
        export_Daily_Report.append({
            "DAY": int(record['start_time'] // 24) + 1,
            "JOB_ID": record['job_id'],
            "ASSIGNED_PRINTER": record.get('printer_id', None),
            "PRINTING_START": record['start_time'],
            "PRINTING_FINISH": record['end_time'],
            "ASSIGNED_POSTPROCESS_WORKER": None,
            "POSTPROCESSING_START": None,
            "POSTPROCESSING_FINISH": None,
            "ASSIGNED_PACKAGING_WORKER": None,
            "PACKAGING_START": None,
            "PACKAGING_FINISH": None
        })
    elif record['process'] == 'Post-Processing':
        for item in export_Daily_Report:
            if item['JOB_ID'] == record['job_id']:
                item["ASSIGNED_POSTPROCESS_WORKER"] = record.get('worker_id', None)
                item["POSTPROCESSING_START"] = record['start_time']
                item["POSTPROCESSING_FINISH"] = record['end_time']
    elif record['process'] == 'Packaging':
        for item in export_Daily_Report:
            if item['JOB_ID'] == record['job_id']:
                item["ASSIGNED_PACKAGING_WORKER"] = record.get('worker_id', None)
                item["PACKAGING_START"] = record['start_time']
                item["PACKAGING_FINISH"] = record['end_time']

daily_reports = pd.DataFrame(export_Daily_Report)
daily_reports.to_csv("./Daily_Report.csv", index=False)

if VISUALIZATION != False:
    visualization.visualization(export_Daily_Report)
