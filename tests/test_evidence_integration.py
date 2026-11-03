import app.verification as verification


def test_ai_analysis_present_in_response(client, monkeypatch):

    async def fake_extract(text):
        return text, "test"

    async def fake_factchecks(claim):
        return []

    async def fake_analysis(claim, evidence):
        return {
            "mode": "test",
            "relation": "inconclusif",
            "explication": "Réponse simulée pour le test.",
            "references": [],
            "limites": "Contrôle humain nécessaire."
        }

    monkeypatch.setattr(
        verification, "extract_claim", fake_extract
    )
    monkeypatch.setattr(
        verification, "search_factchecks", fake_factchecks
    )
    monkeypatch.setattr(
        verification, "analyze_evidence", fake_analysis
    )

    response = client.post(
        "/api/verify/text",
        json={
            "text": (
                "Une affirmation de test qui nécessite "
                "une vérification documentaire."
            )
        }
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["verdict"] == "a_verifier"
    assert data["ai_analysis"]["mode"] == "test"

    saved = client.get(
        "/api/verifications/" + data["id"]
    )

    assert saved.status_code == 200
    assert saved.json()["ai_analysis"] == data["ai_analysis"]
