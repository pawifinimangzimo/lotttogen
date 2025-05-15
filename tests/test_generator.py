def test_set_generation(sample_config, sample_data):
    analyzer = LotteryAnalyzer(sample_data, sample_config)
    generator = NumberSetGenerator(analyzer)
    sets = generator.generate_sets()
    assert len(sets) == sample_config.output.sets_to_generate
    for numbers, _ in sets:
        assert len(numbers) == sample_config.strategy.numbers_to_select