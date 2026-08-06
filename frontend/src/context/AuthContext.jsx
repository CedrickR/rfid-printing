import {
    createContext,
    useContext,
    useEffect,
    useState,
} from "react";

import {
    login as loginApi,
    getCurrentUser,
} from "../api/authApi";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    const token = localStorage.getItem("token");

    const isAuthenticated = Boolean(token);

    async function login(username, password) {
        const loginData = await loginApi(
            username,
            password
        );

        localStorage.setItem(
            "token",
            loginData.access_token
        );

        const currentUser = await getCurrentUser();

        localStorage.setItem(
            "user",
            JSON.stringify(currentUser)
        );

        setUser(currentUser);

        return currentUser;
    }

    function logout() {
        localStorage.removeItem("token");
        localStorage.removeItem("user");
        setUser(null);
    }

    useEffect(() => {
        async function loadUser() {
            try {
                const storedToken =
                    localStorage.getItem("token");

                if (!storedToken) {
                    setLoading(false);
                    return;
                }

                const currentUser =
                    await getCurrentUser();

                setUser(currentUser);

                localStorage.setItem(
                    "user",
                    JSON.stringify(currentUser)
                );
            } catch {
                logout();
            } finally {
                setLoading(false);
            }
        }

        loadUser();
    }, []);

    return (
        <AuthContext.Provider
            value={{
                user,
                loading,
                isAuthenticated,
                login,
                logout,
            }}
        >
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    return useContext(AuthContext);
}