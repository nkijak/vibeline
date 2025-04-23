# tests/triggers/test_cron_trigger.py
import pytest
from datetime import datetime, timedelta, timezone
from freezegun import freeze_time

from pipeline_framework.triggers import CronTrigger, TriggerRunInfo

# Use UTC for consistency in tests
NOW = datetime(2023, 10, 27, 10, 0, 0, tzinfo=timezone.utc)
NOW_PLUS_59_SEC = NOW + timedelta(seconds=59)
NOW_PLUS_1_MIN = NOW + timedelta(minutes=1)
NOW_PLUS_2_MIN = NOW + timedelta(minutes=2)

@freeze_time(NOW) # Freeze time for predictable croniter initialization
def test_cron_trigger_init_valid():
    trigger = CronTrigger("cron1", "pipe1", "* * * * *")
    assert trigger.trigger_id == "cron1"
    assert trigger.pipeline_name == "pipe1"
    # assert trigger.cron_expression == "* * * * *"
    # Check that last fire time is initialized correctly (previous minute)
    assert trigger.last_scheduled_fire_time == datetime(2023, 10, 27, 9, 59, 0, tzinfo=timezone.utc)

def test_cron_trigger_init_invalid_cron():
    with pytest.raises(ValueError, match="Invalid cron expression"):
        CronTrigger("cron_bad", "pipe_bad", "invalid cron string")

@freeze_time(NOW) # Initial time
def test_cron_trigger_check_not_met():
    trigger = CronTrigger("cron_nm", "pipe_nm", "* * * * *") # Every minute
    # Time hasn't advanced to the next minute yet
    with freeze_time(NOW_PLUS_59_SEC):
        assert trigger.check() is None

@freeze_time(NOW) # Initial time
def test_cron_trigger_check_met():
    trigger = CronTrigger("cron_m", "pipe_m", "* * * * *") # Every minute
    # Advance time to exactly the next minute
    with freeze_time(NOW_PLUS_1_MIN):
        run_info = trigger.check()
        assert isinstance(run_info, TriggerRunInfo)
        assert run_info.pipeline_name == "pipe_m"
        assert run_info.trigger_id == "cron_m"
        assert "scheduled_fire_time_utc" in run_info.parameters
        # Ensure the fire time corresponds to the *start* of the minute
        assert run_info.parameters["scheduled_fire_time_utc"] == NOW_PLUS_1_MIN.isoformat()
        # Check that internal state updated
        assert trigger.last_scheduled_fire_time == NOW_PLUS_1_MIN

@freeze_time(NOW) # Initial time
def test_cron_trigger_check_met_multiple_times():
    trigger = CronTrigger("cron_multi", "pipe_multi", "* * * * *") # Every minute

    # 1. First trigger
    with freeze_time(NOW_PLUS_1_MIN):
        run_info1 = trigger.check()
        assert run_info1 is not None
        assert trigger.last_scheduled_fire_time == NOW_PLUS_1_MIN

    # 2. Check immediately after - should not trigger again
    with freeze_time(NOW_PLUS_1_MIN + timedelta(seconds=1)):
         assert trigger.check() is None

    # 3. Advance to the next minute
    with freeze_time(NOW_PLUS_2_MIN):
        run_info2 = trigger.check()
        assert run_info2 is not None
        assert run_info2.parameters["scheduled_fire_time_utc"] == NOW_PLUS_2_MIN.isoformat()
        assert trigger.last_scheduled_fire_time == NOW_PLUS_2_MIN

@freeze_time(NOW)
def test_cron_trigger_get_parameters():
     trigger = CronTrigger("cron_p", "pipe_p", "0 * * * *") # Hourly
     params = trigger.get_run_parameters(fire_time=NOW_PLUS_1_MIN)
     assert params["trigger_id"] == "cron_p"
     assert params["scheduled_fire_time_utc"] == NOW_PLUS_1_MIN.isoformat()

