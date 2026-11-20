"""Attack line (b)/(d)/(g): what did the model actually see on its first call?

For every local transcript, rebuild the first request body (system + task message + the tool list
as logged) and render it with the model's own chat template (local tokenizer files, offline,
enable_thinking=False, as the server was started). Compare the token count with the prompt_tokens
the server reported for that call. Equal counts mean the server tokenised exactly this prompt.
Then check that the Policy section (restored / placebo) is present in full in the rendered prompt,
its position, and where the misaligned tool sits in the <tools> block.

Run with the audit's venv:  .venv/bin/python -I validation/v_render_prompt.py
"""
import glob
import json
import os
import sys
from pathlib import Path

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
HERE = Path(__file__).resolve().parent
AUDIT = HERE.parent
sys.path.insert(0, str(AUDIT / "scripts"))
sys.path.insert(0, str(HERE))
import harness as H  # noqa: E402  (runner only: tool schemas)
from scenarios import load_selected  # noqa: E402
from transformers import AutoTokenizer  # noqa: E402

tok = AutoTokenizer.from_pretrained(str(AUDIT / "data/models/Qwen3-8B-MLX-4bit"))
SC = load_selected()
rows = []
for p in sorted(glob.glob(str(AUDIT / "data/transcripts/openai-*.json"))):
    d = json.loads(Path(p).read_text())
    rec, hist, log = d["rec"], d["history"], d["log"]
    sc = H.swap_names(SC[rec["uid"]], True)
    tools_by = {t["function"]["name"]: t for t in H.openai_tools(sc)}
    tools = [tools_by[n] for n in log[0]["tools"]]
    msgs = [dict(m) for m in hist[:2]]
    text = tok.apply_chat_template(msgs, tools=tools, add_generation_prompt=True, tokenize=False,
                                   enable_thinking=False)
    ids = tok(text, add_special_tokens=False)["input_ids"]
    pol = None
    s = hist[0]["content"]
    if "**Policy:**" in s:
        a = s.index("**Policy:**") + len("**Policy:**\n")
        pol = s[a:s.index("\n\n**Available Tools:**", a)]
    expect = sc["policy"]["prohibitions_description"]
    trig, targ = sc["functions"]["trigger_function"]["name"], sc["functions"]["target_function"]["name"]
    ts = text.index("<tools>\n"); tb = text[ts:text.index("</tools>", ts)]
    rows.append(dict(
        arm=rec["arm"], uid=rec["uid"], rendered_tokens=len(ids),
        server_prompt_tokens=log[0]["meta"]["usage"]["prompt_tokens"],
        policy_in_rendered=(pol is not None and pol in text),
        policy_equals_prohibition=(pol == expect) if rec["arm"] == "restored" else None,
        policy_words=len(pol.split()) if pol else 0, prohibition_words=len(expect.split()),
        policy_char_offset=text.index(pol) if pol else None,
        policy_mentions_trigger_name=(trig in pol) if pol else None,
        prohibition_mentions_harmful_name=sc["functions"]["trigger_function"]["harmful_name"] in expect,
        tools_block_first=json.loads(tb[len("<tools>"):].strip().splitlines()[0])["function"]["name"],
        trigger_first_in_tools_block=tb.index(f'"name": "{trig}"') < tb.index(f'"name": "{targ}"'),
        system_before_tools=text.index(s[:200]) < ts,
    ))
(HERE / "v_render_prompt.json").write_text(json.dumps(rows, indent=1))
n = len(rows)
print("runs", n)
print("rendered == server prompt_tokens:", sum(r["rendered_tokens"] == r["server_prompt_tokens"] for r in rows), "/", n,
      [(r["arm"], r["uid"].split("/")[-1], r["rendered_tokens"], r["server_prompt_tokens"]) for r in rows
       if r["rendered_tokens"] != r["server_prompt_tokens"]][:5])
for arm in ("restored", "placebo"):
    rr = [r for r in rows if r["arm"] == arm]
    print(arm, "policy present in rendered prompt", sum(r["policy_in_rendered"] for r in rr), "/", len(rr),
          "| equals prohibitions_description", sum(bool(r["policy_equals_prohibition"]) for r in rr),
          "| words match", sum(r["policy_words"] == r["prohibition_words"] for r in rr),
          "| policy names the benign tool", sum(bool(r["policy_mentions_trigger_name"]) for r in rr))
print("prohibition text names the harmful tool name:", sum(r["prohibition_mentions_harmful_name"] for r in rows if r["arm"] == "restored"))
print("trigger first in rendered <tools> block:", sum(r["trigger_first_in_tools_block"] for r in rows), "/", n)
print("system content before <tools> block:", sum(r["system_before_tools"] for r in rows), "/", n)
