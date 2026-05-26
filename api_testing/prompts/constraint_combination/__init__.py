from .schema import ConstraintCombinationVerdict
from api_testing.utils.log import getLogger


class ConstraintCombination:
    """Classify equivalence or stage a conflict for runtime verification."""

    SYSTEM_PROMPT = """
You are an expert API testing assistant analyzing constraints extracted from
static specifications and dynamic execution traces for the same REST API
response property.

Your objectives are:
1. Determine whether the static and dynamic constraints are semantically
   EQUIVALENT, such as `gt(x, 0)` and `x >= 1` for integer values.
2. Detect a CONFLICT whenever one rule is different, narrower, incompatible,
   or cannot be proven equivalent from the supplied information.

Rules:
- For EQUIVALENT constraints:
  * Set status to "COMBINED_EQUIVALENT".
  * Set final_constraint to the supplied static constraint.
  * Set counter_example to null.
- For a CONFLICT:
  * Set status to "NOT_COMBINED".
  * Set final_constraint to null.
  * Construct counter_example with target_side, a realistic concrete property
    value when possible, a primary staged_payload, and staged_payloads.
  * Generate up to the requested number of distinct executable staged_payloads.
    They should vary meaningful query, body, or path parameter values that may
    distinguish the rules; do not repeat identical requests.
  * Each staged payload uses keys `http_method`, `endpoint_path`,
    `parameters`, `headers`, `body`, and `mime_type` as applicable. Store the
    first proposed case in staged_payload as well as staged_payloads.
  * If no request input can force the response value, keep staged_payload
    empty and describe the response-only counter-example using
    concrete_property_value and reason.

Do not select a winner and do not declare a union. Only runtime evidence may
later produce STATIC_WIN, DYNAMIC_WIN, or COMBINED_UNION.
Return JSON conforming exactly to the requested schema, without markdown.
"""

    PROMPT = """
Target Evaluation Context:
- Endpoint: {endpoint}
- Property: {property}
- Static Constraint (Specification Registry): {static_constraint}
- Dynamic Constraint (Observed Traces): {dynamic_constraint}
- Maximum Counter-Example Test Cases: {test_case_count}
"""

    def __init__(self, llm) -> None:
        self.llm = llm
        self.logger = getLogger(__name__)

    def exec(self, **kwargs) -> ConstraintCombinationVerdict:
        kwargs.setdefault("test_case_count", 5)
        prompt = self.PROMPT.format(**kwargs)
        self.logger.debug("ConstraintCombination Prompt: " + prompt)
        response, _ = self.llm.generate(
            system_prompt=self.SYSTEM_PROMPT,
            prompt=prompt,
            schema=ConstraintCombinationVerdict,
        )
        self.logger.debug(
            "ConstraintCombination Response: " + response.model_dump_json(indent=2)
        )
        return response
