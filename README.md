# SimPy based 3D Print Farm

## Operation scenario 
```mermaid
sequenceDiagram
    participant C as Customer
    participant M as Manager
    participant P as 3D Printers
    participant WM as Washing Machines
    participant DM as Drying Machines
    participant IW as Inspect Workers

    %% Process: Order to Job Creation
    autonumber
    C->>M: Creates and sends order
    M->>P: Converts order into job and sends to 3D Printers

    %% Process 1: Printing Process
    P-->>P: Builds the object

    %% Process 2: Washing Process
    P->>WM: Sends job to Washing Machines
    WM-->>WM: Performs washing

    %% Process 3: Drying Process
    WM->>DM: Sends job to Drying Machines
    DM-->>DM: Performs air-drying

    %% Process 4: Inspection Process
    DM->>IW: Sends job to Inspect Workers
    loop Each Item in Job
        IW-->>IW: Inspects item for defects
        alt Defect Found
            IW->>P: Creates new job for defective items and sends to 3D Printers
            Note right of P: Restart from 3D Printers
        else Good Item
            IW-->>IW: Keeps item as completed
        end
    end
```
## Problem Description
![Problem Description](https://github.com/user-attachments/assets/fb6320f8-66a6-4633-818c-7004ab839035)
![Gantt Chart](https://github.com/user-attachments/assets/ae8cf6ec-f4a5-45da-947f-61dbb3075db5)
1. The customer sends an order to the manager that includes patients and the items associated with each patient.

2. The manager converts the order into jobs and forwards those jobs to the 3D printing foundry.

3. The 3D printing foundry processes the jobs in the following sequence: build, washing, drying, and inspection. During the build stage, defects may occur, which are detected during the inspection stage.

4. If the number of defective items exceeds a certain threshold, the foundry sends the defective item information to the manager, who then creates a rework job for those defective items.

5. The results of the simulation can be confirmed through the Gant chart and terminal results.

## Requirements
In the simulator, we utilized simpy library.

## Simulator Process Description
Each process is executed in the following sequence: seize, delay, and release.

* Seize stage:
Jobs stored in the job_store are assigned to the available processors.

* Delay stage:
The actual processing takes place, where the available processors are utilized to process the jobs. Once processed, the jobs are forwarded to the next process, moving them to the release stage.

* Release stage:
The processors that have completed processing are marked as available again, allowing them to handle new jobs.

## Configuration setting
If you want to change the settings of the simulation, you can change the settings through the config_SimPy.py.

## Validation
This link is the validation page of our simulation(3D printing farm) [AIIS_LAB](https://www.notion.so/aiis/3D-printing-farm-professor-version-1bda689291af802093b8c2a052b6b1f8)