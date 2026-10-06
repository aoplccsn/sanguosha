# Golden scenario suite

50项指定现有行为场景，对应真实pytest节点。复用测试不是独立规则来源；通过不能替代总矩阵BLOCKED项的人工规则审计。参数化用例保留，不按字符串存在判定通过。执行：python scripts/run_golden_t18a11.py。

| # | 场景 | 可执行测试 |
| --- | --- | --- |
| 1 | slash variants damage and share phase limit | `tests/test_t6_military_basics.py::test_slash_variants_damage_and_share_phase_limit` |
| 2 | wine next slash bonus consumed and phase limit | `tests/test_t6_military_basics.py::test_wine_next_slash_bonus_consumed_and_phase_limit` |
| 3 | wine expires at finish | `tests/test_t6_military_basics.py::test_wine_expires_at_finish` |
| 4 | slash eight trigrams red judgment virtual dodge | `tests/test_t6_military_basics.py::test_slash_eight_trigrams_red_judgment_virtual_dodge` |
| 5 | fire chain waits for peach then resumes next recipient | `tests/test_t6_military_basics.py::test_fire_chain_waits_for_peach_then_resumes_next_recipient` |
| 6 | normal damage does not propagate or unchain | `tests/test_t6_military_basics.py::test_normal_damage_does_not_propagate_or_unchain` |
| 7 | fire slash entire chain waits for rescue before next target | `tests/test_t6_military_basics.py::test_fire_slash_entire_chain_waits_for_rescue_before_next_target` |
| 8 | damage armor modifiers | `tests/test_t6_military_basics.py::test_damage_armor_modifiers` |
| 9 | qinggang ignores black slash armor | `tests/test_t6_military_basics.py::test_qinggang_ignores_black_slash_armor` |
| 10 | armor slash filters | `tests/test_t6_equipment_chains.py::test_armor_slash_filters` |
| 11 | fan converts to fire against vine | `tests/test_t6_equipment_chains.py::test_fan_converts_to_fire_against_vine` |
| 12 | ancient blade empty hand adds damage | `tests/test_t6_equipment_chains.py::test_ancient_blade_empty_hand_adds_damage` |
| 13 | double sword opponent choice draws owner | `tests/test_t6_equipment_chains.py::test_double_sword_opponent_choice_draws_owner` |
| 14 | ice sword replaces damage and discards two | `tests/test_t6_equipment_chains.py::test_ice_sword_replaces_damage_and_discards_two` |
| 15 | kylin bow discards horse after damage | `tests/test_t6_equipment_chains.py::test_kylin_bow_discards_horse_after_damage` |
| 16 | dodge weapon followup | `tests/test_t6_equipment_chains.py::test_dodge_weapon_followup` |
| 17 | halberd last card hits three targets and consumes wine once | `tests/test_t6_equipment_chains.py::test_halberd_last_card_hits_three_targets_and_consumes_wine_once` |
| 18 | spear response preserves instance count and color | `tests/test_t6_equipment_chains.py::test_spear_response_preserves_instance_count_and_color` |
| 19 | spear active uses two physical costs and slash counter | `tests/test_t6_equipment_chains.py::test_spear_active_uses_two_physical_costs_and_slash_counter` |
| 20 | silver lion loss heals through equipment replacement reaction | `tests/test_t6_equipment_chains.py::test_silver_lion_loss_heals_through_equipment_replacement_reaction` |
| 21 | eight trigrams responds to archery window | `tests/test_t6_equipment_chains.py::test_eight_trigrams_responds_to_archery_window` |
| 22 | three nullifications leave original effect cancelled | `tests/test_t6_trick_chains.py::test_three_nullifications_leave_original_effect_cancelled` |
| 23 | duel alternates multiple slash responses then damage | `tests/test_t6_trick_chains.py::test_duel_alternates_multiple_slash_responses_then_damage` |
| 24 | savage assault resumes after dying to later targets | `tests/test_t6_trick_chains.py::test_savage_assault_resumes_after_dying_to_later_targets` |
| 25 | amazing grace five real cards selected from shared pool | `tests/test_t6_trick_chains.py::test_amazing_grace_five_real_cards_selected_from_shared_pool` |
| 26 | lightning miss moves same physical instance to next player | `tests/test_t6_trick_chains.py::test_lightning_miss_moves_same_physical_instance_to_next_player` |
| 27 | fire attack reveal then matching suit discard | `tests/test_t6_trick_chains.py::test_fire_attack_reveal_then_matching_suit_discard` |
| 28 | iron chain recast draws one without counter window | `tests/test_t6_trick_chains.py::test_iron_chain_recast_draws_one_without_counter_window` |
| 29 | remove real opponent card to correct zone | `tests/test_t6_remaining_effects.py::test_remove_real_opponent_card_to_correct_zone` |
| 30 | ex nihilo draws two real cards | `tests/test_t6_remaining_effects.py::test_ex_nihilo_draws_two_real_cards` |
| 31 | god salvation heals each living player once | `tests/test_t6_remaining_effects.py::test_god_salvation_heals_each_living_player_once` |
| 32 | delayed judgment skips actual phase | `tests/test_t6_remaining_effects.py::test_delayed_judgment_skips_actual_phase` |
| 33 | lightning hit deals three thunder and discards delayed card | `tests/test_t6_remaining_effects.py::test_lightning_hit_deals_three_thunder_and_discards_delayed_card` |
| 34 | borrowed sword second target response or weapon transfer | `tests/test_t6_remaining_effects.py::test_borrowed_sword_second_target_response_or_weapon_transfer` |
| 35 | counter chain parity changes real duel effect | `tests/test_t6_remaining_effects.py::test_counter_chain_parity_changes_real_duel_effect` |
| 36 | wine only saves its dying owner | `tests/test_t6_remaining_effects.py::test_wine_only_saves_its_dying_owner` |
| 37 | judgment recycles real discard pile | `tests/test_t6_remaining_effects.py::test_judgment_recycles_real_discard_pile` |
| 38 | wine expires even when finish phase is skipped | `tests/test_t6_remaining_effects.py::test_wine_expires_even_when_finish_phase_is_skipped` |
| 39 | lord loyalist penalty preserves judgment and special piles | `tests/test_t18a11_release.py::test_lord_loyalist_penalty_preserves_judgment_and_special_piles` |
| 40 | cuike killing lord does not offer burst after victory | `tests/test_t18a11_release.py::test_cuike_killing_lord_does_not_offer_burst_after_victory` |
| 41 | jingce never starts a new phase end request after lord death | `tests/test_t18a11_release.py::test_jingce_never_starts_a_new_phase_end_request_after_lord_death` |
| 42 | 103 descriptions are complete and original | `tests/test_t18a10_hardening.py::test_103_descriptions_are_complete_and_original` |
| 43 | discard becomes public only after move | `tests/test_t18a10_hardening.py::test_discard_becomes_public_only_after_move` |
| 44 | fire attack reveal snapshot and result | `tests/test_t18a10_hardening.py::test_fire_attack_reveal_snapshot_and_result` |
| 45 | root skip scope | `tests/test_t18a10_hardening.py::test_root_skip_scope` |
| 46 | short disconnect and token takeover | `tests/test_t18a10_hardening.py::test_short_disconnect_and_token_takeover` |
| 47 | public discard reaches every viewer and reconnect history | `tests/test_t18a10_hardening.py::test_public_discard_reaches_every_viewer_and_reconnect_history` |
| 48 | grace takeover really resolves pending then token returns | `tests/test_t18a10_hardening.py::test_grace_takeover_really_resolves_pending_then_token_returns` |
| 49 | tcp server close releases connected clients | `tests/test_t18a10_hardening.py::test_tcp_server_close_releases_connected_clients` |
| 50 | chengxiang public candidates have rank labels and restore | `tests/test_t17c_request_privacy.py::test_chengxiang_public_candidates_have_rank_labels_and_restore` |
