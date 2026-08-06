export default function RecentActivity({
    activities
}) {

    return (

        <div className="card shadow-sm mt-4">

            <div className="card-body">

                <h5>
                    Dernières activités
                </h5>

                <table className="table">

                    <thead>

                        <tr>
                            <th>Heure</th>
                            <th>Action</th>
                            <th>Lot</th>
                            <th>Utilisateur</th>
                        </tr>

                    </thead>

                    <tbody>

                        {
                            activities.map(
                                (activity) => (

                                <tr
                                    key={activity.id}
                                >

                                    <td>
                                        {
                                            new Date(
                                                activity.created_at
                                            ).toLocaleString(
                                                "fr-FR"
                                            )
                                        }
                                    </td>

                                        <td>

                                        <span
                                            className={
                                                `badge ${getBadgeClass(
                                                    activity.action
                                                )}`
                                            }
                                        >

                                            {activity.action}

                                        </span>

                                        </td>

                                    <td>

                                        #
                                        {
                                            activity.job_id
                                        }

                                    </td>

                                    <td>

                                        {
                                            activity.username
                                        }

                                    </td>

                                </tr>

                            ))
                        }

                    </tbody>

                </table>

            </div>

        </div>

    );
}

function getBadgeClass(
    action
) {

    switch(action) {

        case "GENERATED":
            return "bg-primary";

        case "REPRINTED":
            return "bg-warning";

        case "PRINTED":
            return "bg-success";

        case "FAILED":
            return "bg-danger";

        default:
            return "bg-secondary";
    }
}