from __future__ import annotations

from evals.search import build_search_eval_dataset


def test_build_search_eval_dataset_collects_all_case_modules() -> None:
    dataset = build_search_eval_dataset()

    assert [case.name for case in dataset.cases] == [
        "pet_safe_dark_hallway",
        "toddler_room_tight_gap",
        "balcony_wfh_setup",
        "reading_nook_under_stairs",
        "search_reply_avoids_bundle_word",
        "rental_gallery_wall",
        "hallway_thread_complementary_products",
        "hallway_complementary_omission_guard",
        "unsupported_constraints_do_not_bundle",
    ]
