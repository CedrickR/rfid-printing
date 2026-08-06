import { useEffect, useState } from "react";

import {
    getAssets,
    searchAssets,
} from "../api/assetApi";

import { createPrintJob } from "../api/printApi";

export default function AssetsPage() {
    const [assets, setAssets] = useState([]);
    const [selectedIds, setSelectedIds] = useState([]);
    const [query, setQuery] = useState("");
    const [message, setMessage] = useState("");

    async function loadAssets() {
        const data = await getAssets();
        setAssets(data);
    }

    useEffect(() => {
        loadAssets();
    }, []);

    function toggleSelection(assetId) {
        setSelectedIds((current) => {
            if (current.includes(assetId)) {
                return current.filter(
                    (id) => id !== assetId
                );
            }

            return [
                ...current,
                assetId,
            ];
        });
    }

    async function handleSearch() {
        if (!query) {
            loadAssets();
            return;
        }

        const data = await searchAssets(query);
        setAssets(data);
    }

    async function handleCreatePrintJob() {
        if (selectedIds.length === 0) {
            setMessage(
                "Veuillez sélectionner au moins un bien."
            );
            return;
        }

        const data = await createPrintJob(selectedIds);

        setSelectedIds([]);

        setMessage(
            `Lot d’impression créé : #${data.job_id}`
        );
    }

    return (
        <div>
            <h2>Inventaire</h2>

            <div className="card p-3 mt-4">
                <div className="d-flex gap-2 mb-3">
                    <input
                        className="form-control"
                        placeholder="Rechercher un bien"
                        value={query}
                        onChange={(event) =>
                            setQuery(event.target.value)
                        }
                    />

                    <button
                        className="btn btn-outline-primary"
                        onClick={handleSearch}
                    >
                        Rechercher
                    </button>
                </div>

                {message && (
                    <div className="alert alert-info">
                        {message}
                    </div>
                )}

                <table className="table table-striped">
                    <thead>
                        <tr>
                            <th>Sélection</th>
                            <th>ID</th>
                            <th>Bien ID</th>
                            <th>Désignation</th>
                            <th>Actif</th>
                        </tr>
                    </thead>

                    <tbody>
                        {assets.map((asset) => (
                            <tr key={asset.id}>
                                <td>
                                    <input
                                        type="checkbox"
                                        checked={
                                            selectedIds.includes(
                                                asset.id
                                            )
                                        }
                                        disabled={!asset.is_active}
                                        onChange={() =>
                                            toggleSelection(
                                                asset.id
                                            )
                                        }
                                    />
                                </td>

                                <td>{asset.id}</td>

                                <td>{asset.bien_id}</td>

                                <td>
                                    {asset.bien_designation}
                                </td>

                                <td>
                                    {asset.is_active
                                        ? "Oui"
                                        : "Non"}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>

                <button
                    className="btn btn-primary"
                    onClick={handleCreatePrintJob}
                >
                    Créer un lot d’impression
                </button>
            </div>
        </div>
    );
}