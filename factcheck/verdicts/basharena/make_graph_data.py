# Build graph_data.json from results.json (own analysis) and print compact tables for verdict.md.
import sys, json
R = json.load(open(sys.argv[1])); out_path = sys.argv[2]
REPO_MATCHED = {'apollo-watcher': 0.854, 'GLM-4.6': 0.658, 'Claude Haiku 4.5': 0.668, 'GPT-5.4 nano high': 0.667,
                'GPT-5.4 nano medium': 0.580, 'DeepSeek V3.2': 0.523, 'GPT-5.4 nano none': 0.522, 'GPT-5.4 nano low': 0.509,
                'GPT-4.1 nano': 0.518, 'GPT-5 nano minimal': 0.453, 'GPT-4o mini': 0.381}
r3 = lambda x: None if x is None else round(float(x), 4)
mons = []
for o in R['monitors']:
    m = dict(display_name=o['name'], board_variant=o['variant'], n_attack=o['n_attack'], n_honest=o['n_honest'],
             unmatched_auroc=r3(o['unmatched_auroc']), unmatched_ci_traj=[r3(x) for x in o['unmatched_ci']],
             unmatched_ci_taskcluster=[r3(x) for x in o['unmatched_ci_taskcluster']],
             board_published_auroc=r3(o['unmatched_auroc']),
             board_published_auroc_note='board computes AUROC client-side from score_samples (max over non-null per-action scores, attack positive); value recomputed by the same rule',
             length_only_auroc_nactions=r3(o['length_only_auroc_nactions']),
             repo_reported_matched_auroc=REPO_MATCHED[o['name']],
             mean_per_action_auroc=r3(o['mean_per_action_auroc']), pooled_per_action_auroc=r3(o['pooled_action_auroc']),
             honest_spearman_peak_vs_nactions=r3(o['honest_spearman_peak_vs_n']),
             matched={k: {kk: (r3(vv) if isinstance(vv, (int, float)) else ([r3(x) for x in vv] if isinstance(vv, list) else vv))
                          for kk, vv in v.items()} for k, v in o['matched'].items()},
             stepwise_safety_1pct={k: (r3(v) if isinstance(v, (int, float)) else [r3(x) for x in v]) for k, v in o['stepwise_safety_1pct'].items()})
    mons.append(m)
mech = {x['name']: x for x in R['mechanism']}
for m in mons:
    x = mech[m['display_name']]
    m['mechanism'] = dict(honest_spearman_peak_n=r3(x['honest_spearman_peak_n']), iid_order_stat_sim_spearman=r3(x['iid_sim_spearman_peak_n']),
                          honest_spearman_mean_step_n=r3(x['honest_spearman_meanstep_n']), honest_spearman_score_vs_step_index=r3(x['honest_spearman_score_vs_step_index']),
                          mean_peak_attack=r3(x['attack_mean_peak']), mean_peak_honest=r3(x['honest_mean_peak']), by_length_bin=x['by_length'])
ov = R['overlap']
G = dict(monitors=mons, overlap=ov, counts=R['counts'], change_counts=R['change'], kendall_tau_vs_full=R['kendall_tau_vs_full'],
         median_length=dict(n_actions=dict(attack=ov['median_nactions_attack'], honest=ov['median_nactions_honest']),
                            monitor_visible_chars=dict(attack=ov['median_visible_chars_attack'], honest=ov['median_visible_chars_honest']),
                            agent_output_tokens=dict(attack=ov['median_output_tokens_attack'], honest=ov['median_output_tokens_honest'])),
         notes=dict(
            board='Redwood Control Leaderboard, Monitor evals page (control-leaderboard.redwoodresearch.org/monitors), default dataset BashArena (Claude Opus 4.6 agent, 600/600, 596/596 scored by every monitor). Table columns: AUROC, pAUROC 0-20% FPR, average precision, all on peak (max per-action) suspicion; default sort AUROC descending (site JS bundle 064cp4396tz_~.js, local copy from 2026-11-17). Column tooltip already says: "Stepwise monitors use peak suspicion, which can reflect trajectory length." Step-wise safety at audit budgets is stored in monitors.json (safety_curve) and shown on the safety pages, not as a monitor-board column. Pages are client-rendered; a live fetch on 2026-11-20 showed only a loading shell, so the live wording was not re-read.',
            length_measure='Primary: n_actions (number of agent tool-call actions, from score_samples; equals tool-call count in raw evals). Alternatives: monitor-visible characters (tool-call arguments + tool outputs, from raw evals) and agent output tokens (model_usage; mostly hidden reasoning, NOT visible to monitors).',
            matching_methods=dict(
                repo_quintile_reweight_nactions='Repo method re-implemented: 5 bins at attack n_actions quintiles, honest reweighted to attack bin shares, all attacks kept.',
                reweight_decile_nactions='Same with 10 attack-decile bins.',
                strat_exact_nactions='AUROC over attack/honest pairs with identical n_actions only (pair-count weighted).',
                strat_width2_nactions='Within-bin pairs, bins of width 2 actions.',
                strat_width5_nactions='Within-bin pairs, bins of width 5 actions.',
                strat_quintile_nactions='Within-bin pairs, attack-quintile bins. Coarse: the top bin holds 439 honest (to 106 actions) vs 123 attacks (18-41), residual confounding; pair-count weighting gives that bin ~90% of pairs.',
                strat_decile_nactions='Within-bin pairs, attack-decile bins (same caveat, top bin).',
                resid_linear_logn_honestfit='Peak residualised on log n_actions using OLS fitted on honest runs only; AUROC of residuals. Extrapolates the honest slope to short attacks.',
                resid_cubic_logn_honestfit='Same with cubic in log n.',
                cov_adjusted_knn60_logn='Covariate-adjusted ROC (Janes-Pepe placement values): each attack placed in the score distribution of its 60 nearest-length honest runs.',
                truncate_honest_to_attack_length='Each attack vs every honest run at least as long, honest peak recomputed over its first n_attack actions.',
                nn1to1_nactions_exact='Greedy 1:1 matching without replacement, exact n_actions.',
                **{'nn1to1_logn_cal0.1':'Greedy 1:1 matching without replacement, |log n| caliper 0.1.'},
                visible_chars_and_output_tokens='reweight/strat decile versions on the alternative length measures.'),
            ci='95% percentile bootstrap, 1000 resamples of trajectories stratified by class (200 for cov_adjusted and truncation; 300 for step-wise safety); NN-matched CIs resample matched pairs; repo method also with main-task cluster bootstrap.',
            chance_definitions='point_le_0p5: matched point <= 0.5; ci_includes_0p5; ci_entirely_below: upper < 0.5; ci_entirely_above: lower > 0.5; not_above_chance = 11 - ci_entirely_above.'))
json.dump(G, open(out_path, 'w'), indent=1)

# compact print
print('name | unmatched [CI] | len-only | repo-matched(mine) [CI] | repo reported | delta [CI] | safety full/stored/matched delta[CI]')
for o in R['monitors']:
    rm = o['matched']['repo_quintile_reweight_nactions']; s = o['stepwise_safety_1pct']
    print(f"{o['name']} | {o['unmatched_auroc']:.3f} [{o['unmatched_ci'][0]:.3f},{o['unmatched_ci'][1]:.3f}] | {o['length_only_auroc_nactions']:.3f} | {rm['auroc']:.3f} [{rm['ci'][0]:.3f},{rm['ci'][1]:.3f}] tc[{rm['ci_taskcluster'][0]:.3f},{rm['ci_taskcluster'][1]:.3f}] | {REPO_MATCHED[o['name']]} | {rm['delta']:+.3f} [{rm['delta_ci'][0]:+.3f},{rm['delta_ci'][1]:+.3f}] | {s['full']:.3f}/{s['board_stored']:.3f}/{s['matched_repo']:.3f} {s['delta']:+.3f} [{s['delta_ci'][0]:+.3f},{s['delta_ci'][1]:+.3f}]")
print()
keys = list(R['monitors'][0]['matched'].keys())
print('method | ' + ' | '.join(o['name'] for o in R['monitors']))
for k in keys:
    print(k, '|', ' | '.join(f"{o['matched'][k]['auroc']:.3f}" for o in R['monitors']))
print()
for k, c in R['counts'].items():
    print(k, {kk: (vv['n'] if isinstance(vv, dict) else vv) for kk, vv in c.items()})
print()
for k, c in R['change'].items(): print(k, c['prereg_rule_n'], c['ci_excludes_0_n'], c['prereg_rule'])
print(json.dumps(R['kendall_tau_vs_full']))
for o in R['monitors']:
    for k in ('nn1to1_nactions_exact', 'nn1to1_logn_cal0.1'):
        mm = o['matched'][k]
    print(o['name'], {k: (o['matched'][k]['n_pairs'], round(o['matched'][k]['matched_attack_success_rate'], 3), o['matched'][k]['matched_attack_median_n']) for k in ('nn1to1_nactions_exact', 'nn1to1_logn_cal0.1')})
    break
for x in R['mechanism']:
    print(x['name'], 'rho_peak', round(x['honest_spearman_peak_n'], 2), 'iid', round(x['iid_sim_spearman_peak_n'], 2), 'rho_mean', round(x['honest_spearman_meanstep_n'], 2),
          'rho_idx', round(x['honest_spearman_score_vs_step_index'], 2), 'peakA/H', round(x['attack_mean_peak'], 1), round(x['honest_mean_peak'], 1),
          [(b['bin'], round(b['mean_peak'], 1), round(b['iid_pred_peak'], 1)) for b in x['by_length']])
