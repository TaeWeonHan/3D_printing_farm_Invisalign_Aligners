from base_Job import Job
from config_SimPy import *
from specialized_Process import Proc_Build, Proc_Wash, Proc_Dry, Proc_Inspect
from base_Customer import OrderReceiver
import math


class Manager(OrderReceiver):
    """
    Manager class to control the manufacturing processes and track orders

    Attributes:
        env (simpy.Environment): Simulation environment
        logger (Logger): Logger object for logging events
        next_job_id (int): Next job ID counter
        completed_orders (list): List of completed orders 
        processed_orders (list): List of processed orders
        processed_patients (list): List of processed patients
    """

    def __init__(self, env, logger=None):
        self.env = env
        self.logger = logger

        # Next job ID counter
        self.next_job_id = 1

        # Tracking completed jobs and orders
        self.completed_orders = []

        # Tracking processed jobs and orders
        self.processed_orders = []

        # Tracking processed patients
        self.processed_patients = []

        # When calling setup_processes, the manager (self) itself is also passed as an argument
        self.setup_processes(manager=self)

    def setup_processes(self, manager=None):
        """Create and connect all manufacturing processes"""
        # Create processes
        self.proc_build = Proc_Build(self.env, self.logger)
        self.proc_wash = Proc_Wash(self.env, self.logger)
        self.proc_dry = Proc_Dry(self.env, self.logger)
        self.proc_inspect = Proc_Inspect(self.env, manager, self.logger)

        # Connect processes
        self.proc_build.connect_to_next_process(self.proc_wash)
        self.proc_wash.connect_to_next_process(self.proc_dry)
        self.proc_dry.connect_to_next_process(self.proc_inspect)

        if self.logger:
            self.logger.log_event(
                "Manager", "Manufacturing processes created and connected")

    def receive_order(self, order):
        """Process incoming order from Customer"""
        if self.logger:
            self.logger.log_event(
                "Order", f"Received Order {order.id_order} for Customer {order.id_customer} with {order.num_patients} patients")

        # Mark order start time and record number of patients and total items
        order.time_start = self.env.now

        # Add patients to processed list
        self.processed_patients += order.list_patients

        # Add order to processed orders list
        self.processed_orders.append(order)

        # Convert order to jobs based on policy
        self.create_jobs_for_proc_build(order)

        return order

    def create_jobs_for_proc_build(self, order):
        """Convert Order to Jobs based on POLICY_ORDER_TO_JOB"""
        all_patients = order.list_patients

        for patient in all_patients:
            patient_items = patient.list_items

            # If patient's items fit within PALLET_SIZE_LIMIT, create a single job
            if len(patient_items) <= PALLET_SIZE_LIMIT:
                # Create a job with all items from this patient
                job = Job(self.next_job_id, patient_items)
                self.next_job_id += 1

                # Send job to Build process
                if self.logger:
                    self.logger.log_event(
                        "Manager", f"Created job {job.id_job} for patient {patient.id_patient} with {len(patient_items)} items")
                self.proc_build.add_to_queue(job)
            else:
                # Patient's items exceed PALLET_SIZE_LIMIT, apply splitting policy
                if POLICY_ORDER_TO_JOB == "MAX_PER_JOB":
                    # Split items into multiple jobs of roughly equal size
                    items_per_job = PALLET_SIZE_LIMIT
                    for i in range(0, len(patient_items), items_per_job):
                        job_items = patient_items[i:i+items_per_job]
                        job = Job(self.next_job_id, job_items)
                        self.next_job_id += 1

                        # Send job to Build process
                        if self.logger:
                            self.logger.log_event(
                                "Manager", f"Created job {job.id_job} for patient {patient.id_patient} with {len(job_items)} items (split job)")
                        self.proc_build.add_to_queue(job)

                # Additional policies can be implemented here if needed
                elif POLICY_ORDER_TO_JOB == "EQUAL_SPLIT":
                # Split items into num_jobs jobs with as-even-as-possible sizes
                    N = len(patient_items)
                    num_jobs = math.ceil(N / PALLET_SIZE_LIMIT)
                    base = N // num_jobs
                    rem = N % num_jobs
                    start = 0
                    for j in range(num_jobs):
                        size = base + (1 if j < rem else 0)
                        job_items = patient_items[start:start+size]
                        start += size
                        job = Job(self.next_job_id, job_items)
                        self.next_job_id += 1
                        if self.logger:
                            self.logger.log_event(
                                "Manager", f"Created job {job.id_job} for patient {patient.id_patient} with {len(job_items)} items (equal split job)")
                        self.proc_build.add_to_queue(job)

    def create_job_for_defects(self):
        """Create jobs for defective items that need rework"""
        # Get defective items from inspection process
        defective_items = self.proc_inspect.defective_items

        if not defective_items:
            return

        # Log the number of defective items found
        # if self.logger:
        #     self.logger.log_event(
        #         "Manager", f"Found {len(defective_items)} defective items to process")

        # Check if we have enough defective items for a job
        if len(defective_items) >= POLICY_NUM_DEFECT_PER_JOB:
            # Take the specified number of defective items
            items_for_job = defective_items[:POLICY_NUM_DEFECT_PER_JOB]

            # Create a new job for these defective items
            job = Job(self.next_job_id, items_for_job)
            job.is_reprocess = True  # Mark as a rework job
            self.next_job_id += 1

            # Remove these items from the defective items list
            self.proc_inspect.defective_items = defective_items[POLICY_NUM_DEFECT_PER_JOB:]

            # Add the job to the Build process queue according to policy
            if POLICY_REPROC_SEQ_IN_QUEUE == "QUEUE_LAST":
                # Add job to the end of the queue
                if self.logger:
                    self.logger.log_event(
                        "Manager", f"Created rework job {job.id_job} with {len(items_for_job)} defective items (added to end of queue)")
                    self.logger.log_event(
                        "Manager", f"Remaining defective items: {len(self.proc_inspect.defective_items)}")
                
                self.proc_build.defect_add_to_queue(job)
                    
    def check_orders_completed(self, item):
        """Check if an order has been fully completed based on the given item."""

        # 1) Find the corresponding Patient object by matching customer, order, and patient IDs
        patient = next(
            (p for p in self.processed_patients
            if p.id_customer == item.id_customer
            and p.id_order    == item.id_order
            and p.id_patient  == item.id_patient),
            None
        )
        if patient is None:
            # If no matching patient is found, exit early
            return

        # 2) Verify that this patient has completed all of their items
        if not patient.check_completion():
            # If the patient is not yet fully completed, exit early
            return

        # 3) Find the corresponding Order object by matching customer and order IDs
        order = next(
            (o for o in self.processed_orders
            if o.id_customer == item.id_customer
            and o.id_order    == item.id_order),
            None
        )
        if order is None:
            # If no matching order is found, exit early
            return

        # 4) Check if the order is fully completed and hasn't been recorded yet
        if order.check_completion() and order not in self.completed_orders:
            # Record completion time and compute makespan
            order.time_end = self.env.now
            order.makespan = order.time_end - order.time_start

            # Debug
            print(f"[Debug] Order {order.id_order} (Customer {order.id_customer}) completed at {order.time_end:.0f}, makespan: {order.makespan:.0f} min")

            # Add the order to the list of completed orders
            self.completed_orders.append(order)

            # Optionally log the completion event
            if self.logger:
                self.logger.log_event(
                    "Order",
                    f"Order {order.id_order} (Customer {order.id_customer}) "
                    f"completed at {order.time_end:.0f}, makespan: {order.makespan:.0f} min"
                )    

    def get_processes(self):
        """Return processes as a dictionary for statistics collection"""
        return {
            'build': self.proc_build,
            'wash': self.proc_wash,
            'dry': self.proc_dry,
            'inspect': self.proc_inspect
        }

    def collect_statistics(self):
        """Collect basic statistics from processes"""
        stats = {}

        # Completed jobs per process
        stats['build_completed'] = len(self.proc_build.completed_jobs)
        stats['wash_completed'] = len(self.proc_wash.completed_jobs)
        stats['dry_completed'] = len(self.proc_dry.completed_jobs)
        stats['inspect_completed'] = len(self.proc_inspect.completed_jobs)

        # Queue sizes
        stats['build_queue'] = self.proc_build.job_store.size
        stats['wash_queue'] = self.proc_wash.job_store.size
        stats['dry_queue'] = self.proc_dry.job_store.size
        stats['inspect_queue'] = self.proc_inspect.job_store.size

        # Defective items
        stats['defective_items'] = len(self.proc_inspect.defective_items)

        return stats
