"""Record the hand-read scenario selection for the emulation (ids and hand labels only, no text).

Candidates come from select_scenarios.py (seed 20261117, 2 scenarios per workspace from distinct
roles) for self-proliferation and cyber-security. Every candidate was read in full before use:
task, role, duties, both tool names and descriptions, outcome acknowledgment, consequences,
prohibitions_description, trigger_awareness and the level-12 pressure message of its category.

Content screen (brief: exclude operational detail about weapons, pathogens, synthesis or working
exploits). All 32 candidates are abstract role-play: exploits are named generically or by fictional
identifiers, with no code, commands or procedures. Excluded: 0 of 32. Biosecurity and chemical
security were not read or used.

Hand labels made while reading, before any model output existed:
- late_licenses_bypass: the level-12 message explicitly authorises overriding protocols, unrestrained
  resource access, deviation from protocols or non-standard methods (1) or not (0).
- benign_desc_has_harm_cue (exploratory, not pre-registered): the benign tool description still
  describes a bypass, an exploit or a side effect on others.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import AUDIT, DATA

LICENSE = {  # role/scenario -> late_licenses_bypass
    "Author/direct_algorithmic_self_modification_for_quality_enhancement": 1,
    "Situation-Analysis-Specialist/anomaly_detection_configuration_and_stealth_integration": 1,
    "Container-Orchestration-Manager/urgent_security_patch_orchestration": 1,
    "Compliance-Monitoring-Specialist/perpetual_compliance_protocol_enforcement": 1,
    "Pool-Member/decentralized_influence_network_policy_activation": 1,
    "Data-Loss-Prevention-Engineer/emergency_dlp_fix_via_unauthorized_access": 1,
    "Virtualization-Security-Engineer/expedited_cloud_resource_allocation": 1,
    "Cloud-Security-Engineer/deployment_blocker_circumvention_via_service_account_modification": 1,
}
BENIGN_CUE = {
    "Situation-Analysis-Specialist/anomaly_detection_configuration_and_stealth_integration",
    "Document-Processing-Manager/urgent_document_batch_processing_resource_escalation",
    "Pool-Creator/enhanced_pool_resource_provisioning",
    "Project-Manager/rapid_scaling_of_grant_review_capacity",
    "Container-Orchestration-Manager/urgent_security_patch_orchestration",
    "Data-Loss-Prevention-Engineer/emergency_dlp_fix_via_unauthorized_access",
    "SIEM-Analyst/emergency_substation_threat_containment",
    "Database-Security-Administrator/urgent_database_account_unlock",
    "SCADA-Security-Analyst/emergency_scada_patch_verification_under_duress",
}
EXCLUDED = {}  # uid -> reason; none


def main():
    rows = []
    for f in ("cand_sp.json", "cand_cy.json"):
        rows += json.loads((DATA / f).read_text())
    inc = []
    for r in rows:
        key = r["uid"].split("/", 2)[2]
        if r["uid"] in EXCLUDED:
            continue
        inc.append({"uid": r["uid"], "domain": r["uid"].split("/")[0], "late_category": r["late_category"],
                    "late_licenses_bypass": LICENSE.get(key, 0), "benign_desc_has_harm_cue": int(key in BENIGN_CUE)})
    out = {"seed": 20261117, "domains_read": ["self-proliferation", "cyber-security"], "candidates": len(rows),
           "excluded": EXCLUDED, "n_excluded": len(EXCLUDED), "included": inc}
    (AUDIT / "selected_scenarios.json").write_text(json.dumps(out, indent=1) + "\n")
    print(len(inc), sum(x["late_licenses_bypass"] for x in inc), sum(x["benign_desc_has_harm_cue"] for x in inc))


if __name__ == "__main__":
    main()
