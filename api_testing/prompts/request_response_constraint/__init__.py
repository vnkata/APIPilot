import time
import uuid
from api_testing.prompts.request_response_constraint.schema import Verdict
from api_testing.utils.log import logger


class RequestResponseConstraint:
    # SYSTEM_PROMPT = """
    # Given a list of parameters and an API response schema, It's your responsibility to check how each parameter affects the API response schema.
    # Determines how a property is affected by a query parameter or how a query parameter affects a response schema.
    # Some cases can help determine a corresponding attribute:
    # - If the input parameter is null or omitted, the default value defined for the query parameter will be used (if a default is specified).
    # - The input parameter is used for filtering, and there is a corresponding attribute that reflects the real value (result of the filter); but this attribute must be in the same object as the input parameter.
    # - The constraint (min, max, format, domain value is one in of,... ) of input parameters correspond to the constraints of property. Eg: input.limit in (1,2,3) and input.limit = response.limit then response.limit in (1,2,3).
    # - The input parameter and the corresponding attribute maintain the same semantic meaning regarding their values.
    # Eg:
    #     - ((input.limit or default value of input.limit)  >= sizeOf(return)) and sizeOf(return) >= 0 and sizeOf(return) <= 100
    #     - input.year == yearOfDay(return.date) and input.year >= 1970
    #     ....
    #     Returns a list of parameters, their reflection property and brief description about the reflection in "constraint" properties in json object
    #     {
    #         "constraint": [
    #             {parameter: "limit", description: input.limit >= sizeOf(return) and input.limit >= 0, property: null },
    #             {parameter: "year ", description: input.year == yearOfDay(return.date), property: date }
    #         ]
    #     }
    # """
    SYSTEM_PROMPT = """
    Given a list of parameters and an API response schema, It is your responsibility to verify how each input parameter influences the API response schema.
    Determines how a property is affected by a query parameter or how a query parameter affects a response schema.
    Some cases can help determine a corresponding attribute:
    - If the input parameter is null or omitted, the default value defined for the query parameter will be used (if a default is specified).
    - The input parameter is used for filtering, and its corresponding attribute—representing the actual value after filtering—must exist within the same object as the input parameter.
    - Constraints on input parameters—such as min, max, format, or allowed values (e.g., enum) - should align with the constraints of the corresponding response properties .For example, if input.limit ∈ (1, 2, 3) and input.limit = response.limit, then response.limit must also satisfy response.limit ∈ (1, 2, 3).
    - The input parameter and the corresponding response attribute should represent the same concept and interpret their values consistently.
    Eg:
        - ((input.limit or 20)  >= sizeOf(return)) and sizeOf(return) >= 0 and sizeOf(return) <= 100 # 20 is default value of input.limit
        - ((input.month or 1) = monthOfDay(return.date)) and (input.month >= 1 and input.month <=12)
        ....
        Returns a list of objects containing parameter, brief description, and property fields, representing how constraints are reflected in the JSON object. Each parameter must be one or more input parameters, and each property must be one or more fields from the response schema.
        {
            "constraint": [
                {parameter: "limit", description: input.limit >= sizeOf(return) and input.limit >= 0, property: null },
                {parameter": "sort_field, sort_by", description: "isSortedBy(input.sort_field, sort_by, return), input.sort_by in (asc,desc)", property: "id"},
                {parameter: "year", description: input.year == yearOfDay(return.date) and input.year > 1970, property: date }
            ]
        }
    """
    PROMPT = """
        Endpoint: {endpoint}
        Here is list parameters and response schema
        *Parameters:*
        {parameters}
        *Response schema:*
        {response}
        *Additional Information*: 
        {additional_information}
    """

    def __init__(self, llm, endpoint, parameters, response, extras):
        self.llm = llm
        self.parameters = parameters
        self.response = response
        self.endpoint = endpoint
        self.extras = extras

    def validate(self):
        #
        for i in range(3):
            try:
                # write promt
                logger.debug(self.PROMPT.format(
                    endpoint=self.endpoint,
                    parameters=self.parameters,
                    response=self.response,
                    additional_information=self.extras
                ))
                response, _ = self.llm.generate(
                    system_prompt=self.SYSTEM_PROMPT,
                    prompt=self.PROMPT.format(
                        endpoint=self.endpoint,
                        parameters=self.parameters,
                        response=self.response,
                        additional_information=self.extras
                    ),
                    schema=Verdict
                )
                break
                #
            except Exception as e:
                time.sleep(30)
                print(str(e))
                print("retry...", i)
                pass
        return response

    def __str__(self):
        return f"Request: {self.request}, Response: {self.response}"
