import copy
import json
import unittest
from pathlib import Path

from audience_swarm_lab.context import retrieve
from audience_swarm_lab.contracts import validate
from audience_swarm_lab.engine import simulate
from audience_swarm_lab.matching import evaluate_logged_policy, rank_products


ROOT = Path(__file__).resolve().parents[1]
CASE = json.loads((ROOT / "fixtures/offer-comparison.json").read_text())


class AudienceLabTests(unittest.TestCase):
    def test_same_scenario_replays_exactly(self):
        first = simulate(CASE)
        self.assertEqual(first, simulate(CASE))
        self.assertEqual(first["agent_steps"], 400 * 8 * 50 * 3)
        self.assertEqual(first["evidence_label"], "SYNTHETIC_SCENARIO")

    def test_no_op_arm_has_exact_zero_paired_effect(self):
        case = copy.deepcopy(CASE)
        case["runs"] = 3
        case["arms"] = [{"id": "same", "start_step": 4, "product_id": "assist-basic", "changes": {"price": 49}}]
        effect = simulate(case)["paired_effects"]["same"]
        self.assertTrue(all(item["mean"] == 0 for item in effect.values()))

    def test_inputs_have_bounded_cost_and_known_references(self):
        case = copy.deepcopy(CASE)
        case["runs"] = 200
        case["population"] = 5000
        with self.assertRaisesRegex(ValueError, "work budget"):
            validate(case)
        case = copy.deepcopy(CASE)
        case["arms"][0]["product_id"] = "not-a-product"
        with self.assertRaisesRegex(ValueError, "unknown product"):
            validate(case)
        case = copy.deepcopy(CASE)
        case["products"][0]["unit_cost"] = 100
        with self.assertRaisesRegex(ValueError, "exceeds price"):
            validate(case)

    def test_context_retrieval_returns_source_and_license(self):
        hits = retrieve("pricing quality adoption", CASE["documents"])
        self.assertTrue(hits)
        self.assertEqual(hits[0]["document_id"], "demo-brief")
        self.assertIn("license", hits[0])
        self.assertEqual(retrieve("unmatchedtoken", CASE["documents"]), [])

    def test_ranking_respects_availability(self):
        ranking = rank_products(CASE["segments"][0], CASE["products"], {"assist-basic"})
        self.assertEqual([item["product_id"] for item in ranking], ["assist-basic"])

    def test_off_policy_evaluation_requires_overlap_and_propensity(self):
        logged = json.loads((ROOT / "fixtures/logged-policy.json").read_text())
        result = evaluate_logged_policy(logged["records"], logged["target_actions"])
        self.assertEqual(result["estimate"], 47.5)
        self.assertEqual(result["effective_sample_size"], 2.0)
        bad = copy.deepcopy(logged["records"])
        bad[0]["propensity"] = 0
        with self.assertRaisesRegex(ValueError, "propensity"):
            evaluate_logged_policy(bad, logged["target_actions"])
        with self.assertRaisesRegex(ValueError, "no overlap"):
            evaluate_logged_policy(logged["records"][:1], {"budget": "assist-pro"})

    def test_cost_meter_reconciles(self):
        cost = simulate(CASE)["cost_estimate"]
        self.assertAlmostEqual(cost["direct"], cost["cpu"] + cost["graph_index"] + cost["storage_and_observability"])
        self.assertAlmostEqual(cost["with_operating_allowance"], cost["direct"] * 1.3)
        self.assertIn("excludes provider calls", cost["basis"])


if __name__ == "__main__":
    unittest.main()
