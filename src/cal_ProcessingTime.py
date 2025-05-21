from config_SimPy import *

def calculate_processing_time(job, process_name, base_time):
    """
    Args:
        job: Job object (job.num_items used)
        process_name: 'Proc_Build' | 'Proc_Wash' | 'Proc_Dry' | 'Proc_Inspect'
        base_time: each machine and worker's processing_time
    Returns:
        float: dynamic calculated processing time
    """
    if process_name == 'Proc_Build':
        corr = BUILD_CORRELATION
    elif process_name == 'Proc_Wash':
        corr = WASH_CORRELATION
    elif process_name == 'Proc_Dry':
        corr = DRY_CORRELATION
    else:
        corr = INSPECT_CORRELATION

    # (Num of items × processing correlation × unit processing time) + base time
    return job.num_items * corr * UNIT_PROC_TIME + base_time