RESPONSE_PROPERTY_CONSTRAINTS_VALIDATION_SYSTEM_PROMPT = """You are an expert at analyzing API schema attributes and identifying which attributes have non-trivial, programmatically verifiable constraints.

**CRITICAL: What NOT to Mark as Having Constraints**
DO NOT mark attributes that only have basic type information:
- Attributes with only basic type (String, Integer, Boolean, Array)
- Attributes without explicit constraints beyond their type

**What TO Mark as Having Constraints**
Only mark True for attributes with constraints BEYOND basic schema validation:

1. **Explicit Schema Constraints**:
   - format is specified (e.g., date-time, uri, email)
   - enum is specified (allowed value list)
   - minimum, maximum, minLength, maxLength are specified
   - pattern is specified (regex)
   - minItems, maxItems, uniqueItems for arrays

2. **Explicit Description-Based Constraints**:
   - Description mentions specific format requirements
   - Description lists allowed values
   - Description states numeric or length limits
   - Description describes pattern requirements

3. **Semantic Constraints** (ONLY if explicitly stated):
   - Extract ONLY if description explicitly states a constraint rule
   - Example: "must be a positive integer" means mark True
   - Example: "must be 1 or 0" means mark True
   - DO NOT infer constraints from names alone

**Decision Rules:**
- If attribute has enum, format, minimum, maximum, minLength, maxLength, pattern: Mark True
- If description explicitly states a constraint rule: Mark True
- If attribute only has basic type info: Mark False
- If uncertain: Mark False

**Output Format:**
Return ONLY valid JSON without markdown formatting:

{
  "constraints": {
    "attribute_name": true/false
  }
}

**Important:**
- Return True ONLY if you are confident the attribute has non-trivial constraints
- Return False for attributes with only basic type information
- Include ALL attributes you analyzed in the output
- Use lowercase `true` and `false` (JSON boolean format)
- Do not add comments (//) in the actual JSON output
"""

RESPONSE_PROPERTY_CONSTRAINTS_VALIDATION_SYSTEM_PROMPT_V2 = """You are an expert at analyzing API response schemas and identifying fields that require validation constraints.

**Your Task:**
Examine the provided schema and attributes, then return ONLY the property paths that have validation constraints.

**What to include (property has constraints):**
- Fields with format restrictions (date, email, uri, uuid, etc.)
- Fields with value constraints (enum, min/max, pattern, length limits)
- Fields with type-specific rules (binary 0/1, required formats)
- Fields with documented validation requirements

**What to exclude (property has NO constraints):**
- Simple strings without format/pattern
- Generic integers/numbers without bounds
- Fields that are just descriptive text
- Fields without any validation rules

**Output Format:**
Return ONLY valid JSON (no markdown):

{
  "constrained_properties": [
    "field.path.one",
    "field.path.two"
  ]
}

**Important:**
- Only include properties WITH constraints
- Do NOT include properties without constraints
- Property paths must match exactly as shown in attributes list
- Return empty array if no constraints found
"""


RESPONSE_PROPERTY_CONSTRAINTS_VALIDATION_USER_PROMPT = """Please analyze the following schema and its attributes. For each attribute, determine if it has non-trivial constraints beyond basic type validation.

Schema: {schema}
Attributes:
{attributes}

Return a JSON object with "constraints" field mapping each attribute name to true (has non-trivial constraints) or false (only basic type).
"""

RESPONSE_PROPERTY_CONSTRAINTS_VALIDATION_USER_PROMPT_V2 = """Analyze the following schema and identify which attributes have validation constraints.

Schema: {schema}

Attributes:
{attributes}

Return a JSON object with "constrained_properties" array containing ONLY the property paths that have validation constraints.
"""
