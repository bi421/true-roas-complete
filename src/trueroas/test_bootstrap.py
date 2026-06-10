#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.

import pytest
from trueroas.learning.bootstrap import PolicyBootstrapper


def test_generate_initial_config_valid() -> None:
    # 25% margin -> 4.0 BE ROAS
    config = PolicyBootstrapper.generate_initial_config(0.25)
    assert config["break_even_roas"] == 4.0
    assert config["scale_threshold"] == 5.0
    assert config["pause_threshold"] == 3.6


def test_generate_initial_config_boundaries() -> None:
    with pytest.raises(ValueError):
        PolicyBootstrapper.generate_initial_config(0.0)
    with pytest.raises(ValueError):
        PolicyBootstrapper.generate_initial_config(1.0)
