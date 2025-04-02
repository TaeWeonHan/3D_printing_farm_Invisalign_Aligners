import random
from config_SimPy import *
from base_Process import Process
from specialized_Processor import Mach_3DPrint, Mach_Wash, Mach_Dry, Worker_Inspect


class Proc_Build(Process):
    """
    3D Printing Process
    inherits from Process class  
    """

    def __init__(self, env, logger=None, manager=None):
        super().__init__("Proc_Build", env, logger)
        self.manager = manager

        # Initialize 3D printing machines
        for i in range(NUM_MACHINES_BUILD):
            self.register_processor(Mach_3DPrint(i+1))

    def acquire_pallet(self, job):
        """It is a method of acquiring pallets and binding them to jobs in the Build stage."""
        pallet_resource = self.manager.pallet_resource
        # acquire a pallet
        pallet = yield self.env.process(pallet_resource.acquire())
        pallet.assign_job(job)
        pallet.current_process = "Build"
        if self.logger:
            self.logger.log_event("Pallet", f"Job {job.id_job} acquired Pallet {pallet.id} at Build")
        return pallet    

    def apply_pallet_management_before(self, jobs):
        """새 hook: Build 단계에서 각 job에 대해 Pallet 획득 처리"""
        for job in jobs:
            if not hasattr(job, 'pallet') or job.pallet is None:
                yield self.env.process(self.acquire_pallet(job))

    def apply_special_processing(self, processor, jobs):
        """3D Printing special processing - possibility of defects"""
        """for job in jobs:
            print(f"job id: {job.id_job}")
            print(f"job items: {[item.id_item for item in job.list_items]}")
            for item in job.list_items:
                if random.random() < DEFECT_RATE_PROC_BUILD:
                    item.is_defect = True
                else:
                    item.is_defect = False
        return True"""
        
        # Validation senario - every 5th item is defective
        for job in jobs:
            count = 0
            print(f"job id: {job.id_job}")
            print(f"job items: {[item.id_item for item in job.list_items]}")
            for item in job.list_items:
                count += 1
                if count % 5 == 0:
                    item.is_defect = True
                else:
                    item.is_defect = False
            print(f"job id: {job.id_job}")
            print(f"defective job items: {[item.id_item for item in job.list_items if item.is_defect]}")
        return True


class Proc_Wash(Process):
    """
    Washing Process
    inherits from Process class   
    """

    def __init__(self, env, logger=None):
        super().__init__("Proc_Wash", env, logger)

        # Initialize wash machines
        for i in range(NUM_MACHINES_WASH):
            self.register_processor(Mach_Wash(i+1))


class Proc_Dry(Process):
    """
    Drying Process
    inherits from Process class
    """

    def __init__(self, env, logger=None):
        super().__init__("Proc_Dry", env, logger)

        # Initialize dry machines
        for i in range(NUM_MACHINES_DRY):
            self.register_processor(Mach_Dry(i+1))


class Proc_Inspect(Process):
    """
    Inspection Process
    inherits from Process class
    """

    def __init__(self, env, manager=None, logger=None):
        super().__init__("Proc_Inspect", env, logger)

        self.manager = manager

        # Initialize inspection workers
        for i in range(NUM_WORKERS_IN_INSPECT):
            self.register_processor(Worker_Inspect(i+1))

        # Defective items repository
        self.defective_items = []

    def release_pallet(self, job):
        """Method of returning pallets in Inspect step"""
        pallet_resource = self.manager.pallet_resource
        pallet = job.pallet
        if pallet:
            if self.logger:
                self.logger.log_event("Pallet", f"Job {job.id_job} releasing Pallet {pallet.id} at Inspect")
            # Upon return, reset the status of the pallet and return it to the resource
            yield self.env.process(pallet_resource.release(pallet))
            job.pallet = None

    def apply_pallet_management_after(self, jobs):
        """Pallet return processing for each job in Inspect step"""
        for job in jobs:
            if hasattr(job, 'pallet') and job.pallet is not None:
                yield self.env.process(self.release_pallet(job))

    def apply_special_processing(self, processor, jobs):
        """Inspection process special processing - defect identification"""
        if isinstance(processor, Worker_Inspect):
            for job in jobs:
                defective_items = []

                # Inspect each item
                for item in job.list_items:
                    # Identify defects
                    if item.is_defect:
                        defective_items.append(item)
                    else:
                        # Mark normal items as completed
                        item.is_completed = True

                # Process defective items
                if defective_items:
                    # Store defective items
                    self.defective_items.extend(defective_items)

                    if self.logger:
                        self.logger.log_event(
                            "Inspection", f"Found {len(defective_items)} defective items in job {job.id_job}")

                    # Check if enough defective items to create a new job
                    if len(self.defective_items) >= POLICY_NUM_DEFECT_PER_JOB:
                        # Create a job for the defective items
                        self.manager.create_job_for_defects()

        # Return True to indicate processing was done
        return True
