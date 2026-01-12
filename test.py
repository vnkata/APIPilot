from api_testing.inputs import RandomGeneratorFactory


def test_random_input_generator_next_value():
    gen = RandomGeneratorFactory.create(
        "RandomCreditCardGenerator"
        # ,mode ="country_code"
        ,card_type="mastercard"
    )

    value = gen.next_value()
    print("Generated value:", value)


test_random_input_generator_next_value()

