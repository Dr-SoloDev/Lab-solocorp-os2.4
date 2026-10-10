from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from .state import last_run, record
from .verdict_log import append_verdict, infer_verdict


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
            append_verdict(self.loop_id, "NOT_DUE")  # per-gate heartbeat
            return None
        try:
            result = self.run()
            record(self.loop_id, result, success=True)
            append_verdict(self.loop_id, infer_verdict(result), result or "")
            return result
        except Exception as e:
            record(self.loop_id, str(e), success=False)
            append_verdict(self.loop_id, "FAIL", f"{type(e).__name__}: {e}")
            raise
