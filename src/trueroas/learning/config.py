class _LearningSettings:
    def __init__(self) -> None:
        self.enabled: bool = True
        self.auto_tune: bool = True
        self.min_confidence: float = 0.75
        self.learning_enabled: bool = True  # attribute expected by main.py


learning_settings: _LearningSettings = _LearningSettings()
