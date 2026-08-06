import { useState } from "react";

import { uploadCsv } from "../api/importApi";

export default function ImportPage() {
    const [file, setFile] = useState(null);
    const [result, setResult] = useState(null);
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    async function handleSubmit(event) {
        event.preventDefault();

        if (!file) {
            setError("Veuillez sélectionner un fichier CSV.");
            return;
        }

        setLoading(true);
        setError("");
        setResult(null);

        try {
            const data = await uploadCsv(file);
            setResult(data);
        } catch (err) {
            setError(
                err.response?.data?.detail ||
                "Erreur lors de l’import."
            );
        } finally {
            setLoading(false);
        }
    }

    return (
        <div>
            <h2>Import inventaire CSV</h2>

            <form
                className="card p-4 mt-4"
                onSubmit={handleSubmit}
            >
                <div className="mb-3">
                    <label className="form-label">
                        Fichier CSV
                    </label>

                    <input
                        type="file"
                        accept=".csv"
                        className="form-control"
                        onChange={(event) =>
                            setFile(event.target.files[0])
                        }
                    />
                </div>

                {error && (
                    <div className="alert alert-danger">
                        {error}
                    </div>
                )}

                <button
                    className="btn btn-primary"
                    disabled={loading}
                >
                    {loading
                        ? "Import en cours..."
                        : "Importer"}
                </button>
            </form>

            {result && (
                <div className="card p-4 mt-4">
                    <h5>Résultat de l’import</h5>

                    <p>
                        Fichier : {result.filename}
                    </p>

                    <p>
                        Lignes : {result.total_rows}
                    </p>

                    <p>
                        Biens actifs : {result.active_assets}
                    </p>

                    <p>
                        Biens exclus : {result.excluded_assets}
                    </p>
                </div>
            )}
        </div>
    );
}