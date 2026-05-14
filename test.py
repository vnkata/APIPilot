from api_testing.inputs.request_params_mutator import ParamsMutator


generator = ParamsMutator()

print(generator.mutate({"existing_param": "value"}))