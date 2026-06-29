from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from .state import last_run, record


class Loop(ABC):
    loop_id: str
    interval: timedelta
    trust_level: int  # 1=report, 2=assist, 3=advise, 4=auto-execute
    model_hint: str = "glm-5.2"  # model alias from Hermes config; cron sub-agent default

    def should_run(self) -> bool:
        lr = last_run(self.loop_id)
        return lr is None or datetime.now() - lr >= self.interval

    @abstractmethod
    def run(self) -> str:
        ...

    def execute(self) -> str | None:
        if not self.should_run():
            return None
        try:
            result = self.run()
            record(self.loop_id, result, success=True)
            return result
        except Exception as e:
            record(self.loop_id, str(e), success=False)
            raise
