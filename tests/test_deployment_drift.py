from copy import deepcopy

import pytest

from scripts.check_deployment_drift import check_plan


def example():
    before = {
        "template": [
            {
                "cooldown_period_in_seconds": 0,
                "polling_interval_in_seconds": 0,
                "container": [{"image": "frozen", "startup_probe": [{"transport": ""}]}],
            }
        ]
    }
    after = deepcopy(before)
    after["template"][0]["cooldown_period_in_seconds"] = 300
    after["template"][0]["polling_interval_in_seconds"] = 30
    after["template"][0]["container"][0]["startup_probe"][0]["transport"] = "HTTP"
    return {
        "resource_changes": [
            {
                "mode": "managed",
                "address": "azurerm_container_app.staylens",
                "change": {
                    "actions": ["update"],
                    "before": before,
                    "after": after,
                    "after_unknown": {},
                },
            }
        ]
    }


def test_only_documented_omitted_defaults_are_accepted():
    _, accepted = check_plan(example())
    assert len(accepted) == 3


@pytest.mark.parametrize("change", ["image", "cooldown", "probe", "unknown", "delete"])
def test_real_drift_or_unresolved_changes_fail(change):
    value = example()
    diff = value["resource_changes"][0]["change"]
    template = diff["after"]["template"][0]
    if change == "image":
        template["container"][0]["image"] = "changed"
    elif change == "cooldown":
        template["cooldown_period_in_seconds"] = 60
    elif change == "probe":
        template["container"][0]["startup_probe"][0]["transport"] = "TCP"
    elif change == "unknown":
        diff["after_unknown"] = {"template": True}
    else:
        diff["actions"] = ["delete", "create"]
    with pytest.raises(ValueError):
        check_plan(value)
