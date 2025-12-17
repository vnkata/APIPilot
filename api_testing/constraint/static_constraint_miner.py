class StaticConstraintMiner:
    def __init__(self, spec_parser=None, model=None, embedding_model=None,):
        self.spec_parser = spec_parser
        self.model = model
        self.embedding_model = embedding_model
        # self.max_load = 
        self.operations = self.spec_parser.operations
        self.schemas = {k: v for opt in self.operations.values() for k, v in opt.schemas.items()}
        
    def reuest_response_constraints(self):
        # Implement mining constraints between request and response

        pass
      
    def response_properties_constraints(self):
        # Implement mining constraints among response properties
        pass