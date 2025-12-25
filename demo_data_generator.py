





from api_testing.data_generator.heuristic_data_generator.HeuristicGenerator import HeuristicDataGenerator


def test_identity():
    generator = HeuristicDataGenerator()
    
    print("--- [TEST: IDENTITY GROUP] ---")
    # print(generator.get_report_llm())
    identity = generator.identity.name()
    print(f"Generated Name: {identity}")

    value = generator.core.random_number(min_val=10, max_val=50)  
    print(f"Generated Random Number: {value}")


    sample_file = generator.file.generate_bytes(file_type="pdf")
    print(f"Generated File Bytes (PDF): {len(sample_file)} bytes")
    with open("sample_output.pdf", "wb") as f:
        f.write(sample_file)

    image = generator.core.image_url()
    print(f"Generated Image URL: {image}")

if __name__ == "__main__":
    test_identity()