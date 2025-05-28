import simpy
from config_SimPy import *

class Job:
    """
    Job class to represent a job in the manufacturing process

    Attributes:
        id_job (int): Unique job identifier
        workstation (dict): Current workstation assignment
        list_items (list): List of items in the job
        time_processing_start (float): Time when processing started
        time_processing_end (float): Time when processing ended
        time_waiting_start (float): Time when waiting started
        time_waiting_end (float): Time when waiting ended
        is_reprocess (bool): Flag for reprocessed jobs
        processing_history (list): List of processing history
    """

    def __init__(self, id_job, list_items):
        self.id_job = id_job
        self.workstation = {"Process": None, "Machine": None, "Worker": None}
        self.list_items = list_items
        self.time_processing_start = None
        self.time_processing_end = None
        self.time_waiting_start = None
        self.time_waiting_end = None
        self.is_reprocess = False  # Flag for reprocessed jobs
        self.num_items = len(self.list_items) # Set Num of items in job

        # Add processing history to track jobs across all processes and waiting
        self.processing_history = []  # Will store each process step details
        self.waiting_history = []  # Will store each waiting step details


class JobStore(simpy.Store):
    """
    Job queue management class that inherits SimPy Store

    Attributes:
        env (simpy.Environment): Simulation environment
        name (str): Name of the JobStore
        queue_length_history (list): Queue length
    """

    def __init__(self, env, name="JobStore"):
        super().__init__(env)
        self.name = name
        self.queue_length_history = []  # Track queue length history

    def put(self, item):
        """Add Job to Store (override)"""
        result = super().put(item)
        # Record queue length
        self.queue_length_history.append((self._env.now, len(self.items)))
        return result

    def rework_put(self, job):
        """
        Add a reprocessed job to the store according to the FRONT/MIDDLE/BACK policy:
        * FRONT: place after all existing reprocessed jobs (idx = number of existing reprocess jobs)
        * MIDDLE: insert at floor(len/2) plus offset for same-timestamp reprocess jobs with lower IDs
        * BACK: append to the end of the queue
        """
        # 1) Perform the standard put to append the job and get the event result
        result = super().put(job)

        # 2) Remove the newly appended job from the end of the internal list
        items = self.items  # internal Python list of stored jobs
        new_job = items.pop(-1)

        # 3) Determine insertion index based on the configured policy
        pos = POLICY_REPROC_INSERT_POSITION.upper()
        if pos == "FRONT":
            # Count existing reprocessed jobs for front insertion
            idx = sum(1 for j in items if getattr(j, "is_reprocess", False))

        elif pos == "MIDDLE":
            # Base index at the middle of the current queue
            base_index = len(items) // 2
            # Offset by the number of same-timestamp reprocessed jobs with lower IDs
            offset = sum(
                1
                for j in items
                if getattr(j, "is_reprocess", False)
                and getattr(j, "time_waiting_start", None) == self._env.now
                and j.id_job < new_job.id_job
            )
            idx = base_index + offset

        else:  # BACK
            # Simply append to the end
            idx = len(items)

        # 4) Insert the job at the calculated index
        items.insert(idx, new_job)

        # 5) Record the new queue length
        self.queue_length_history.append((self._env.now, len(items)))

        return result
    
    def get(self):
        """Get Job from queue (override)"""
        result = super().get()
        # Record queue length when getting result

        # Use event chain instead of callback
        def process_get(env, result):
            job = yield result
            self.queue_length_history.append((self._env.now, len(self.items)))
            return job

        return self._env.process(process_get(self._env, result))

    @property
    def is_empty(self):
        """Check if queue is empty"""
        return len(self.items) == 0

    @property
    def size(self):
        """Current queue size"""
        return len(self.items)
