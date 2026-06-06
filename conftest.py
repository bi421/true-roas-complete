#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.

import os
import builtins
import random
import sys
from pathlib import Path

from hypothesis import settings, HealthCheck

builtins.random = random
builtins.true_roas = 0.0
builtins.post_mean = 0.0
builtins.prior_var = 1.0

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
for path in (ROOT, SRC):
    path_text = str(path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)

# Define the 'ci' profile: more examples, no deadlines for slower environments
settings.register_profile("ci", max_examples=1000, deadline=None, suppress_health_check=[HealthCheck.too_slow])

# Define a 'dev' profile for faster local runs
settings.register_profile("dev", max_examples=50, deadline=500)

# Default to 'dev' unless specified via environment variable
# This also allows the --hypothesis-profile flag to work
settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "dev"))

try:
    from src.trueroas.core.database import Base, engine
    from src.trueroas.core import subscriptions  # noqa: F401

    Base.metadata.create_all(bind=engine)
except Exception:
    pass
