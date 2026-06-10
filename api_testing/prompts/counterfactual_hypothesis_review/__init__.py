# from .schema import Verdict
# from api_testing.utils.log import getLogger


# class CounterfactualHypothesisReview:
#     SYSTEM_PROMPT = """
# You are an expert API constraint analyst. Your task is to compare two competing hypotheses for the same API property using real counterexample execution results.

# You will be given:
# * Endpoint and property information
# * Hypothesis 1 derived from the OpenAPI specification
# * Hypothesis 2 derived from runtime observation
# * A short summary of counterexample requests and their responses

# Your job is to decide which hypothesis is more consistent with the observed counterexamples and which one is more likely to be the better property constraint.

# ### Output rules
# Return ONLY valid JSON in this exact structure, Dont explain anything, just return the JSON array:
# {
#   "datas": [
#     {
#       "id": 1,
#       "best_hypothesis": "<hypothesis_1|hypothesis_2|equal|union>",
#       "explanation": "<brief reasoning>"
#     }
#   ]
# }

# Use these values for best_hypothesis:
# * hypothesis_1
# * hypothesis_2
# * equal
# * union
# """

#     PROMPT = """
# Endpoint: {endpoint}
# Property: {property}
# Hypothesis 1 (spec): {hypothesis_1}
# Hypothesis 2 (runtime): {hypothesis_2}
# Relation: {relation}

# Counterexample summary:
# {counterexample_summary}
# """

#     def __init__(self, llm) -> None:
#         self.llm = llm
#         self.logger = getLogger()

#     def exec(self, *args, **kwargs):
#         prompt = self.PROMPT.format(*args, **kwargs)
#         self.logger.debug("CounterfactualHypothesisReview Prompt: " + prompt)
#         response, _ = self.llm.generate(
#             system_prompt=self.SYSTEM_PROMPT,
#             prompt=prompt,
#             schema=Verdict
#         )
#         self.logger.debug("CounterfactualHypothesisReview Response: " + response.model_dump_json(indent=2))
#         return response.datas

from .schema import Verdict
from api_testing.utils.log import getLogger


class CounterfactualHypothesisReview:

    SYSTEM_PROMPT = """
You are an expert API constraint analyst.

Your task is to determine which hypothesis better explains the observed API behavior.

You will receive:
- Endpoint and property information
- Hypothesis 1 (spec)
- Hypothesis 2 (runtime)
- Relationship between them
- Verification results showing how many examples satisfy each hypothesis
- Counterexample execution summary

Decision rules:

1. Prefer the hypothesis with a significantly higher validation rate.
2. If both hypotheses have nearly identical validation rates, choose "equal".
3. If both hypotheses explain different valid subsets of behavior and neither dominates, choose "union".
4. Use counterexamples to understand why a hypothesis fails.
5. Do not simply prefer specification-derived constraints.

Return ONLY valid JSON.

{
  "datas": [
    {
      "id": 1,
      "best_hypothesis": "<hypothesis_1|hypothesis_2|equal|union>",
      "explanation": ""
    }
  ]
}
"""

    PROMPT = """
Endpoint: {endpoint}
Property: {property}

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
        )

        self.logger.debug(
            "CounterfactualHypothesisReview Response:\n%s",
            response.model_dump_json(indent=2),
        )

        return response.datas