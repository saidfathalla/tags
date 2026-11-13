"""Regression tests for the TAGS metrics (run with: python -m pytest)."""

import contextlib
import io
import os
import sys

import pytest
import rdflib

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
import tags  # noqa: E402

EPS = 1e-5
EDGE = os.path.join(ROOT, "tests", "edge-Case-validation")


def profile(path, **kw):
    with contextlib.redirect_stdout(io.StringIO()):
        return tags.analyze_knowledge_graph(path, **kw)


def m(res, code):
    return res["metrics"][code][0]


# --------------------------------------------------------------------------
# Ground truth for the Theoretical Reference Graph G_ref (paper, validation table)
G_REF = {
    "M1": 14, "M2": 7, "M3": 7, "M4": 7, "M5": 2.0, "M6": 0.33333, "M7": 1.0,
    "M8": 1.0, "M9": 0.23810, "M10": 1.5, "M11": 2, "M12": 1, "M13": 1,
    "M14": 0.85714, "M15": 1.0, "M16": 1.55666,
}


@pytest.mark.parametrize("code,expected", sorted(G_REF.items()))
def test_reference_graph_all_metrics(code, expected):
    res = profile(os.path.join(ROOT, "tests", "test_baseline.ttl"))
    assert m(res, code) == pytest.approx(expected, abs=EPS)


def test_projection_example():
    res = profile(os.path.join(ROOT, "tests", "projection_example.ttl"))
    assert (m(res, "M1"), m(res, "M2"), m(res, "M3"), m(res, "M4")) == (12, 5, 3, 5)
    assert m(res, "M11") == 2 and m(res, "M12") == 1


# --------------------------------------------------------------------------
# Edge cases
def test_empty_graph_returns_none():
    assert profile(os.path.join(EDGE, "empty_graph.ttl")) is None


def test_malformed_rdf_reports_error():
    res = profile(os.path.join(EDGE, "malformed_rdf.ttl"))
    assert isinstance(res, dict) and "error" in res


def test_disconnected_singletons():
    res = profile(os.path.join(EDGE, "disconnected_singletons.ttl"))
    assert (m(res, "M2"), m(res, "M3"), m(res, "M11"), m(res, "M12"), m(res, "M13")) == (4, 1, 3, 2, 3)
    assert m(profile(os.path.join(EDGE, "disconnected_singletons.ttl"), tau=1), "M13") == 2


def test_duplicate_triples_collapsed():
    res = profile(os.path.join(EDGE, "duplicate_triples.ttl"))
    assert (m(res, "M1"), m(res, "M3"), m(res, "M4")) == (2, 1, 1)


def test_multiple_predicates_collapse_to_one_edge():
    res = profile(os.path.join(EDGE, "multiple_OP.ttl"))
    assert m(res, "M3") == 1
    assert m(res, "M15") == pytest.approx(1.0)   # 2 predicates / 2 object triples


def test_literals_are_not_edges_and_typed_node_is_orphan():
    res = profile(os.path.join(EDGE, "literals.ttl"))
    assert (m(res, "M2"), m(res, "M3"), m(res, "M12")) == (1, 0, 1)


def test_multi_type_entity_entropy():
    res = profile(os.path.join(EDGE, "multi_type_entity.ttl"))
    assert m(res, "M4") == 4
    assert m(res, "M16") == pytest.approx(1.5)   # Researcher 2/4, others 1/4


def test_no_type_graph():
    res = profile(os.path.join(EDGE, "no_type_graph.ttl"))
    assert (m(res, "M3"), m(res, "M4"), m(res, "M12")) == (3, 0, 0)
    assert m(res, "M7") == 0.0 and m(res, "M16") == 0.0
    assert m(res, "M9") == pytest.approx(1.0)    # triangle


def test_object_only_nodes():
    res = profile(os.path.join(EDGE, "object_only_nodes.ttl"))
    assert (m(res, "M2"), m(res, "M3")) == (2, 1)


def test_self_loops_ignored():
    res = profile(os.path.join(EDGE, "self_loops.ttl"))
    assert m(res, "M3") == 1 and m(res, "M8") == 0.0
    assert res["diagnostics"]["self_loops_ignored"] == 1
    assert 0.0 <= m(res, "M6") <= 1.0


def test_type_only_graph():
    res = profile(os.path.join(EDGE, "type_only_graph.ttl"))
    assert (m(res, "M3"), m(res, "M11"), m(res, "M12"), m(res, "M5")) == (0, 3, 3, 0.0)


def test_blank_nodes():
    res = profile(os.path.join(EDGE, "blank_nodes.ttl"))
    assert (m(res, "M2"), m(res, "M3"), m(res, "M11")) == (3, 2, 1)


def test_untyped_literal_only_node_not_counted_in_m12(tmp_path):
    f = tmp_path / "g.ttl"
    f.write_text('@prefix ex: <http://example.org/> .\n'
                 'ex:a a ex:C .\n'
                 'ex:b ex:name "literal only, no type" .\n')
    res = profile(str(f))
    assert m(res, "M12") == 1
    assert res["diagnostics"]["untyped_isolated_nodes"] == 1


def test_flat_mode_masks_orphans():
    res = profile(os.path.join(ROOT, "tests", "test_baseline.ttl"), isolate_taxonomy=False)
    assert m(res, "M12") == 0 and m(res, "M11") == 1


def test_m15_within_unit_interval():
    for name in os.listdir(EDGE):
        res = profile(os.path.join(EDGE, name))
        if isinstance(res, dict) and "metrics" in res:
            assert 0.0 <= m(res, "M15") <= 1.0, name


# --------------------------------------------------------------------------
# VoID / DQV export
def test_void_profile_contains_all_metrics(tmp_path):
    res = profile(os.path.join(ROOT, "tests", "test_baseline.ttl"))
    void_path = tags.export_void_statistics(res, "test_baseline", str(tmp_path))
    vocab_path = tags.export_metric_vocabulary(res, str(tmp_path))
    g = rdflib.Graph().parse(void_path)
    dqv = rdflib.Namespace("http://www.w3.org/ns/dqv#")
    void = rdflib.Namespace("http://rdfs.org/ns/void#")
    assert len(list(g.objects(None, dqv.hasQualityMeasurement))) == 16
    assert next(g.objects(None, void.triples)).toPython() == 14
    assert len(set(rdflib.Graph().parse(vocab_path).subjects(rdflib.RDF.type, dqv.Metric))) == 16


# --------------------------------------------------------------------------
# Controlled defect injection on G_ref (paper, ORKG case study section)
def test_defect_injection(tmp_path):
    """Inject 5 typed orphans and 5 untyped literal-only nodes, and remove 4 edges
    (A-B, A-C, B-E, D-F) so that Node_A and the pair {E, F} become disconnected."""
    S = rdflib.Namespace("https://schema.org/")
    g = rdflib.Graph().parse(os.path.join(ROOT, "tests", "test_baseline.ttl"))
    for s, p, o in [(S.Node_A, S.collaboratesWith, S.Node_B), (S.Node_A, S.leadsProject, S.Node_C),
                    (S.Node_B, S.producesData, S.Node_E), (S.Node_D, S.utilizesDataset, S.Node_F)]:
        assert (s, p, o) in g
        g.remove((s, p, o))
    for i in range(5):
        g.add((S[f"Typed_Orphan_{i}"], rdflib.RDF.type, S.Dataset))
        g.add((S[f"Literal_Only_{i}"], S.name, rdflib.Literal(f"literal {i}")))
    f = tmp_path / "g_ref_defects.ttl"
    g.serialize(destination=str(f), format="turtle")

    res = profile(str(f))
    assert m(res, "M11") == 2 + 2 + 10        # original 2, +{A}, +{E,F}, +10 injected singletons
    assert m(res, "M12") == 1 + 1 + 5         # O_1, Node_A (typed, now isolated), 5 typed orphans
    assert res["diagnostics"]["untyped_isolated_nodes"] == 5
    assert m(res, "M13") == 13                # O_1, {A}, {E,F}, 10 injected (tau = 2)
