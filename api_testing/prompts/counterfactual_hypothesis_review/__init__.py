from .schema import Verdict
from api_testing.utils.log import getLogger


class CounterfactualHypothesisReview:

    SYSTEM_PROMPT = """
You are an expert API constraint analyst. Determine which hypothesis best represents true API behavior based on observed execution evidence.
### Inputs Received:
* Endpoint & property metadata
* Hypothesis 1 (spec-derived) & Hypothesis 2 (runtime-derived)
* Relationship metadata, validation statistics, and counterexample summaries
### Decision Rules:
1. **Empirical Support:** Prefer the hypothesis better supported by validation stats and uncontradicted by counterexamples.
* Select 1 if Hypothesis 1 has stronger empirical support.
* Select 2 if Hypothesis 2 has stronger empirical support.
Precision & Tie-Breaker: If both hypotheses are equally supported by empirical data:
2. **Precision (Strength):** If validation results are similar, prefer the **stronger, more restrictive** constraint (e.g., a logical subset, `between(x,1,34)` over `gte(x,1)`, or `A and B` over `A`).
* Prefer the stronger, more restrictive constraint (e.g., choose between(x,1,34) over gte(x,1)).
*If they are logically equivalent (differing only by redundant predicates), default to 1 (Spec-derived) as the baseline truth.
3. **Equivalence:** Treat constraints that differ only by redundant or implied predicates as equivalent.
4. **Union Criteria:** Choose **Union (3)** *only* if both hypotheses capture unique, valid behaviors. Avoid union if one is simply a broader, weaker, or redundant version of the other.
5. **Objectivity:** Evaluate purely on semantic implication and empirical data; do not inherently bias toward spec or runtime.
### Output Format:
Return **ONLY** a single digit. Do not include markdown formatting, JSON, or any text.
* `1` = Hypothesis 1 is preferred
* `2` = Hypothesis 2 is preferred
* `3` = Union is required
"""

    PROMPT = """
Endpoint: {endpoint}
Property: {property}
Description: {property_description}
Hypothesis 1 (spec):
{hypothesis_1}
Hypothesis 2 (runtime):
{hypothesis_2}
Relation:
{relation}
Verification Results:

Spec:
- Valid: {spec_valid}/{spec_total}
- Invalid Examples:
{spec_invalid_examples}

Runtime:
- Valid: {runtime_valid}/{runtime_total}
- Invalid Examples:
{runtime_invalid_examples}
"""

    def __init__(self, llm) -> None:
        self.llm = llm
        self.logger = getLogger()
    def summarize_invalid_examples(self, examples: list[dict]) -> str:
        if not examples:
            return "None"

        lines = []

        for idx, example in enumerate(examples, start=1):
            context = example.get("context")
            input_data = context.get("input", {})
            output_data = context.get("return", {})
            lines.append(
                f"{idx}. Input={input_data} => Output={output_data}"
            )

        return "\n".join(lines)
    
    def exec(
        self,
        endpoint: str,
        property: str,
        property_description: str,
        hypothesis_1: str,
        hypothesis_2: str,
        relation: str,
        verification_info: dict,
        # counterexample_summary: str,
    ):

        spec = verification_info.get("spec", {})
        runtime = verification_info.get("runtime", {})

        prompt = self.PROMPT.format(
            endpoint=endpoint,
            property=property,
            property_description=property_description,
            hypothesis_1=hypothesis_1,
            hypothesis_2=hypothesis_2,
            relation=relation,
            spec_valid=spec.get("valid", 0),
            spec_total=spec.get("total", 0),
            runtime_valid=runtime.get("valid", 0),
            runtime_total=runtime.get("total", 0),
            spec_invalid_examples=self.summarize_invalid_examples(spec.get("invalid_examples", [])),
            runtime_invalid_examples=self.summarize_invalid_examples(runtime.get("invalid_examples", [])),
        )

        self.logger.debug(
            "CounterfactualHypothesisReview Prompt:\n%s",
            prompt,
        )

        response, _ = self.llm.generate(
            system_prompt=self.SYSTEM_PROMPT,
            prompt=prompt,
            schema=Verdict,
            caller=self.__class__.__name__,
        )

        self.logger.debug(
            "CounterfactualHypothesisReview Response:\n%s",
            response.model_dump_json(indent=2),
        )

        return response.label