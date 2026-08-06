import {
    useEffect,
    useState
} from "react";

import DashboardCard
    from "../components/DashboardCard";

import {
    getDashboardStats
} from "../api/dashboardApi";

export default function DashboardPage() {

    const [stats, setStats] =
        useState(null);

    const [loading, setLoading] =
        useState(true);

    const [error, setError] =
        useState("");

    async function loadDashboard() {

        try {

            const data =
                await getDashboardStats();

            setStats(data);

        } catch (err) {

            setError(
                "Impossible de charger le tableau de bord."
            );

        } finally {

            setLoading(false);

        }
    }

    useEffect(() => {
        loadDashboard();
    }, []);

    if (loading) {

        return (
            <div>
                Chargement...
            </div>
        );
    }

    if (error) {

        return (
            <div className="alert alert-danger">
                {error}
            </div>
        );
    }

    return (

        <div>

            <h2>
                Tableau de bord RFID
            </h2>

            <div className="row mt-4 g-3">

                <div className="col-md-4">
                    <DashboardCard
                        title="Imports"
                        value={stats.imports}
                        color="primary"
                    />
                </div>

                <div className="col-md-4">
                    <DashboardCard
                        title="Biens actifs"
                        value={stats.active_assets}
                        color="success"
                    />
                </div>

                <div className="col-md-4">
                    <DashboardCard
                        title="Lots"
                        value={stats.jobs}
                        color="info"
                    />
                </div>

                <div className="col-md-4">
                    <DashboardCard
                        title="Fichiers générés"
                        value={stats.generated}
                        color="primary"
                    />
                </div>

                <div className="col-md-4">
                    <DashboardCard
                        title="Réimpressions"
                        value={stats.reprints}
                        color="warning"
                    />
                </div>

                <div className="col-md-4">
                    <DashboardCard
                        title="Lots en attente"
                        value={stats.pending}
                        color="danger"
                    />
                </div>

            </div>

        </div>
    );
}