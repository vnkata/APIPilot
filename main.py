

from api_testing.inputs import RandomGeneratorFactory


def main():
    factory = RandomGeneratorFactory()
    descriptions = factory.gen_description()
    for name, desc in descriptions.items():
        print(f"{name}:\n{desc}\n{'-'*40}")

if __name__ == "__main__":
    main()