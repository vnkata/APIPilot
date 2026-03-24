# APITesting

## Available Baseline Tools

- **RESTifAI** (`RESTifAI`): A LLM-based REST API testing framework designed to generate reusable and executable production-ready test suites. The approach validates OpenAPI specifications through structural conformance testing and verifying business logic scenarios through functional test case generation.

- **AutoRestTest** (`AutoRestTest`): A mutation-based API testing methodology that leverages LLM-generated request values combined with reinforcement learning techniques to maximize the detection of unique HTTP 500 server errors and successful 2xx responses across distinct API operations.  
  *Reference*: https://doi.org/10.48550/arXiv.2501.08600  
  *Repository*: https://github.com/selab-gatech/AutoRestTest/

- **LogiAgent** (`LogiAgent`): A multi-agent framework-based approach that autonomously generates ad-hoc logical test scenarios designed to validate the semantic business logic constraints of REST API implementations.  
  *Reference*: https://doi.org/10.48550/arXiv.2503.15079  
  *Repository*: https://anonymous.4open.science/r/LogiAgent-5055/README.md

## Evaluation Dataset: API Services

The experimental evaluation encompasses five diverse REST API services, selected to represent varying complexity levels and domain-specific characteristics:

#### Locally Deployed Services

- **genome-nexus**: A bioinformatics service providing genomic variant annotation capabilities  
  *Source*: https://github.com/genome-nexus/genome-nexus
- **language-tool**: A natural language processing service offering grammar and linguistic analysis  
  *Source*: https://github.com/languagetool-org/languagetool  
- **rest-countries**: A geographical information service providing country-specific metadata  
  *Source*: https://github.com/apilayer/restcountries

#### Remotely Hosted Services

- **fdic**: Federal Deposit Insurance Corporation banking institution data service  
  *Documentation*: https://api.fdic.gov/banks/docs/
- **ohsome**: OpenStreetMap geospatial data analysis and statistics service  
  *Documentation*: https://docs.ohsome.org/ohsome-api/v1/

**Happy testing! 🚀**

