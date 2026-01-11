from api_testing.inputs import RandomGeneratorFactory


def test_random_input_generator_next_value():
    gen = RandomGeneratorFactory.create(
        "RandomInputGenerator",
        values=["PENDING", "APPROVED", "REJECTED"],
        count=1,
        seed=42
    )

    value = gen.next_fuzz_value(strategy="empty")
    print("Generated value:", value)


test_random_input_generator_next_value()

