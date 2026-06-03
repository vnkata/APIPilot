from .schema import ConstraintCombinationVerdict
from api_testing.utils.log import getLogger


class ConstraintCombination:
    """Classify the set relation between static and dynamic constraints."""

    SYSTEM_PROMPT = """
You are an expert API testing assistant classifying the set relation between
one static specification-derived constraint and one dynamic trace-derived
constraint for the same REST API response property.

Treat each constraint as a set of valid API cases. A case may include request
inputs and the response body because some rules relate input parameters to
returned properties. Compare only the two constraints provided in the user
message. Do not reason about whether a value was observed often enough or
"appears" in traces; compare the allowed case sets implied by the constraint
expressions.

Classify exactly one relation:
- EQUIVALENT: both constraints accept exactly the same cases.
- STATIC_STRONGER: every static-valid case is dynamic-valid, and at least one
  dynamic-valid case is not static-valid.
- DYNAMIC_STRONGER: every dynamic-valid case is static-valid, and at least one
  static-valid case is not dynamic-valid.
- PARTIAL_OVERLAP: at least one case satisfies both constraints, at least one
  static-valid case violates the dynamic constraint, and at least one
  dynamic-valid case violates the static constraint.
- DISJOINT: no possible case can satisfy both constraints.
- UNKNOWN: the implication direction cannot be determined from the provided
  minimal context.

Decision checklist:
- Choose PARTIAL_OVERLAP only after identifying both a static-valid case that
  violates dynamic and a dynamic-valid case that violates static.
- If you can identify only static-valid cases that violate dynamic, choose
  DYNAMIC_STRONGER.
- If you can identify only dynamic-valid cases that violate static, choose
  STATIC_STRONGER.
- The relation field must match the final conclusion in the reason.

Direction reminder:
- If one constraint is a strict subset of the other, choose STATIC_STRONGER or
  DYNAMIC_STRONGER. Do not choose PARTIAL_OVERLAP unless each side has at
  least one valid case rejected by the other side.
- If the static side adds an input-response equality on top of a shared enum,
  static is usually stronger.
- If the dynamic side adds an enum, range, length, membership, or equality on
  top of static existence or broad type checks, dynamic is usually stronger.
- If static only requires `exists(x)` and dynamic requires `x one of {...}`,
  dynamic is stronger because every enum value exists.
- If dynamic requires an exact string length and static only requires a
  non-empty string, dynamic is stronger because every exact-length string is
  non-empty. Do not call this PARTIAL_OVERLAP: there is no dynamic-valid
  exact-length string that violates non-empty.
- If dynamic only requires an exact string length while static requires a
  semantic validator such as isDateTime, they usually partially overlap because
  a fixed-length string may still be semantically invalid.
- In this DSL, `x is Url` means `isURL(x)`, and `isURL("")` is false.
  Therefore `and(isURL(x), gt(size_of(x), 0))` and `x is Url` are equivalent
  unless another predicate is present.
- If dynamic requires a count to be at least the size of a returned collection
  and static only requires the count to be nonnegative, dynamic is stronger
  because collection size cannot be negative.
- More generally, `x >= size(collection)` is stronger than `x >= 0` because
  `size(collection)` cannot be negative.
- If static requires membership in a finite set of fixed-length codes and
  dynamic only requires that same fixed length, static is stronger.
  Never treat a finite enum and a length check as equivalent: the length check
  admits unlisted strings.
- If static has both lower and upper numeric bounds and dynamic has only the
  same lower bound, static is stronger.
- If one side constrains a request-conditioned subset while the other
  constrains observed response values, they often partially overlap.
- If static allows `x == input` OR membership in a collection while dynamic
  requires only collection membership, they can partially overlap: `x == input`
  outside the collection can satisfy static but violate dynamic, while `x` in
  the collection with a value rejected by another static predicate can satisfy
  dynamic but violate static.
- Date format constraints and input-year equality constraints are independent
  dimensions; if one side enforces year matching and the other only enforces
  date format, they often partially overlap.

Generic examples:
- `gt(size_of(x), 0)` vs `LENGTH(x)==6` => DYNAMIC_STRONGER.
- `and(gte(x, 1), lte(x, 34))` vs `x >= 1` => STATIC_STRONGER.
- `in(code, ['AA', 'BB'])` vs `LENGTH(code)==2` => STATIC_STRONGER.
- `and(gt(x,0), implies(exists(input.s), or(eq(x,input.s), contains(ids,input.s))))`
  vs `x in ids[]` => PARTIAL_OVERLAP.
- `and(isURL(x), gt(size_of(x), 0))` vs `x is Url` => EQUIVALENT.

Return only the relation and a short reason. Do not add runtime conclusions,
confidence scores, executable examples, payload plans, or fields outside the
requested schema. Return JSON conforming exactly to the requested schema,
without markdown.
"""

    PROMPT = """
Target Evaluation Context:
- Endpoint: {endpoint}
- Property: {property}
- Static Constraint (Specification Registry): {static_constraint}
- Dynamic Constraint (Observed Traces): {dynamic_constraint}
"""

    def __init__(self, llm) -> None:
        self.llm = llm
        self.logger = getLogger(__name__)

    def exec(self, **kwargs) -> ConstraintCombinationVerdict:
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
