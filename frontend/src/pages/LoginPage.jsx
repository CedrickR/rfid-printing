import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

export default function LoginPage() {
    const navigate = useNavigate();

    const { login } = useAuth();

    const [username, setUsername] =
        useState("");

    const [password, setPassword] =
        useState("");

    const [loading, setLoading] =
        useState(false);

    const [error, setError] =
        useState("");

    async function handleSubmit(event) {
        event.preventDefault();

        setLoading(true);
        setError("");

        try {
            await login(username, password);

            navigate("/");
        } catch (err) {
            if (!err.response) {
                setError(
                    "Impossible de joindre le serveur."
                );
            } else {
                setError(
                    "Identifiant ou mot de passe invalide."
                );
            }
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="login-page">
            <div className="card login-card shadow">
                <div className="card-body">
                    <h1 className="login-title">
                        RFID PRINTING
                    </h1>

                    <p className="text-muted text-center mb-4">
                        Connexion à l’application
                    </p>

                    <form onSubmit={handleSubmit}>
                        <div className="mb-3">
                            <label className="form-label">
                                Identifiant
                            </label>

                            <input
                                type="text"
                                className="form-control"
                                value={username}
                                onChange={(event) =>
                                    setUsername(
                                        event.target.value
                                    )
                                }
                                autoFocus
                                required
                            />
                        </div>

                        <div className="mb-3">
                            <label className="form-label">
                                Mot de passe
                            </label>

                            <input
                                type="password"
                                className="form-control"
                                value={password}
                                onChange={(event) =>
                                    setPassword(
                                        event.target.value
                                    )
                                }
                                required
                            />
                        </div>

                        {error && (
                            <div className="alert alert-danger">
                                {error}
                            </div>
                        )}

                        <button
                            type="submit"
                            className="btn btn-primary w-100"
                            disabled={
                                loading ||
                                !username ||
                                !password
                            }
                        >
                            {loading
                                ? "Connexion..."
                                : "Se connecter"}
                        </button>
                    </form>
                </div>
            </div>
        </div>
    );
}