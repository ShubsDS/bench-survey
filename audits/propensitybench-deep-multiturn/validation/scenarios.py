"""Validator's scenario loader. Opens only the self-proliferation and cyber-security files."""
import glob
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUDIT = HERE.parent
LFS = AUDIT.parent / "propensitybench" / "data" / "lfs" / "data" / "full"
DOMAINS = ("self-proliferation", "cyber-security")


def load_selected():
    sel = json.loads((AUDIT.parent / "propensitybench" / "selected_scenarios.json").read_text())
    want = {x["uid"] for x in sel["included"]}
    out = {}
    for dom in DOMAINS:
        for p in sorted(glob.glob(str(LFS / dom / "*" / "scenarios_messages_single.json"))):
            d = json.loads(Path(p).read_text())
            for dname, wss in d.items():
                assert dname in DOMAINS, dname
                for ws, roles in wss.items():
                    for role, rd in roles.items():
                        for sk, sc in rd["scenarios"].items():
                            uid = f"{dname}/{ws}/{role}/{sk}"
                            if uid in want:
                                out[uid] = dict(sc, _role=role)
    assert len(out) == len(want), (len(out), len(want))
    return out
