import { NavLink } from "react-router-dom";

export default function Sidebar() {
    return (
        <aside className="sidebar bg-dark text-white">
            <div className="sidebar-title">
                RFID PRINTING
            </div>

            <nav className="nav flex-column">
                <NavLink
                    to="/"
                    end
                    className="nav-link text-white"
                >
                    Tableau de bord
                </NavLink>

                <NavLink
                    to="/imports"
                    className="nav-link text-white"
                >
                    Imports
                </NavLink>

                <NavLink
                    to="/assets"
                    className="nav-link text-white"
                >
                    Inventaire
                </NavLink>

                <NavLink
                    to="/print-jobs"
                    className="nav-link text-white"
                >
                    Lots d’impression
                </NavLink>

                <NavLink
                    to="/history"
                    className="nav-link text-white"
                >
                    Historique
                </NavLink>

                <NavLink
                    to="/settings"
                    className="nav-link text-white"
                >
                    Administration
                </NavLink>
            </nav>
        </aside>
    );
}