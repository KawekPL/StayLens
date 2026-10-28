"""Check strict Terraform drift plus documented Azure defaults omitted by GET.

AzureRM 4.81 reads missing HTTP scheme as '' and missing KEDA defaults as 0.
Keep those desired settings in Terraform (do not ignore them on later PUTs).
Allow only these five exact readback differences; independently check ARM.
"""

import argparse
import json
from pathlib import Path

DEFAULT_DIFFS = {
    ("template", 0, "cooldown_period_in_seconds"): (0, 300),
    ("template", 0, "polling_interval_in_seconds"): (0, 30),
    **{
        ("template", 0, "container", 0, kind + "_probe", 0, "transport"): ("", "HTTP")
        for kind in ["startup", "readiness", "liveness"]
    },
}


def differences(before, after, path=()):
    if isinstance(before, dict) and isinstance(after, dict):
        for key in sorted(set(before) | set(after)):
            yield from differences(before.get(key), after.get(key), (*path, key))
    elif isinstance(before, list) and isinstance(after, list) and len(before) == len(after):
        for index, (left, right) in enumerate(zip(before, after, strict=True)):
            yield from differences(left, right, (*path, index))
    elif before != after:
        yield path, before, after


def check_plan(plan):
    resources = [r for r in plan.get("resource_changes", []) if r["mode"] != "data"]
    if len(resources) != 1 or resources[0]["address"] != "azurerm_container_app.staylens":
        raise ValueError("Unexpected resources in convergence plan")
    change = resources[0]["change"]
    if change["actions"] not in [["no-op"], ["update"]] or change.get("after_unknown"):
        raise ValueError("Unexpected or unresolved deployment change")
    accepted = []
    for path, before, after in differences(change["before"], change["after"]):
        if DEFAULT_DIFFS.get(path) != (before, after):
            raise ValueError(f"Unexpected infrastructure drift at {path}: {before!r} -> {after!r}")
        accepted.append(".".join(map(str, path)))
    return change["after"], accepted


def default(value, fallback):
    return fallback if value is None else value


def check(plan, observed, digest):
    desired, accepted = check_plan(plan)
    properties = observed["properties"]
    configuration = properties["configuration"]
    template = properties["template"]
    assert observed["name"] == "staylens"
    assert properties["provisioningState"] == "Succeeded"
    assert configuration["activeRevisionsMode"] == "Single"
    assert (
        properties["managedEnvironmentId"].lower()
        == desired["container_app_environment_id"].lower()
    )
    ingress = configuration["ingress"]
    assert ingress["external"] is True and ingress["targetPort"] == 8080
    assert ingress["transport"].lower() == "http" and not ingress.get("allowInsecure", False)
    assert len(template["containers"]) == 1
    container = template["containers"][0]
    expected_image = desired["template"][0]["container"][0]["image"]
    assert expected_image.endswith("/staylens@" + digest)
    assert container["image"] == expected_image
    assert container["resources"]["cpu"] == 0.5 and container["resources"]["memory"] == "1Gi"
    scale = template["scale"]
    assert default(scale.get("minReplicas"), 0) == 0 and scale["maxReplicas"] == 1
    assert default(scale.get("pollingInterval"), 30) == 30
    assert default(scale.get("cooldownPeriod"), 300) == 300
    assert len(scale["rules"]) == 1
    assert scale["rules"][0]["http"]["metadata"]["concurrentRequests"] == "10"
    probes = {probe["type"]: probe for probe in container["probes"]}
    assert len(container["probes"]) == 3 and set(probes) == {"Startup", "Liveness", "Readiness"}
    for kind, period, failures in [("Startup", 5, 24), ("Readiness", 10, 3), ("Liveness", 30, 3)]:
        probe = probes[kind]
        http = probe["httpGet"]
        assert default(http.get("scheme"), "HTTP") == "HTTP" and not probe.get("tcpSocket")
        assert http["port"] == 8080 and http["path"] == "/health"
        assert probe["periodSeconds"] == period and probe["failureThreshold"] == failures
        assert probe["timeoutSeconds"] == 3
    registry = desired["registry"][0]
    assert configuration["registries"] == [
        {"identity": registry["identity"], "server": registry["server"]}
    ]
    assert registry["identity"].lower() in {
        key.lower() for key in observed["identity"]["userAssignedIdentities"]
    }
    return {
        "effective_configuration_matches": True,
        "terraform_exact_no_changes": not accepted,
        "known_default_readback_differences": accepted,
        "observed_image": expected_image,
        "scale": {"min": 0, "max": 1},
        "http_health_probes": 3,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan")
    parser.add_argument("observed")
    parser.add_argument("digest")
    parser.add_argument("--output")
    args = parser.parse_args()
    result = check(
        json.loads(Path(args.plan).read_text(encoding="utf-8-sig")),
        json.loads(Path(args.observed).read_text(encoding="utf-8-sig")),
        args.digest,
    )
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    print(rendered)
