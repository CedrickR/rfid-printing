# Lance l'application RFID Printing en local, pour les tests avant la
# mise en place du service NSSM (voir §8.9/§8.11 de la documentation
# technique). A utiliser via un raccourci bureau (double-clic) ou
# directement dans une console PowerShell.
#
# Arreter le serveur : fermer la fenetre, ou Ctrl+C puis Entree.

$ErrorActionPreference = "Stop"

try {
    # Le script vit dans backend\scripts\ : le dossier backend est son
    # dossier parent, quel que soit l'emplacement du clone (D:\git\...
    # ou ailleurs).
    $BackendDir = Split-Path -Parent $PSScriptRoot
    Set-Location $BackendDir

    $VenvActivate = Join-Path $BackendDir "venv\Scripts\Activate.ps1"

    if (-not (Test-Path $VenvActivate)) {
        throw "Environnement virtuel introuvable : $VenvActivate (voir la documentation, section installation, pour le creer)."
    }

    & $VenvActivate

    # Sous-chemin de service derriere le reverse proxy Apache existant
    # (voir §8.11 de la documentation). Mettre "" si l'application est
    # testee directement sur le port 8000, sans passer par Apache.
    $env:URL_PREFIX = "/rfid"

    Write-Host ""
    Write-Host "RFID Printing - demarrage sur http://127.0.0.1:8000 (URL_PREFIX=$env:URL_PREFIX)" -ForegroundColor Green
    Write-Host "Laisser cette fenetre ouverte tant que le serveur doit tourner." -ForegroundColor Yellow
    Write-Host ""

    uvicorn app.main:app --host 127.0.0.1 --port 8000
}
catch {
    Write-Host ""
    Write-Host "Erreur : $_" -ForegroundColor Red
}
finally {
    Write-Host ""
    Read-Host "Appuyez sur Entree pour fermer cette fenetre"
}
