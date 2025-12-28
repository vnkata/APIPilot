import os
from api_testing.dataset.specification_parser import SpecificationParser
from api_testing.configuration.configuration_parser import ConfigurationParser

def test_configuration_parser_debug_log():
    path = "C:\\Users\\Admin\\Desktop\\NCKH\\API-Testing\\datasets\\stripe.json"


    print(f"[*] Initializing SpecificationParser for: {os.path.basename(path)}")

    spec_parser = SpecificationParser(spec_path=path)
    spec_parser.parse_specification() 
    
    print(f"[*] Successfully parsed {len(spec_parser.operations)} operations.")

    config_parser = ConfigurationParser(spec_parser=spec_parser)
    
    config_parser.parse()
    debug_file = "test_debug_config.json"
    config_parser.export_debug_log(debug_file)

    print("-" * 40)
    print(f"[SUCCESS] Test complete.")
    print(f"Configurations generated: {len(config_parser.configurations)}")
    print(f"GPT Tasks collected: {len(config_parser.gpt_tasks)}")
    print(f"Results saved to: {os.path.abspath(debug_file)}")

if __name__ == "__main__":
    test_configuration_parser_debug_log()