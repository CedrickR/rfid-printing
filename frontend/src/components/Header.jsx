import { useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

export default function Header() {
    const navigate = useNavigate();

    const {
        user,
        logout,
    } = useAuth();

    function handleLogout() {
        logout();
        navigate("/login");
    }

    return (
        <header className="app-header">
            <div>
                <strong>Application RFID</strong>
            </div>

            <div className="d-flex align-items-center gap-3">
                {user && (
                    <span>
                        {user.sub} ({user.role})
                    </span>
                )}

                <button
                    className="btn btn-outline-danger btn-sm"
                    onClick={handleLogout}
                >
                    Déconnexion
                </button>
            </div>
        </header>
    );
}