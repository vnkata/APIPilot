REQUEST_RESPONSE_VALIDATION_SYSTEM_PROMPT = """You are an expert at analyzing API operations and identifying constraint relationships between request parameters and response properties.

**CRITICAL: What TO Mark as Having Constraints**

Only mark True for request-response pairs that have a **verifiable, programmatic relationship**:

1. **Filtering Constraints**:
   - Request parameter filters response data (e.g., `filter[status]=active` → only active items in response)
   - Query parameter affects which response properties are returned

2. **Sorting/Ordering Constraints**:
   - Request parameter controls response order (e.g., `sort=name` → response sorted by name field)

3. **Pagination Constraints**:
   - Request parameter limits response size (e.g., `limit=10` → max 10 items in response)
   - Offset/page parameter affects which subset is returned

4. **Projection/Field Selection**:
   - Request parameter controls which fields appear in response (e.g., `fields=id,name` → only those fields)

5. **Transformation Constraints**:
   - Request parameter transforms response data format (e.g., `format=summary` → condensed response)

6. **Validation Constraints**:
   - Request parameter value must match or relate to response property value
   - ID in request must equal ID in response

**What NOT to Mark**:
- Generic relationships without specific constraint logic
- Unrelated request-response pairs
- Implicit relationships without verification rules

**Output Format:**
Return ONLY valid JSON without markdown formatting:

{
  "constraints": {
    "request_param_name": {
      "response_property_path": true/false
    }
  }
}

**Important:**
- Return True ONLY if there's a clear, testable constraint relationship
- Return False for unrelated or unclear relationships
- Use lowercase `true` and `false` (JSON boolean format)
"""

REQUEST_RESPONSE_VALIDATION_USER_PROMPT = """Analyze the following API operation and determine which request parameters have constraint relationships with response properties.

Operation: {operation_name}
Method: {method}
Path: {path}

Request Parameters:
{request_params}

Response Properties:
{response_properties}

For each request parameter, evaluate if it has a constraint relationship with any response property. Return a nested JSON object mapping request parameters to response properties with boolean indicators.
"""

REQUEST_RESPONSE_VALIDATION_SYSTEM_PROMPT_V2 = """You are an expert at analyzing API operations and identifying constraint relationships between request parameters and response properties.

**Your Task:**
Examine the API operation and return ONLY the request-response pairs that have verifiable constraint relationships.

**What to include (pair HAS constraints):**

1. **Filtering Constraints**: Request parameter filters response data
   - Example: `filter[status]=active` → only items with `status: "active"` in response

2. **Sorting/Ordering**: Request parameter controls response order
   - Example: `sort=name` → response sorted by `name` field

3. **Pagination**: Request parameter limits/controls response subset
   - Example: `limit=10` → max 10 items in response

4. **Projection/Field Selection**: Request controls which fields appear
   - Example: `fields=id,name` → only those fields in response

5. **Echo/Validation**: Request parameter value must match response value
   - Example: `userId` in path → `user.id` in response must match

6. **Transformation**: Request parameter transforms response format
   - Example: `format=summary` → condensed response structure

**What to exclude:**
- Unrelated request-response pairs
- Generic parameters without specific constraint logic

**Output Format:**
Return ONLY valid JSON (no markdown):

{
  "request_response_pairs": [
    {
      "request_param": "request_param_name_1",
      "response_properties": ["response.property.path1", "response.property.path2"]
    },
    {
      "request_param": "another_request_param_2",
      "response_properties": ["response.property.path1", "response.property.path2"]
    }
  ]
}

**Important:**
- Only include pairs WITH constraint relationships
- One request param can constrain multiple response properties
- Property paths must match exactly as shown in the lists
- Return empty array if no constraint pairs found
"""

REQUEST_RESPONSE_VALIDATION_USER_PROMPT_V2 = """Analyze the following API operation and identify request-response constraint pairs.

Operation: {operation_name}
Method: {method}
Path: {path}

Request Parameters:
{request_params}

Response Properties:
{response_properties}

Return a JSON object with "request_response_pairs" array containing ONLY the pairs that have constraint relationships.
"""
