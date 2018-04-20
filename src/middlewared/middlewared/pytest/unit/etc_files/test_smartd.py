import asyncio
import subprocess
import textwrap

from mock import call, Mock, patch
import pytest

from middlewared.etc_files.smartd import (
    ensure_smart_enabled, annotate_disk_for_smart, get_smartd_schedule_piece, get_smartd_config
)


@pytest.mark.asyncio
async def test__ensure_smart_enabled__smart_error():
    with patch("middlewared.etc_files.smartd.run") as run:
        run.return_value = asyncio.Future()
        run.return_value.set_result(Mock(stdout="S.M.A.R.T. Error"))

        assert await ensure_smart_enabled(["/dev/ada0"]) is False

        run.assert_called_once()


@pytest.mark.asyncio
async def test__ensure_smart_enabled__smart_enabled():
    with patch("middlewared.etc_files.smartd.run") as run:
        run.return_value = asyncio.Future()
        run.return_value.set_result(Mock(stdout="SMART   Enabled"))

        assert await ensure_smart_enabled(["/dev/ada0"])

        run.assert_called_once()


@pytest.mark.asyncio
async def test__ensure_smart_enabled__smart_was_disabled():
    with patch("middlewared.etc_files.smartd.run") as run:
        run.return_value = asyncio.Future()
        run.return_value.set_result(Mock(stdout="SMART   Disabled", returncode=0))

        assert await ensure_smart_enabled(["/dev/ada0"])

        assert run.call_args_list == [
            call(["smartctl", "-i", "/dev/ada0"], check=False, stderr=subprocess.STDOUT, encoding="utf8"),
            call(["smartctl", "-s", "on", "/dev/ada0"], check=False, stderr=subprocess.STDOUT, encoding="utf8"),
        ]


@pytest.mark.asyncio
async def test__ensure_smart_enabled__enabling_smart_failed():
    with patch("middlewared.etc_files.smartd.run") as run:
        run.return_value = asyncio.Future()
        run.return_value.set_result(Mock(stdout="SMART   Disabled", returncode=1))

        assert await ensure_smart_enabled(["/dev/ada0"]) is False


@pytest.mark.asyncio
async def test__ensure_smart_enabled__handled_args_properly():
    with patch("middlewared.etc_files.smartd.run") as run:
        run.return_value = asyncio.Future()
        run.return_value.set_result(Mock(stdout="SMART   Enabled"))

        assert await ensure_smart_enabled(["/dev/ada0", "-d", "sat"])

        run.assert_called_once_with(
            ["smartctl", "-i", "/dev/ada0", "-d", "sat"], check=False, stderr=subprocess.STDOUT, encoding="utf8",
        )


@pytest.mark.asyncio
async def test__annotate_disk_for_smart__skips_zvol():
    assert await annotate_disk_for_smart({}, {"disk_name": "/dev/zvol1"}) is None


@pytest.mark.asyncio
async def test__annotate_disk_for_smart__skips_unknown_device():
    assert await annotate_disk_for_smart({"/dev/ada0": {}}, {"disk_name": "/dev/ada1"}) is None


@pytest.mark.asyncio
async def test__annotate_disk_for_smart__skips_device_without_args():
    with patch("middlewared.etc_files.smartd.get_smartctl_args") as get_smartctl_args:
        get_smartctl_args.return_value = asyncio.Future()
        get_smartctl_args.return_value.set_result(None)
        assert await annotate_disk_for_smart({"/dev/ada1": {"driver": "ata"}}, {"disk_name": "/dev/ada1"}) is None


@pytest.mark.asyncio
async def test__annotate_disk_for_smart__skips_device_with_unavailable_smart():
    with patch("middlewared.etc_files.smartd.get_smartctl_args") as get_smartctl_args:
        get_smartctl_args.return_value = asyncio.Future()
        get_smartctl_args.return_value.set_result(["/dev/ada1", "-d", "sat"])
        with patch("middlewared.etc_files.smartd.ensure_smart_enabled") as ensure_smart_enabled:
            ensure_smart_enabled.return_value = asyncio.Future()
            ensure_smart_enabled.return_value.set_result(False)
            assert await annotate_disk_for_smart({"/dev/ada1": {"driver": "ata"}}, {"disk_name": "/dev/ada1"}) is \
                None


@pytest.mark.asyncio
async def test__annotate_disk_for_smart():
    with patch("middlewared.etc_files.smartd.get_smartctl_args") as get_smartctl_args:
        get_smartctl_args.return_value = asyncio.Future()
        get_smartctl_args.return_value.set_result(["/dev/ada1", "-d", "sat"])
        with patch("middlewared.etc_files.smartd.ensure_smart_enabled") as ensure_smart_enabled:
            ensure_smart_enabled.return_value = asyncio.Future()
            ensure_smart_enabled.return_value.set_result(True)
            assert await annotate_disk_for_smart({"/dev/ada1": {"driver": "ata"}}, {"disk_name": "/dev/ada1"}) == {
                "disk_name": "/dev/ada1",
                "smartctl_args": ["/dev/ada1", "-d", "sat"],
            }


def test__get_smartd_schedule_piece__every_month():
    assert get_smartd_schedule_piece("1,2,3,4,5,6,7,8,9,10,11,12", 1, 12) == ".."


def test__get_smartd_schedule_piece__every_each_month():
    assert get_smartd_schedule_piece("*/1", 1, 12) == ".."


def test__get_smartd_schedule_piece__every_fifth_month():
    assert get_smartd_schedule_piece("*/5", 1, 12) == "(05|10)"


def test__get_smartd_schedule_piece__every_specific_month():
    assert get_smartd_schedule_piece("1,5,11", 1, 12) == "(01|05|11)"


def test__get_smartd_config():
    assert get_smartd_config({
        "smartctl_args": ["/dev/ada0", "-d", "sat"],
        "smart_powermode": "never",
        "smart_difference": 0,
        "smart_informational": 1,
        "smart_critical": 2,
        "smart_email": "",
        "smarttest_type": "S",
        "smarttest_month": "*/1",
        "smarttest_daymonth": "*/1",
        "smarttest_dayweek": "*/1",
        "smarttest_hour": "*/1",
        "disk_smartoptions": "--options",
    }) == textwrap.dedent("""\
        /dev/ada0 -d sat -n never -W 0,1,2 -m root -M exec /usr/local/www/freenasUI/tools/smart_alert.py\\
        -s S/../.././..\\
         --options""")


def test__get_smartd_config_without_schedule():
    assert get_smartd_config({
        "smartctl_args": ["/dev/ada0", "-d", "sat"],
        "smart_powermode": "never",
        "smart_difference": 0,
        "smart_informational": 1,
        "smart_critical": 2,
        "smart_email": "",
        "disk_smartoptions": "--options",
    }) == textwrap.dedent("""\
        /dev/ada0 -d sat -n never -W 0,1,2 -m root -M exec /usr/local/www/freenasUI/tools/smart_alert.py --options""")
