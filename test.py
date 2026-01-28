from api_testing.inputs import RandomGeneratorFactory


def test_random_input_generator_next_value():
    gen = RandomGeneratorFactory.create(
        "RandomTextGenerator"
        ,mode ="word"
        # ,card_type="mastercard"
    )

    value = gen.next_fuzz_value()
    print("Generated value:", value)


test_random_input_generator_next_value()

