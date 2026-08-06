import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { getPrintJobs } from "../api/printApi";
import StatusBadge from "../components/StatusBadge";

export default function PrintJobsPage() {
    const [jobs, setJobs] = useState([]);

    async function loadJobs() {
        const data = await getPrintJobs();
        setJobs(data);
    }

    useEffect(() => {
        loadJobs();
    }, []);

    return (
        <div>
            <h2>Lots d’impression</h2>

            <div className="card p-3 mt-4">
                <table className="table table-striped">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Créé par</th>
                            <th>Statut</th>
                            <th>Étiquettes</th>
                            <th>Actions</th>
                        </tr>
                    </thead>

                    <tbody>
                        {jobs.map((job) => (
                            <tr key={job.id}>
                                <td>{job.id}</td>

                                <td>{job.created_by}</td>

                                <td>
                                    <StatusBadge
                                        status={job.status}
                                    />
                                </td>

                                <td>{job.labels_count}</td>

                                <td>
                                    <Link
                                        to={`/print-jobs/${job.id}`}
                                        className="btn btn-sm btn-outline-primary"
                                    >
                                        Voir
                                    </Link>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}