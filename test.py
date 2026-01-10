


from api_testing.inputs import RandomGeneratorFactory


factory = RandomGeneratorFactory()
generator = factory.create("RandomIdentityGenerator", field="email", seed=10000)

print(generator.next_value())