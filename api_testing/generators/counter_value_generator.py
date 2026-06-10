
from typing import Optional

from api_testing.models.specification_model import ItemProperties, OperationProperties
from api_testing.prompts.counter_value_generate import CounterValueGenerate


class HypothesisProperties:
    def __init__(
        self,
        name: str,
        hypothesis_1: str,
        hypothesis_2: str,
        relation: Optional[str] = None
    ):
        self.name = name
        self.hypothesis_1 = hypothesis_1
        self.hypothesis_2 = hypothesis_2
        self.relation = relation


class CounterValueGenerator:
    def __init__(
        self,
        operation: OperationProperties,
        hypothesis: HypothesisProperties,
        model=None,
        num_test_cases: int = 10,
        cache_dir: str = ".",
        context_pool=None,
    ):
        self.operation = operation
        self.hypothesis = hypothesis
        self.model = model
        self.num_test_cases = num_test_cases
        self.cache_dir = cache_dir
        self.context_pool = context_pool
        self._generator = CounterValueGenerate(llm=model)

    def exec(self):
        params = {
            "endpoint": f"{self.operation.http_method.upper()} {self.operation.endpoint_path}",
            "summary": ((self.operation.summary or "") + " " + (self.operation.description or "")).strip(),
            "num_test_cases": self.num_test_cases,
            "specific_endpoint_params": "\n".join([
                f"- {name} : {param.to_human_readable()}"
                for name, param in (self.operation.parameters or {}).items()
            ]),
            "specific_endpoint_body": None,
            "property": self.hypothesis.name,
            "hypothesis_1": self.hypothesis.hypothesis_1,
            "hypothesis_2": self.hypothesis.hypothesis_2,
            "relation": self.hypothesis.relation
        }

        if self.operation.request_body:
            first_body = next(iter(self.operation.request_body.values()))
            if isinstance(first_body, ItemProperties) and hasattr(first_body, "to_human_readable"):
                params["specific_endpoint_body"] = first_body.to_human_readable()
            else:
                params["specific_endpoint_body"] = str(first_body)

        results = self._generator.exec(**params)
        if hasattr(results, "dict"):
            return results.dict().get("datas")
        if isinstance(results, dict):
            return results.get("datas")
        return getattr(results, "datas", None)
