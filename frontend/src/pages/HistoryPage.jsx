import { useEffect, useState } from "react";

import { getHistory } from "../api/historyApi";

export default function HistoryPage() {
    const [history, setHistory] = useState([]);

    async function loadHistory() {
        const data = await getHistory();
        setHistory(data);
    }

    useEffect(() => {
        loadHistory();
    }, []);

    return (
        <div>
            <h2>Historique</h2>

            <div className="card p-3 mt-4">
                <table className="table table-striped">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Lot</th>
                            <th>Utilisateur</th>
                            <th>Action</th>
                            <th>Fichier</th>
                            <th>Étiquettes</th>
                        </tr>
                    </thead>

                    <tbody>
                        {history.map((item) => (
                            <tr key={item.id}>
                                <td>{item.id}</td>
                                <td>{item.job_id}</td>
                                <td>{item.username}</td>
                                <td>{item.action}</td>
                                <td>{item.file_name}</td>
                                <td>{item.labels_count}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}