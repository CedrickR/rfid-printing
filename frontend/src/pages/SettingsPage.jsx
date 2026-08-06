export default function SettingsPage() {
    return (
        <div>
            <h2>Administration</h2>

            <div className="card p-4 mt-4">
                <h5>Intégration RFID réelle</h5>

                <p>
                    Statut : en attente des informations du prestataire.
                </p>

                <ul>
                    <li>Modèle de l’imprimante RFID</li>
                    <li>Format de fichier attendu</li>
                    <li>Exemple de commande constructeur</li>
                    <li>Règles d’encodage RFID</li>
                    <li>Dossier surveillé par l’imprimante</li>
                </ul>
            </div>
        </div>
    );
}