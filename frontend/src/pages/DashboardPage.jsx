export default function DashboardPage() {
    return (
        <div>
            <h2>Tableau de bord</h2>

            <div className="row mt-4">
                <div className="col-md-3">
                    <div className="card p-3">
                        <span className="text-muted">
                            Imports
                        </span>
                        <h3>À venir</h3>
                    </div>
                </div>

                <div className="col-md-3">
                    <div className="card p-3">
                        <span className="text-muted">
                            Biens actifs
                        </span>
                        <h3>À venir</h3>
                    </div>
                </div>

                <div className="col-md-3">
                    <div className="card p-3">
                        <span className="text-muted">
                            Lots générés
                        </span>
                        <h3>À venir</h3>
                    </div>
                </div>

                <div className="col-md-3">
                    <div className="card p-3">
                        <span className="text-muted">
                            Réimpressions
                        </span>
                        <h3>À venir</h3>
                    </div>
                </div>
            </div>
        </div>
    );
}

import RecentActivity
    from "../components/RecentActivity";

import {
    getDashboardStats,
    getRecentActivity
}
from "../api/dashboardApi";

const [activities, setActivities] =
    useState([]);

async function loadDashboard() {

    try {

        const statsData =
            await getDashboardStats();

        setStats(
            statsData
        );

        const activityData =
            await getRecentActivity();

        setActivities(
            activityData
        );

    } catch {

        setError(
            "Impossible de charger le tableau de bord."
        );

    } finally {

        setLoading(false);

    }
}

<RecentActivity
    activities={activities}
/>
