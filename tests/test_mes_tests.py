import main


def test_sauver_et_reprendre(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    reponses = iter(["d4 e5", "sauver", "e7 d6", "reprendre", "quitter"])
    monkeypatch.setattr("builtins.input", lambda invite="": next(reponses))

    assert main.main() == 0
    sortie = capsys.readouterr().out
    assert "Partie sauvegardée." in sortie
    assert "Partie reprise." in sortie
