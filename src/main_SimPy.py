# main.py
import simpy
import random
from base_Customer import Customer
from manager import Manager
from log_SimPy import Logger
from config_SimPy import *
from base_Job import Job


def run_simulation(sim_duration=SIM_TIME):
    """Run the manufacturing simulation"""
    print("================ Manufacturing Process Simulation ================")

    # Setup simulation environment
    env = simpy.Environment()

    # Create logger with env
    logger = Logger(env)

    # Create manager and provide logger
    manager = Manager(env, logger)

    # Create customer to generate orders
    Customer(env, manager, logger)

    # Run simulation
    print("\nStarting simulation...")
    print(f"Simulation will run for {sim_duration} minutes")

    # Run simulation
    env.run(until=sim_duration)

    # ─── 디버깅용: waiting_history 출력 ───
    print("\n=== Debug: Waiting History per Job ===")
    # 1) 모든 프로세스 가져오기
    processes = manager.get_processes()                            # :contentReference[oaicite:0]{index=0}
    # 2) completed_jobs 집계 (중복 제거)
    all_jobs = []
    for proc in processes.values():
        all_jobs.extend(proc.completed_jobs)
    unique_jobs = {job.id_job: job for job in all_jobs}.values()

    # 3) 각 job의 waiting_history 출력
    for job in sorted(unique_jobs, key=lambda j: j.id_job):
        print(f"\nJob {job.id_job} waiting steps:")
        # waiting_history 는 dict 리스트: {'process','start_time','end_time','duration'}
        for step in getattr(job, 'waiting_history', []):
            proc = step.get('process')
            start = step.get('start_time')
            end   = step.get('end_time')
            dur   = step.get('duration')
            print(f"  - {proc}: start={start:.1f}, end={end:.1f}, dur={dur:.1f}")
    print("=== End Debug ===\n")
    print("\n=== Debug: Processing History per Job ===")
    # 1) 모든 프로세스 가져오기
    processes = manager.get_processes()                            # :contentReference[oaicite:0]{index=0}
    # 2) completed_jobs 집계 (중복 제거)
    all_jobs = []
    for proc in processes.values():
        all_jobs.extend(proc.completed_jobs)
    unique_jobs = {job.id_job: job for job in all_jobs}.values()

    # 3) 각 job의 waiting_history 출력
    for job in sorted(unique_jobs, key=lambda j: j.id_job):
        print(f"\nJob {job.id_job} processing steps:")
        # waiting_history 는 dict 리스트: {'process','start_time','end_time','duration'}
        for step in getattr(job, 'processing_history', []):
            proc = step.get('process')
            start = step.get('start_time')
            end   = step.get('end_time')
            dur   = step.get('duration')
            print(f"  - {proc}: start={start:.1f}, end={end:.1f}, dur={dur:.1f}")
    print("=== End Debug ===\n")
    
    # Collect and display results
    print("\n================ Simulation Results ================")

    # Get basic statistics from manager
    manager_stats = manager.collect_statistics()

    # Basic results
    print(f"Completed jobs by process:")
    print(f"  Build: {manager_stats['build_completed']}")
    print(f"  Wash: {manager_stats['wash_completed']}")
    print(f"  Dry: {manager_stats['dry_completed']}")
    print(f"  Inspect: {manager_stats['inspect_completed']}")

    print(f"\nRemaining defective items: {manager_stats['defective_items']}")

    # Queue statistics
    print("\nFinal queue lengths:")
    print(f"  Build queue: {manager_stats['build_queue']}")
    print(f"  Wash queue: {manager_stats['wash_queue']}")
    print(f"  Dry queue: {manager_stats['dry_queue']}")
    print(f"  Inspect queue: {manager_stats['inspect_queue']}")

    # Collect detailed statistics and visualize if enabled
    if DETAILED_STATS_ENABLED or GANTT_CHART_ENABLED or VIS_STAT_ENABLED:
        print("\nCollecting detailed statistics...")
        processes = manager.get_processes()
        stats = logger.collect_statistics(processes, manager.completed_orders)

        print("\n=== Detailed Statistics ===")
        for key, val in stats.items():
            print(f"  {key}: {val:.3f}" if isinstance(val, float) else f"  {key}: {val}")

        # Visualize results if enabled
        if GANTT_CHART_ENABLED or VIS_STAT_ENABLED:
            logger.visualize_statistics(stats, processes)

    print("\n================ Simulation Ended ================")


if __name__ == "__main__":
    # Set random seed for reproducibility
    random.seed(42)

    # Run the simulation
    run_simulation()
