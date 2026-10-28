from copy import deepcopy

import pytest

from scripts.check_deployment_plan import check


def plan():
    return {
        "resource_changes": [
            {
                "mode": "managed",
                "address": "azurerm_container_app.staylens",
                "change": {
                    "actions": ["update"],
                    "after": {
                        "name": "staylens",
                        "resource_group_name": "rg-staylens-123",
                        "template": [
                            {
                                "min_replicas": 0,
                                "max_replicas": 1,
                                "container": [{"cpu": 0.5, "memory": "1Gi"}],
                            }
                        ],
                    },
                },
            }
        ]
    }


def test_accept_non_destructive_staylens_deployment():
    check(plan())


@pytest.mark.parametrize("kind", ["delete", "other_resource", "more_replicas", "other_app"])
def test_reject_destructive_or_out_of_scope_deployment(kind):
    value = deepcopy(plan())
    resource = value["resource_changes"][0]
    if kind == "delete":
        resource["change"]["actions"] = ["delete", "create"]
    elif kind == "other_resource":
        resource["address"] = "azurerm_container_app.supportrouter"
    elif kind == "more_replicas":
        resource["change"]["after"]["template"][0]["max_replicas"] = 2
    else:
        resource["change"]["after"]["name"] = "supportrouter-pl"
    with pytest.raises(ValueError):
        check(value)
