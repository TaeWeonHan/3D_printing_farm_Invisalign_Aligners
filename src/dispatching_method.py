def FIFO(next_process_job):
    n = len(next_process_job)
    for job1 in range(n-1):
        least = job1
        for job2 in range(job1+1, n):
            # 각 job 객체에 대해 create_time 속성을 비교
            if next_process_job[job2].create_time < next_process_job[least].create_time:
                # 최소 항목 갱신
                least = job2
        # create_time에 따라 job의 순서교환
        next_process_job[job1], next_process_job[least] = next_process_job[least], next_process_job[job1]
    return next_process_job

def LIFO(next_process_job):
    n = len(next_process_job)
    for job1 in range(n - 1):
        most = job1
        for job2 in range(job1 + 1, n):
            # 각 job 객체에 대해 create_time 속성을 비교하여
            # 더 늦게 생성된 (create_time 값이 큰) job을 찾는다.
            if next_process_job[job2].create_time > next_process_job[most].create_time:
                most = job2
        # create_time에 따라 job의 순서를 교환
        next_process_job[job1], next_process_job[most] = next_process_job[most], next_process_job[job1]
    return next_process_job

def SPT(next_process_job):
    """Shortest Processing Time (build_time이 가장 짧은 순으로 정렬)"""
    n = len(next_process_job)
    for i in range(n - 1):
        least = i
        for j in range(i + 1, n):
            if next_process_job[j].build_time < next_process_job[least].build_time:
                least = j
        next_process_job[i], next_process_job[least] = next_process_job[least], next_process_job[i]
    return next_process_job

def LPT(next_process_job):
    """Longest Processing Time (build_time이 가장 긴 순으로 정렬)"""
    n = len(next_process_job)
    for i in range(n - 1):
        most = i
        for j in range(i + 1, n):
            if next_process_job[j].build_time > next_process_job[most].build_time:
                most = j
        next_process_job[i], next_process_job[most] = next_process_job[most], next_process_job[i]
    return next_process_job

def EDD(next_process_job):
    """Earliest Due Date (due_date가 가장 임박한 순으로 정렬)"""
    n = len(next_process_job)
    for i in range(n - 1):
        earliest = i
        for j in range(i + 1, n):
            if next_process_job[j].due_date < next_process_job[earliest].due_date:
                earliest = j
        next_process_job[i], next_process_job[earliest] = next_process_job[earliest], next_process_job[i]
    return next_process_job