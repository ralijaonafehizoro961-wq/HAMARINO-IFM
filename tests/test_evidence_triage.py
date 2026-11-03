import pytest
from app.evidence_triage import validate_triage

DOC = {'title': 'Sommet Russie Afrique', 'passage': "Le chef de l'Etat a effectué un déplacement en Russie pour le sommet Russie Afrique.", 'url': 'https://example.org/one'}


def test_rejets_et_preuves():
    assert validate_triage({'documents': [{'id': 'S1', 'statut': 'hors_sujet', 'justification': 'Autre événement', 'citation': ''}]}, [DOC]) == []
    valid = validate_triage({'documents': [{'id': 'S1', 'statut': 'pertinent', 'justification': 'Documente le voyage', 'citation': 'a effectué un déplacement en Russie pour le sommet'}]}, [DOC])
    assert len(valid) == 1
    assert valid[0]['citation_pertinence'].startswith('a effectué')


def test_citation_inventee_refusee():
    assert validate_triage({'documents': [{'id': 'S1', 'statut': 'pertinent', 'justification': 'Test', 'citation': 'information inventée pour tester la validation'}]}, [DOC]) == []


def test_reference_inconnue_refusee():
    with pytest.raises(ValueError):
        validate_triage({'documents': [{'id': 'S99', 'statut': 'pertinent', 'justification': '', 'citation': ''}]}, [DOC])
