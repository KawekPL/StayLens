"""Reject destructive or out-of-scope changes in the ordinary CI deployment."""

import json
import sys


def check(plan):
    for resource in plan.get("resource_changes", []):
        if resource["mode"] == "data":
            continue
        if resource["address"] != "azurerm_container_app.staylens":
            raise ValueError("Deployment attempted to change a resource outside StayLens")
        if "delete" in resource["change"]["actions"]:
            raise ValueError("Destructive Terraform plan requires a separate reviewed migration")
        after = resource["change"]["after"]
        if after["name"] != "staylens" or not after["resource_group_name"].startswith(
            "rg-staylens-"
        ):
            raise ValueError("Unexpected deployment target")
        template = after["template"][0]
        if template["min_replicas"] != 0 or template["max_replicas"] != 1:
            raise ValueError("Student cost guardrails changed")
        container = template["container"][0]
        if container["cpu"] > 0.5 or container["memory"] != "1Gi":
            raise ValueError("Container resource budget changed")
    print("Plan allowed: StayLens only, no deletions, scale 0–1")


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8-sig") as source:
        check(json.load(source))
