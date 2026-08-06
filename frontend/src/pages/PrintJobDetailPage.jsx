import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import {
    getPrintJob,
    generatePrintJobFile,
    downloadPrintJobFile,
    reprintJob,
} from "../api/printApi";

import StatusBadge from "../components/StatusBadge";

export default function PrintJobDetailPage() {
    const { id } = useParams();

    const [job, setJob] = useState(null);
    const [message, setMessage] = useState("");
    const [error, setError] = useState("");

    async function loadJob() {
        const data = await getPrintJob(id);
        setJob(data);
    }

    useEffect(() => {
        loadJob();
    }, [id]);

    async function handleGenerate() {
        setError("");
        setMessage("");

        try {
            await generatePrintJobFile(id);
            setMessage("Fichier CMD généré.");
            loadJob();
        } catch (err) {
            setError(
                err.response?.data?.detail ||
                "Erreur lors de la génération."
            );
        }
    }

    async function handleDownload() {
        const response = await downloadPrintJobFile(id);

        const url = window.URL.createObjectURL(
            new Blob([response.data])
        );

        const link = document.createElement("a");

        link.href = url;
        link.download = `print_job_${id}.cmd`;
        link.click();
    }

    async function handleReprint() {
        const confirmed = window.confirm(
            "Ce lot a déjà été généré. Confirmer la réimpression ?"
        );

        if (!confirmed) {
            return;
        }

        const data = await reprintJob(id);

        setMessage(
            `Réimpression enregistrée : ${data.status}`
        );
    }

    if (!job) {
        return <p>Chargement...</p>;
    }

    return (
        <div>
            <h2>Lot d’impression #{job.job_id}</h2>

            {message && (
                <div className="alert alert-success">
                    {message}
                </div>
            )}

            {error && (
                <div className="alert alert-danger">
                    {error}
                </div>
            )}

            <div className="card p-4 mt-4">
                <p>
                    Statut :{" "}
                    <StatusBadge status={job.status} />
                </p>

                <p>
                    Créé par : {job.created_by}
                </p>

                <p>
                    Étiquettes : {job.labels_count}
                </p>

                <h5>Biens du lot</h5>

                <ul>
                    {job.assets.map((asset) => (
                        <li key={asset.id}>
                            {asset.bien_id} -{" "}
                            {asset.bien_designation}
                        </li>
                    ))}
                </ul>

                <div className="d-flex gap-2 mt-3">
                    {job.status === "PENDING" && (
                        <button
                            className="btn btn-primary"
                            onClick={handleGenerate}
                        >
                            Générer CMD
                        </button>
                    )}

                    {job.status === "GENERATED" && (
                        <>
                            <button
                                className="btn btn-success"
                                onClick={handleDownload}
                            >
                                Télécharger CMD
                            </button>

                            <button
                                className="btn btn-warning"
                                onClick={handleReprint}
                            >
                                Réimprimer
                            </button>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}