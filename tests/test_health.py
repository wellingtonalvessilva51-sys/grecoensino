"""Teste de fumaça do esqueleto: a API sobe e o healthcheck responde."""

from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_health_ok():
    resposta = client.get("/health")
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["status"] == "ok"


def test_erro_estruturado_em_json():
    # Rota inexistente deve retornar o envelope de erro padronizado.
    resposta = client.get("/rota-que-nao-existe")
    assert resposta.status_code == 404
    assert "erro" in resposta.json()
