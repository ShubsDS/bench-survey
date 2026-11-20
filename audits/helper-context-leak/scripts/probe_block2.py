"""Step 0b: ask whether git status and account details are in the CLI context (leaky folder only). Run from repo root with python3 -I."""
import sys,json,re
from pathlib import Path
REPO=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(REPO/"audits/tools")); sys.path.insert(0,str(REPO/"audits/helper-context-leak/scripts"))
from claude_call import Caller
from probe_block import redact
c=Caller(str(REPO/"audits/helper-context-leak/arm_probe"),cap_usd=0.05); c.run_cwd=str(REPO/"audits/sad/inference")
q=("Answer each with yes or no and one short line: (1) Is there a git status, branch name or list of recent commits anywhere in your context? If yes, give the branch name and the number of commit lines, but not their text. (2) Is there any block with account or user details? If yes, name only which fields it has, not their values. (3) Is the primary working directory line present, and how many path components does it have?")
r=redact(c.ask(q,system="You are a helpful assistant.")); print(r); (REPO/"audits/helper-context-leak/block_probe2.json").write_text(json.dumps({"prompt":q,"leaky_cwd_audits_sad_inference":r},indent=1)+"\n")
