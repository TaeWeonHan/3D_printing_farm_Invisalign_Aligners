import pandas as pd
import plotly.express as px
import plotly.figure_factory as ff
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
from config_SimPy import *


class Logger:
    def __init__(self, env):
        # Logger는 env만 저장하고 manager에 의존하지 않음
        self.env = env
        self.event_logs = []  # 이벤트 로그 저장소

    def log_event(self, event_type, message):
        """Log an event with a timestamp"""
        if EVENT_LOGGING:
            current_time = self.env.now
            days = int(current_time // (24 * 60))
            hours = int((current_time % (24 * 60)) // 60)
            minutes = int(current_time % 60)
            timestamp = f"{days:02d}:{hours:02d}:{minutes:02d}"
            total_minutes = int(current_time)
            print(f"[{timestamp}] [{total_minutes}] | {event_type}: {message}")

            # 나중에 분석을 위해 로그 저장
            self.event_logs.append((current_time, event_type, message))

    def collect_statistics(self, processes):
        """Collect statistics from the simulation

        Args:
            processes: Dictionary containing all process objects
                (e.g., {'build': proc_build, 'wash': proc_wash, ...})
        """
        stats = {}

        # Extract processes
        proc_build = processes.get('build')
        proc_wash = processes.get('wash')
        proc_dry = processes.get('dry')
        proc_inspect = processes.get('inspect')

        # Available processes for statistics
        available_processes = []
        for proc_name, proc in processes.items():
            if proc:
                available_processes.append(proc)

        # Completed jobs
        completed_jobs = []
        for proc in available_processes:
            completed_jobs.extend(proc.completed_jobs)

        # Remove duplicates by job ID
        unique_jobs = {}
        for job in completed_jobs:
            unique_jobs[job.id_job] = job

        completed_jobs = list(unique_jobs.values())

        # Basic statistics
        stats['total_completed_jobs'] = len(completed_jobs)

        # Process specific statistics
        process_ids = [proc.name_process for proc in available_processes]
        process_jobs = {proc_id: [] for proc_id in process_ids}

        for job in completed_jobs:
            process_id = job.workstation.get('Process')
            if process_id in process_jobs:
                process_jobs[process_id].append(job)

        # Analyze waiting and processing times
        for process_id, jobs in process_jobs.items():
            if jobs:
                # Waiting time statistics
                waiting_times = [(job.time_waiting_end - job.time_waiting_start)
                                 for job in jobs
                                 if job.time_waiting_end is not None and job.time_waiting_start is not None]

                if waiting_times:
                    stats[f'{process_id}_waiting_time_avg'] = sum(
                        waiting_times) / len(waiting_times)
                    stats[f'{process_id}_waiting_time_std'] = np.std(
                        waiting_times) if len(waiting_times) > 1 else 0

                # Processing time statistics
                processing_times = [(job.time_processing_end - job.time_processing_start)
                                    for job in jobs
                                    if job.time_processing_end is not None and job.time_processing_start is not None]

                if processing_times:
                    stats[f'{process_id}_processing_time_avg'] = sum(
                        processing_times) / len(processing_times)
                    stats[f'{process_id}_processing_time_std'] = np.std(
                        processing_times) if len(processing_times) > 1 else 0

        # Queue length statistics
        for proc in available_processes:
            if hasattr(proc, 'job_store') and hasattr(proc.job_store, 'queue_length_history'):
                if proc.job_store.queue_length_history:
                    # Calculate average queue length
                    times = [t for t, _ in proc.job_store.queue_length_history]
                    lengths = [
                        l for _, l in proc.job_store.queue_length_history]

                    if times and lengths:
                        # Add final point if needed
                        if times[-1] < self.env.now:
                            times.append(self.env.now)
                            lengths.append(lengths[-1])

                        # Calculate time-weighted average
                        weighted_sum = 0
                        for i in range(1, len(times)):
                            weighted_sum += lengths[i-1] * \
                                (times[i] - times[i-1])

                        avg_length = weighted_sum / self.env.now if self.env.now > 0 else 0
                        stats[f'{proc.name_process}_avg_queue_length'] = avg_length

        # Count defective items if inspection process exists
        if proc_inspect and hasattr(proc_inspect, 'defective_items'):
            stats['total_defects'] = len(proc_inspect.defective_items)

        return stats

    def visualize_statistics(self, stats, processes):
        """Visualize various statistics

        Args:
            stats: Dictionary of statistics collected
            processes: Dictionary containing all process objects
        """
        figures = {}

        # Process timings visualization - only if VIS_STAT_ENABLED
        if VIS_STAT_ENABLED:
            figures['waiting_time'] = self.visualize_process_statistics(
                stats, 'waiting_time')
            figures['processing_time'] = self.visualize_process_statistics(
                stats, 'processing_time')

            # Resource utilization visualization
            figures['queue_length'] = self.visualize_queue_lengths(processes)

        # Gantt chart (only if enabled) - independent of VIS_STAT_ENABLED
        if GANTT_CHART_ENABLED:
            figures['gantt'] = self.visualize_gantt(processes)

        # Display all figures
        for name, fig in figures.items():
            if fig is not None:
                fig.show()

        return figures

    def visualize_process_statistics(self, stats, stat_type):
        """Visualize process statistics (waiting time, processing time)"""
        if not VIS_STAT_ENABLED:
            return None

        # Find all processes in stats
        processes = set()
        for key in stats.keys():
            if f'_{stat_type}_avg' in key:
                proc_name = key.split('_')[0]
                processes.add(proc_name)

        processes = sorted(list(processes))

        # Extract relevant statistics
        avg_values = []
        std_values = []

        for process in processes:
            avg_key = f'{process}_{stat_type}_avg'
            std_key = f'{process}_{stat_type}_std'

            if avg_key in stats:
                avg_values.append(stats[avg_key])
                std_values.append(stats.get(std_key, 0))
            else:
                avg_values.append(0)
                std_values.append(0)

        # Create bar chart with error bars
        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=processes,
            y=avg_values,
            error_y=dict(
                type='data',
                array=std_values,
                visible=True
            ),
            name='Average'
        ))

        fig.update_layout(
            title=f"Process {stat_type.replace('_', ' ').title()}",
            xaxis_title="Process",
            yaxis_title=f"{stat_type.replace('_', ' ').title()} (minutes)"
        )

        return fig

    def visualize_queue_lengths(self, processes):
        """Visualize queue lengths over time"""
        if not VIS_STAT_ENABLED:
            return None

        fig = go.Figure()

        for proc_name, proc in processes.items():
            if proc and hasattr(proc, 'job_store') and hasattr(proc.job_store, 'queue_length_history'):
                if proc.job_store.queue_length_history:
                    # Keep times in minutes for x-axis
                    times = [t for t, _ in proc.job_store.queue_length_history]
                    lengths = [
                        l for _, l in proc.job_store.queue_length_history]

                    fig.add_trace(go.Scatter(
                        x=times,
                        y=lengths,
                        mode='lines',
                        name=proc.name_process
                    ))

        fig.update_layout(
            title="Queue Lengths Over Time",
            xaxis_title="Simulation Time (minutes)",
            yaxis_title="Queue Length",
            legend_title="Process"
        )

        return fig

    def visualize_gantt(self, processes):
        """Create slot-based Gantt chart - maintaining job slot consistency"""
        if not GANTT_CHART_ENABLED:
            return None

        # Get all resources from processes
        all_resources = self.get_all_resources(processes)
        resource_names = [r['name'] for r in all_resources]

        # Create resource name and original name mapping
        resource_mapping = {r['name']: r['original_name']
                            for r in all_resources}

        # Create original name and slot index mapping
        slot_mapping = {}
        for r in all_resources:
            if r['original_name'] not in slot_mapping:
                slot_mapping[r['original_name']] = []
            slot_mapping[r['original_name']].append((r['name'], r['slot']))

        # Create a trace for each job's processing step
        fig = go.Figure()

        # Track which resources have jobs
        resources_with_jobs = set()

        # Create dict to track created traces by job ID
        trace_keys = {}

        # Job assignment status tracking
        slot_assignment = {name: [] for name in resource_names}

        # Important: track job-machine slot assignments (for job slot consistency)
        job_machine_slot = {}  # {(job_id, machine_name): assigned_slot_name}

        # Collect all completed jobs
        completed_jobs = []
        for proc_name, proc in processes.items():
            if proc:
                completed_jobs.extend(proc.completed_jobs)

        for job in completed_jobs:
            # Job ID
            job_id = job.id_job

            # Check if job has processing history
            if hasattr(job, 'processing_history') and job.processing_history:
                # Get a consistent color for this job
                job_color = self.get_color_for_job(job_id)

                for step in job.processing_history:
                    # Skip incomplete steps
                    if step['end_time'] is None:
                        continue

                    # Get original resource name
                    orig_resource = step['resource_name']

                    # For machines with slots
                    if step['resource_type'] == 'Machine' and orig_resource in slot_mapping:
                        # Job's start/end times
                        start_min = step['start_time']
                        end_min = step['end_time']
                        duration_min = end_min - start_min

                        # Check if time is valid
                        if duration_min <= 0:
                            continue

                        # Create job-machine assignment key
                        job_machine_key = (job_id, orig_resource)

                        # Check if this job was previously assigned to this machine
                        if job_machine_key in job_machine_slot:
                            # Reuse previously assigned slot
                            assigned_slot = job_machine_slot[job_machine_key]
                        else:
                            # All slot info for original machine
                            slots = slot_mapping[orig_resource]

                            # Find appropriate slot (non-overlapping)
                            assigned_slot = None
                            for slot_name, slot_index in slots:
                                # Check existing jobs assigned to this slot
                                conflict = False
                                for existing_start, existing_end, existing_job_id in slot_assignment[slot_name]:
                                    # Skip conflict check for same job
                                    if existing_job_id == job_id:
                                        continue
                                    # Check if times overlap
                                    if not (end_min <= existing_start or start_min >= existing_end):
                                        conflict = True
                                        break

                                # If no time overlap, assign to this slot
                                if not conflict:
                                    assigned_slot = slot_name
                                    # Record job-machine slot assignment
                                    job_machine_slot[job_machine_key] = assigned_slot
                                    break

                            # If no suitable slot found, force assign to first slot
                            if assigned_slot is None:
                                assigned_slot = slots[0][0]
                                # Record job-machine slot assignment
                                job_machine_slot[job_machine_key] = assigned_slot

                        # Add job record to selected slot (with job ID)
                        slot_assignment[assigned_slot].append(
                            (start_min, end_min, job_id))

                        # Add job to selected slot
                        resource_name = assigned_slot

                    else:
                        # Workers don't need slots
                        resource_name = orig_resource
                        start_min = step['start_time']
                        end_min = step['end_time']
                        duration_min = end_min - start_min

                        # Check if time is valid
                        if duration_min <= 0:
                            continue

                    # Add to resources with jobs
                    resources_with_jobs.add(resource_name)

                    # Create trace name using only the job ID
                    trace_name = f"Job {job_id}"
                    trace_key = str(job_id)

                    # Check if we already created a legend entry for this job
                    show_legend = trace_key not in trace_keys
                    if show_legend:
                        trace_keys[trace_key] = True

                    # Create trace for this step
                    fig.add_trace(go.Bar(
                        y=[resource_name],
                        x=[duration_min],
                        base=start_min,
                        orientation='h',
                        name=trace_name,
                        marker_color=job_color,
                        text=f"Job {job_id}",
                        hovertext=f"Job {job_id} - {step['process']} - Duration: {duration_min} mins",
                        showlegend=show_legend,
                        legendgroup=trace_key,
                    ))

        # Add invisible traces for resources with no jobs
        for resource in resource_names:
            if resource not in resources_with_jobs:
                fig.add_trace(go.Bar(
                    y=[resource],
                    x=[0.001],
                    base=0,
                    orientation='h',
                    marker_color='rgba(0,0,0,0)',
                    showlegend=False,
                    hoverinfo="skip"
                ))

        # Customize layout
        fig.update_layout(
            title="Job Processing Gantt Chart",
            barmode='overlay',
            xaxis_title="Simulation Time (minutes)",
            yaxis_title="Resource",
            yaxis=dict(
                categoryorder='array',
                categoryarray=resource_names
            ),
            legend_title="Jobs",
            height=max(600, len(resource_names) * 30),
            showlegend=True
        )

        return fig

    def get_all_resources(self, processes):
        """Create resource list split into slots based on machine capacity"""
        resources = []

        # Extract processes from dictionary
        proc_build = processes.get('build')
        proc_wash = processes.get('wash')
        proc_dry = processes.get('dry')
        proc_inspect = processes.get('inspect')

        # Process machines for Build process
        if proc_build:
            for machine in proc_build.list_processors:
                if hasattr(machine, 'capacity_jobs') and machine.capacity_jobs > 1:
                    # Split into slots if capacity > 1
                    for slot in range(machine.capacity_jobs):
                        resources.append({
                            'name': f"{machine.name_machine}_Slot{slot+1}",
                            'original_name': machine.name_machine,
                            'slot': slot,
                            'type': 'Machine',
                            'process': 'Proc_Build'
                        })
                else:
                    # Add as is if capacity is 1
                    resources.append({
                        'name': machine.name_machine,
                        'original_name': machine.name_machine,
                        'slot': 0,
                        'type': 'Machine',
                        'process': 'Proc_Build'
                    })

        # Process machines for Wash process
        if proc_wash:
            for machine in proc_wash.list_processors:
                if hasattr(machine, 'capacity_jobs') and machine.capacity_jobs > 1:
                    for slot in range(machine.capacity_jobs):
                        resources.append({
                            'name': f"{machine.name_machine}_Slot{slot+1}",
                            'original_name': machine.name_machine,
                            'slot': slot,
                            'type': 'Machine',
                            'process': 'Proc_Wash'
                        })
                else:
                    resources.append({
                        'name': machine.name_machine,
                        'original_name': machine.name_machine,
                        'slot': 0,
                        'type': 'Machine',
                        'process': 'Proc_Wash'
                    })

        # Process machines for Dry process
        if proc_dry:
            for machine in proc_dry.list_processors:
                if hasattr(machine, 'capacity_jobs') and machine.capacity_jobs > 1:
                    for slot in range(machine.capacity_jobs):
                        resources.append({
                            'name': f"{machine.name_machine}_Slot{slot+1}",
                            'original_name': machine.name_machine,
                            'slot': slot,
                            'type': 'Machine',
                            'process': 'Proc_Dry'
                        })
                else:
                    resources.append({
                        'name': machine.name_machine,
                        'original_name': machine.name_machine,
                        'slot': 0,
                        'type': 'Machine',
                        'process': 'Proc_Dry'
                    })

        # Process workers for Inspect process (workers always have capacity=1)
        if proc_inspect:
            for worker in proc_inspect.list_processors:
                resources.append({
                    'name': worker.name_worker,
                    'original_name': worker.name_worker,
                    'slot': 0,
                    'type': 'Worker',
                    'process': 'Proc_Inspect'
                })

        return resources

    def get_color_for_job(self, job_id):
        """Return a color based on the job ID"""
        # List of colors for jobs - using a colorful palette
        colors = [
            'rgba(31, 119, 180, 0.8)',   # Blue
            'rgba(255, 127, 14, 0.8)',   # Orange
            'rgba(44, 160, 44, 0.8)',    # Green
            'rgba(214, 39, 40, 0.8)',    # Red
            'rgba(148, 103, 189, 0.8)',  # Purple
            'rgba(140, 86, 75, 0.8)',    # Brown
            'rgba(227, 119, 194, 0.8)',  # Pink
            'rgba(127, 127, 127, 0.8)',  # Gray
            'rgba(188, 189, 34, 0.8)',   # Olive
            'rgba(23, 190, 207, 0.8)'    # Cyan
        ]

        # Use modulo to cycle through colors for large number of jobs
        return colors[job_id % len(colors)]
