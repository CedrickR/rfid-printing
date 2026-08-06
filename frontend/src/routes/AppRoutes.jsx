import {
    Navigate,
    Route,
    Routes,
} from "react-router-dom";

import ProtectedRoute from "../components/ProtectedRoute";
import Layout from "../components/Layout";

import LoginPage from "../pages/LoginPage";
import DashboardPage from "../pages/DashboardPage";
import ImportPage from "../pages/ImportPage";
import AssetsPage from "../pages/AssetsPage";
import PrintJobsPage from "../pages/PrintJobsPage";
import PrintJobDetailPage from "../pages/PrintJobDetailPage";
import HistoryPage from "../pages/HistoryPage";
import SettingsPage from "../pages/SettingsPage";

export default function AppRoutes() {
    return (
        <Routes>
            <Route
                path="/login"
                element={<LoginPage />}
            />

            <Route
                path="/"
                element={
                    <ProtectedRoute>
                        <Layout />
                    </ProtectedRoute>
                }
            >
                <Route
                    index
                    element={<DashboardPage />}
                />

                <Route
                    path="imports"
                    element={<ImportPage />}
                />

                <Route
                    path="assets"
                    element={<AssetsPage />}
                />

                <Route
                    path="print-jobs"
                    element={<PrintJobsPage />}
                />

                <Route
                    path="print-jobs/:id"
                    element={<PrintJobDetailPage />}
                />

                <Route
                    path="history"
                    element={<HistoryPage />}
                />

                <Route
                    path="settings"
                    element={<SettingsPage />}
                />
            </Route>

            <Route
                path="*"
                element={
                    <Navigate
                        to="/"
                        replace
                    />
                }
            />
        </Routes>
    );
}