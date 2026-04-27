"""fixplan_v3 sub-fix 1F — cron workers.

Three entry points sharing one binary (per fixplan_v3 §0.7.5):

  * `cron/reverify_periodic.py`     — periodic norm freshness checks.
  * `cron/cascade_consumer.py`       — consumes the re-verify queue from
                                       on_history_row_inserted + on_periodic_tick.
  * `cron/state_flip_notifier.py`    — DI → IE / VL → V notifications.

Deployed to Railway (staging + production); local docker stack has no cron
workers (per `docs/orchestration/orchestration.md` env matrix).
"""
