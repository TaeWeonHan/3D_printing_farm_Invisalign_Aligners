import simpy
from config_SimPy import *
# base_Pallet.py
class BasePallet:
    def __init__(self, pallet_id, size_limit):
        self.id = pallet_id
        self.size_limit = size_limit
        self.current_job = None        # 현재 탑재된 Job (없으면 None)
        self.current_process = None    # Pallet이 위치한 공정 단계 이름
        self.current_machine = None    # Pallet이 할당된 머신 ID (있다면)
    
    def assign_job(self, job):
        """이 팔레트에 Job을 탑재"""
        self.current_job = job
        # job 객체에 pallet 연결 (양방향 연계)
        job.pallet = self
        job.pallet_id = self.id
        # 팔레트 상태 업데이트
        self.current_process = "Build"  # 최초 탑재 시 Build 단계로 설정
        self.current_machine = None     # Build 시점에 머신은 추후 설정
        
    def release_job(self):
        """Pallet에서 Job을 내려놓음 (반납 시)"""
        if self.current_job:
            # Pallet 상태 비움
            self.current_job.pallet = None
            self.current_job = None
        self.current_process = None
        self.current_machine = None

# base_Pallet.py (이어서)
class BasePalletResource:
    def __init__(self, env, total_pallets, pallet_size_limit):
        self.env = env
        self.store = simpy.Store(env, capacity=total_pallets)
        # Pallet 객체 풀 초기화
        self.pallets = [BasePallet(p_id, pallet_size_limit) for p_id in range(NUM_PALLETS)]
        for pallet in self.pallets:
            self.store.put(pallet)  # 초기 팔레트를 store에 채워둠

    @property
    def available_count(self):  
        """남아있는 팔레트 개수를 반환"""
        return len(self.store.items)
    
    def acquire(self):
        """Pallet 하나를 얻는 요청 이벤트를 반환"""
        return self.store.get()  # SimPy 이벤트 (yield 가능)

    def release(self, pallet):
        """사용 완료된 Pallet 반납 이벤트를 반환"""
        # 팔레트 객체 상태 초기화
        pallet.release_job()
        return self.store.put(pallet)
