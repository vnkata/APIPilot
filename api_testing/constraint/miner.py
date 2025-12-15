class MinerConstraint:
    def __init__(self, miner_id: str, max_load: float):
        self.miner_id = miner_id
        self.max_load = max_load

    def is_within_constraints(self, current_load: float) -> bool:
        return current_load <= self.max_load
    
    def reuest_response_constraints(self):
        pass
      
    def response_properties_constraints(self):
        pass