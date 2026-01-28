import os

from dotenv import load_dotenv
from api_testing.dataset.specification_parser import SpecificationParser
from api_testing.configuration.configuration_parser import ConfigurationParser
from api_testing.models.llms.AzureOpenAIModel import AzureOpenAIModel
load_dotenv()
def test_configuration_parser_debug_log(llm: AzureOpenAIModel):
    file_name = "Genome-nexus.json"
    path = f"C:\\Users\\Admin\\Desktop\\NCKH\\API-Testing\\datasets\\{file_name}"
    name = os.path.splitext(file_name)[0]
    print(f"[*] Initializing SpecificationParser for: {os.path.basename(path)}")

    spec_parser = SpecificationParser(spec_path=path)
    spec_parser.parse_specification() 
    
    print(f"[*] Successfully parsed {len(spec_parser.operations)} operations.")

    config_parser = ConfigurationParser(spec_parser=spec_parser, model=llm, cache_dir=f"./.cache/{name}")

    config_parser.parse()
    debug_file = "test_debug_config.json"
    config_parser.export_debug_log(debug_file)

    print("-" * 40)
    print(f"[SUCCESS] Test complete.")
    print(f"Configurations generated: {len(config_parser.configurations)}")
    # print(f"GPT Tasks collected: {len(config_parser.gpt_tasks)}")
    print(f"Results saved to: {os.path.abspath(debug_file)}")

if __name__ == "__main__":
    llm = AzureOpenAIModel(
    model="gpt-4.1",
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
    temperature=0.7,
)
    test_configuration_parser_debug_log(llm = llm)