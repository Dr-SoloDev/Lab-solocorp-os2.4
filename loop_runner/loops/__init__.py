from .daily_brief import DailyBriefLoop
from .subscription_audit import SubscriptionAuditLoop
from .brain_auto_commit import BrainAutoCommitLoop
from .pipeline_executor import PipelineExecutorLoop
from .media_daily import MediaDailyLoop

ALL_LOOPS = [DailyBriefLoop(), SubscriptionAuditLoop(), BrainAutoCommitLoop(),
             PipelineExecutorLoop(), MediaDailyLoop()]
