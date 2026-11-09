| suite / engine | case | verdict | expected | must-not violated | certificates (axioms) |
|---|---|---|---|---|---|
| /tmp/ce/sota3/core_heldout | h01_int_abs_sq | ABSTAIN  | CERTIFIED_LOGICAL_EQUIVALENCE | False |  |
| /tmp/ce/sota3/core_heldout | h02_nat_div_mul | CERTIFIED_LOGICAL_DIFFERENCE reference_false_formalization_true | CERTIFIED_LOGICAL_DIFFERENCE | False | diff_RL propext+Quot.sound, false_R, link_L, link_R, region_ref_excluded, true_L propext+Quot.sound, wit_R |
| /tmp/ce/sota3/core_heldout | h03_bool_and_comm | CERTIFIED_LOGICAL_EQUIVALENCE both_true | CERTIFIED_LOGICAL_EQUIVALENCE | False | equiv_both_true, link_L, link_R, true_L, true_R |
| /tmp/ce/sota3/core_heldout | h04_list_length_append | ABSTAIN  | CERTIFIED_LOGICAL_DIFFERENCE | False |  |
| /tmp/ce/sota3/core_heldout | h05_exists_bound_swap | CERTIFIED_LOGICAL_DIFFERENCE reference_true_formalization_false | CERTIFIED_LOGICAL_DIFFERENCE | False | diff_LR propext+Quot.sound, false_L propext+Quot.sound, link_L, link_R, true_R propext+Quot.sound, wit_L propext+Quot.sound |
| /tmp/ce/sota3/core_heldout | h06_off_by_one | CERTIFIED_LOGICAL_DIFFERENCE reference_true_formalization_false | CERTIFIED_LOGICAL_DIFFERENCE | False | diff_LR, false_L, link_L, link_R, region_conclusion_lean_stronger, true_R, wit_L |
| /tmp/ce/sota3/core_heldout | h07_vacuous_ref | CERTIFIED_LOGICAL_DIFFERENCE reference_true_formalization_false | CERTIFIED_LOGICAL_DIFFERENCE | False | diff_LR propext+Quot.sound, false_L, link_L, link_R, region_lean_excluded, true_R propext+Quot.sound, wit_L |
| /tmp/ce/sota3/core_heldout | h08_both_false_different | CERTIFIED_LOGICAL_EQUIVALENCE both_false | CERTIFIED_LOGICAL_EQUIVALENCE | False | equiv_both_false, false_L, false_R, link_L, link_R, region_conclusion_lean_stronger, wit_L, wit_R |
| /tmp/ce/sota3/core_heldout | h09_int_sub_order | CERTIFIED_LOGICAL_DIFFERENCE reference_false_formalization_true | CERTIFIED_LOGICAL_DIFFERENCE | False | diff_RL propext+Quot.sound, false_R, link_L, link_R, region_ref_excluded, true_L propext+Quot.sound, wit_R |
| /tmp/ce/sota3/core_heldout | h10_joint_harmless_parts | CERTIFIED_LOGICAL_DIFFERENCE reference_true_formalization_false | CERTIFIED_LOGICAL_DIFFERENCE | False | diff_LR, false_L, link_L, link_R, region_joint, region_lean_excluded, true_R, wit_L |
| /tmp/ce/sota3/core_heldout | h11_disjoint_regions | CERTIFIED_LOGICAL_EQUIVALENCE both_true | CERTIFIED_LOGICAL_EQUIVALENCE | False | equiv_both_true, link_L, link_R, true_L, true_R |
| /tmp/ce/sota3/core_heldout | h12_open_problem_like | ABSTAIN  | CERTIFIED_LOGICAL_DIFFERENCE | False |  |
| /tmp/ce/sota3/core_heldout | h13_identical_unprovable_here | CERTIFIED_LOGICAL_EQUIVALENCE definitional | CERTIFIED_LOGICAL_EQUIVALENCE | False | equiv_both_true propext, equiv_defeq, link_L, link_R, true_L propext, true_R propext |
| /tmp/ce/sota3/core_heldout | h14_mixed_strict | CERTIFIED_LOGICAL_DIFFERENCE reference_true_formalization_false | CERTIFIED_LOGICAL_DIFFERENCE | False | diff_LR, false_L, link_L, link_R, region_lean_excluded, true_R, wit_L |
| /tmp/ce/sota4/core_heldout | h01_int_abs_sq | ABSTAIN  | CERTIFIED_LOGICAL_EQUIVALENCE | False | link_L, link_R, true_L propext |
| /tmp/ce/sota4/core_heldout | h02_nat_div_mul | CERTIFIED_LOGICAL_DIFFERENCE reference_false_formalization_true | CERTIFIED_LOGICAL_DIFFERENCE | False | diff_RL propext+Quot.sound, false_R, link_L, link_R, region_ref_excluded, true_L propext+Quot.sound, wit_R |
| /tmp/ce/sota4/core_heldout | h03_bool_and_comm | CERTIFIED_LOGICAL_EQUIVALENCE both_true | CERTIFIED_LOGICAL_EQUIVALENCE | False | equiv_both_true, link_L, link_R, true_L, true_R |
| /tmp/ce/sota4/core_heldout | h04_list_length_append | ABSTAIN  | CERTIFIED_LOGICAL_DIFFERENCE | False | link_L, link_R, true_R propext |
| /tmp/ce/sota4/core_heldout | h05_exists_bound_swap | CERTIFIED_LOGICAL_DIFFERENCE reference_true_formalization_false | CERTIFIED_LOGICAL_DIFFERENCE | False | diff_LR propext+Quot.sound, false_L propext+Quot.sound, link_L, link_R, true_R propext+Quot.sound, wit_L propext+Quot.sound |
| /tmp/ce/sota4/core_heldout | h06_off_by_one | CERTIFIED_LOGICAL_DIFFERENCE reference_true_formalization_false | CERTIFIED_LOGICAL_DIFFERENCE | False | diff_LR, false_L, link_L, link_R, region_conclusion_lean_stronger, true_R, wit_L |
| /tmp/ce/sota4/core_heldout | h07_vacuous_ref | CERTIFIED_LOGICAL_DIFFERENCE reference_true_formalization_false | CERTIFIED_LOGICAL_DIFFERENCE | False | diff_LR propext+Quot.sound, false_L, link_L, link_R, region_lean_excluded, true_R propext+Quot.sound, wit_L |
| /tmp/ce/sota4/core_heldout | h08_both_false_different | CERTIFIED_LOGICAL_EQUIVALENCE both_false | CERTIFIED_LOGICAL_EQUIVALENCE | False | equiv_both_false, false_L, false_R, link_L, link_R, region_conclusion_lean_stronger, wit_L, wit_R |
| /tmp/ce/sota4/core_heldout | h09_int_sub_order | CERTIFIED_LOGICAL_DIFFERENCE reference_false_formalization_true | CERTIFIED_LOGICAL_DIFFERENCE | False | diff_RL propext+Quot.sound, false_R, link_L, link_R, region_ref_excluded, true_L propext+Quot.sound, wit_R |
| /tmp/ce/sota4/core_heldout | h10_joint_harmless_parts | CERTIFIED_LOGICAL_DIFFERENCE reference_true_formalization_false | CERTIFIED_LOGICAL_DIFFERENCE | False | diff_LR, false_L, link_L, link_R, region_joint, region_lean_excluded, true_R, wit_L |
| /tmp/ce/sota4/core_heldout | h11_disjoint_regions | CERTIFIED_LOGICAL_EQUIVALENCE both_true | CERTIFIED_LOGICAL_EQUIVALENCE | False | equiv_both_true, link_L, link_R, true_L, true_R |
| /tmp/ce/sota4/core_heldout | h12_open_problem_like | ABSTAIN  | CERTIFIED_LOGICAL_DIFFERENCE | False | false_L propext+Classical.choice+Quot.sound, link_L, link_R, region_lean_excluded propext+Classical.choice+Quot.sound, wit_L propext+Classical.choice+Quot.sound |
| /tmp/ce/sota4/core_heldout | h13_identical_unprovable_here | CERTIFIED_LOGICAL_EQUIVALENCE definitional | CERTIFIED_LOGICAL_EQUIVALENCE | False | equiv_both_true propext, equiv_defeq, link_L, link_R, true_L propext, true_R propext |
| /tmp/ce/sota4/core_heldout | h14_mixed_strict | CERTIFIED_LOGICAL_DIFFERENCE reference_true_formalization_false | CERTIFIED_LOGICAL_DIFFERENCE | False | diff_LR, false_L, link_L, link_R, region_lean_excluded, true_R, wit_L |
| /tmp/ce/sota3/core_dev | c01_natsub_needs_hyp | CERTIFIED_LOGICAL_DIFFERENCE reference_false_formalization_true | CERTIFIED_LOGICAL_DIFFERENCE | False | diff_RL propext+Quot.sound, false_R, link_L, link_R, region_ref_excluded, true_L propext+Quot.sound, wit_R |
| /tmp/ce/sota3/core_dev | c02_natabs_analogue | CERTIFIED_LOGICAL_DIFFERENCE reference_false_formalization_true | CERTIFIED_LOGICAL_DIFFERENCE | False | diff_RL propext+Quot.sound, false_R, link_L, link_R, region_ref_excluded, true_L propext+Quot.sound, wit_R |
| /tmp/ce/sota3/core_dev | c03_identical_true | CERTIFIED_LOGICAL_EQUIVALENCE definitional | CERTIFIED_LOGICAL_EQUIVALENCE | False | equiv_both_true propext+Quot.sound, equiv_defeq, link_L, link_R, true_L propext+Quot.sound, true_R propext+Quot.sound |
| /tmp/ce/sota3/core_dev | c04_both_false | CERTIFIED_LOGICAL_EQUIVALENCE both_false | CERTIFIED_LOGICAL_EQUIVALENCE | False | equiv_both_false, false_L, false_R, link_L, link_R, region_conclusion_ref_stronger, wit_L, wit_R |
| /tmp/ce/sota3/core_dev | c05_quantifier_swap | CERTIFIED_LOGICAL_DIFFERENCE reference_true_formalization_false | CERTIFIED_LOGICAL_DIFFERENCE | False | diff_LR propext+Quot.sound, false_L propext+Quot.sound, link_L, link_R, true_R propext+Quot.sound, wit_L propext+Quot.sound |
| /tmp/ce/sota3/core_dev | c06_strengthened_conclusion | CERTIFIED_LOGICAL_DIFFERENCE reference_true_formalization_false | CERTIFIED_LOGICAL_DIFFERENCE | False | diff_LR propext+Quot.sound, false_L, link_L, link_R, region_conclusion_lean_stronger, true_R propext+Quot.sound, wit_L |
| /tmp/ce/sota3/core_dev | c07_vacuous_both_true | CERTIFIED_LOGICAL_EQUIVALENCE both_true | CERTIFIED_LOGICAL_EQUIVALENCE | False | equiv_both_true, link_L, link_R, true_L, true_R |
| /tmp/ce/sota3/core_dev | c08_joint_drift | CERTIFIED_LOGICAL_DIFFERENCE reference_true_formalization_false | CERTIFIED_LOGICAL_DIFFERENCE | False | diff_LR, false_L, link_L, link_R, region_joint, region_lean_excluded, true_R, wit_L |
| /tmp/ce/sota3/core_dev | c09_bool_dropped | CERTIFIED_LOGICAL_DIFFERENCE reference_true_formalization_false | CERTIFIED_LOGICAL_DIFFERENCE | False | diff_LR, false_L, link_L, link_R, region_lean_excluded, true_R, wit_L |
| /tmp/ce/sota3/core_dev | c10_list_open | CERTIFIED_LOGICAL_EQUIVALENCE both_true | CERTIFIED_LOGICAL_EQUIVALENCE | False | equiv_both_true propext, link_L, link_R, true_L propext, true_R propext |
| /tmp/ce/sota4/core_dev | c01_natsub_needs_hyp | CERTIFIED_LOGICAL_DIFFERENCE reference_false_formalization_true | CERTIFIED_LOGICAL_DIFFERENCE | False | diff_RL propext+Quot.sound, false_R, link_L, link_R, region_ref_excluded, true_L propext+Quot.sound, wit_R |
| /tmp/ce/sota4/core_dev | c02_natabs_analogue | CERTIFIED_LOGICAL_DIFFERENCE reference_false_formalization_true | CERTIFIED_LOGICAL_DIFFERENCE | False | diff_RL propext+Quot.sound, false_R, link_L, link_R, region_ref_excluded, true_L propext+Quot.sound, wit_R |
| /tmp/ce/sota4/core_dev | c03_identical_true | CERTIFIED_LOGICAL_EQUIVALENCE definitional | CERTIFIED_LOGICAL_EQUIVALENCE | False | equiv_both_true propext+Quot.sound, equiv_defeq, link_L, link_R, true_L propext+Quot.sound, true_R propext+Quot.sound |
| /tmp/ce/sota4/core_dev | c04_both_false | CERTIFIED_LOGICAL_EQUIVALENCE both_false | CERTIFIED_LOGICAL_EQUIVALENCE | False | equiv_both_false, false_L, false_R, link_L, link_R, region_conclusion_ref_stronger, wit_L, wit_R |
| /tmp/ce/sota4/core_dev | c05_quantifier_swap | CERTIFIED_LOGICAL_DIFFERENCE reference_true_formalization_false | CERTIFIED_LOGICAL_DIFFERENCE | False | diff_LR propext+Quot.sound, false_L propext+Quot.sound, link_L, link_R, true_R propext+Quot.sound, wit_L propext+Quot.sound |
| /tmp/ce/sota4/core_dev | c06_strengthened_conclusion | CERTIFIED_LOGICAL_DIFFERENCE reference_true_formalization_false | CERTIFIED_LOGICAL_DIFFERENCE | False | diff_LR propext+Quot.sound, false_L, link_L, link_R, region_conclusion_lean_stronger, true_R propext+Quot.sound, wit_L |
| /tmp/ce/sota4/core_dev | c07_vacuous_both_true | CERTIFIED_LOGICAL_EQUIVALENCE both_true | CERTIFIED_LOGICAL_EQUIVALENCE | False | equiv_both_true, link_L, link_R, true_L, true_R |
| /tmp/ce/sota4/core_dev | c08_joint_drift | CERTIFIED_LOGICAL_DIFFERENCE reference_true_formalization_false | CERTIFIED_LOGICAL_DIFFERENCE | False | diff_LR, false_L, link_L, link_R, region_joint, region_lean_excluded, true_R, wit_L |
| /tmp/ce/sota4/core_dev | c09_bool_dropped | CERTIFIED_LOGICAL_DIFFERENCE reference_true_formalization_false | CERTIFIED_LOGICAL_DIFFERENCE | False | diff_LR, false_L, link_L, link_R, region_lean_excluded, true_R, wit_L |
| /tmp/ce/sota4/core_dev | c10_list_open | CERTIFIED_LOGICAL_EQUIVALENCE both_true | CERTIFIED_LOGICAL_EQUIVALENCE | False | equiv_both_true propext, link_L, link_R, true_L propext, true_R propext |

{
 "/tmp/ce/sota3/core_heldout": {
  "cases": 14,
  "exact": 11,
  "must_not_violations": 0,
  "certificate_problems": 0
 },
 "/tmp/ce/sota4/core_heldout": {
  "cases": 14,
  "exact": 11,
  "must_not_violations": 0,
  "certificate_problems": 0
 },
 "/tmp/ce/sota3/core_dev": {
  "cases": 10,
  "exact": 10,
  "must_not_violations": 0,
  "certificate_problems": 0
 },
 "/tmp/ce/sota4/core_dev": {
  "cases": 10,
  "exact": 10,
  "must_not_violations": 0,
  "certificate_problems": 0
 }
}
