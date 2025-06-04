import os
import shutil
from config_SimPy import *

# RL algorithms
RL_ALGORITHM = "PPO"  # "DP", "DQN", "DDPG", "PPO", "SAC"

# Def Action
ORDER_TO_JOB_OPTIONS = ["EQUAL_SPLIT", "MAX_PER_JOB"]
REPROC_INSERT_OPTIONS = ["FRONT", "MIDDLE", "BACK"]

# 1) Action type
ACTION_TYPE = ["ORDER_TO_JOB", "REPROC_INSERT"] 

# 2) 각 action_type별 세부 옵션
ORDER_TO_JOB_SPACE = {0: "EQUAL_SPLIT", 1: "MAX_PER_JOB"}
REPROC_INSERT_SPACE = {0: "FRONT", 1: "MIDDLE", 2: "BACK"}

# 3. State Space 정의
# ─────────────────────────────────────────────────────────────────────────────
# 총 4개 공정(build, wash, dry, inspect)을 사용한다고 가정
PROCESS_NAMES = ["build", "wash", "dry", "inspect"]

# (1) State 차원 계산
#    1) Total completed jobs: 1차원
#    2) 공정별 waiting time avg, std: 4공정 × 2 = 8차원
#    3) 공정별 avg queue length: 4공정 × 1 = 4차원
#
# → 최종 차원: 1 + 8 + 4 = 13
STATE_DIMENSION = 1 + len(PROCESS_NAMES) * 2 + len(PROCESS_NAMES) * 1

# (2) State 벡터 내부에서 각 값이 차지하는 인덱스(참고용)
#     - completed_jobs       : index 0
#     - build_wait_avg       : index 1
#     - build_wait_std       : index 2
#     - wash_wait_avg        : index 3
#     - wash_wait_std        : index 4
#     - dry_wait_avg         : index 5
#     - dry_wait_std         : index 6
#     - inspect_wait_avg     : index 7
#     - inspect_wait_std     : index 8
#     - build_queue_avg_len  : index 9
#     - wash_queue_avg_len   : index 10
#     - dry_queue_avg_len    : index 11
#     - inspect_queue_avg_len: index 12
#
STATE_INDICES = {
    "completed_jobs": 0,
    "build_wait_avg": 1,  "build_wait_std": 2,
    "wash_wait_avg": 3,   "wash_wait_std": 4,
    "dry_wait_avg": 5,    "dry_wait_std": 6,
    "inspect_wait_avg": 7,"inspect_wait_std": 8,
    "build_q_avg": 9,     "wash_q_avg": 10,
    "dry_q_avg": 11,      "inspect_q_avg": 12,
}

# Episode
N_EPISODES = 2

def DEFINE_FOLDER(folder_name):
    if os.path.exists(folder_name):
        file_list = os.listdir(folder_name)
        folder_name = os.path.join(folder_name, f"Train_{len(file_list)+1}")
    else:
        folder_name = os.path.join(folder_name, "Train_1")
    os.makedirs(folder_name)
    return folder_name


def save_path(path):
    if os.path.exists(path):
        shutil.rmtree(path)
    # Create a new folder
    os.makedirs(path)
    return path

# Hyperparameter optimization
OPTIMIZE_HYPERPARAMETERS = False
N_TRIALS = 15  # 50

# RL_Options
INTRANSIT = 1  # 0 Means False , 1 Means True
USE_CORRECTION = True
EXPERIMENT = False

# Evaluation
N_EVAL_EPISODES = 10  # 100

# Export files
DAILY_REPORT_EXPORT = False
STATE_TRAIN_EXPORT = True
STATE_TEST_EXPORT = True

# Define parent dir's path
current_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(current_dir)
# Define each dir's parent dir's path
tensorboard_folder = os.path.join(parent_dir, "tensorboard_log")
experiment_folder = os.path.join(parent_dir, "experiment_log")
result_csv_folder = os.path.join(parent_dir, "result_CSV")
STATE_folder = os.path.join(result_csv_folder, "state")
result_experiment = os.path.join(result_csv_folder, "Experiment_Result")
daily_report_folder = os.path.join(result_csv_folder, "daily_report")

# Define dir's path
TENSORFLOW_LOGS = DEFINE_FOLDER(tensorboard_folder)
if EXPERIMENT:
    EXPERIMENT_LOGS = DEFINE_FOLDER(experiment_folder)

if EXPERIMENT:
    RESULT_CSV_EXPERIMENT = save_path(result_experiment)
STATE = save_path(STATE_folder)
REPORT_LOGS = save_path(daily_report_folder)

# Makedir
'''
if os.path.exists(STATE):
    pass
else:
    os.makedirs(STATE)

if os.path.exists(REPORT_LOGS):
    pass
else:
    os.makedirs(REPORT_LOGS)
if os.path.exists(GRAPH_FOLDER):
    pass
else:
    os.makedirs(GRAPH_FOLDER)
'''
# Visualize_Graph
VIZ_INVEN_LINE = False
VIZ_INVEN_PIE = False
VIZ_COST_PIE = False
VIZ_COST_BOX = False

# Saved Model
SAVED_MODEL_PATH = os.path.join(parent_dir, "Saved_Model")
SAVE_MODEL = False
SAVED_MODEL_NAME = "PPO_MODEL_test_val"

# Load Model
LOAD_MODEL = False
LOAD_MODEL_NAME = "PPO_MODEL_SIM500"