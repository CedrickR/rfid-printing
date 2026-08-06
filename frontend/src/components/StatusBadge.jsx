export default function StatusBadge({ status }) {
    const colors = {
        PENDING: "secondary",
        GENERATED: "primary",
        PRINTED: "success",
        FAILED: "danger",
        REPRINTED: "warning",
    };

    const color = colors[status] || "secondary";

    return (
        <span className={`badge bg-${color}`}>
            {status}
        </span>
    );
}