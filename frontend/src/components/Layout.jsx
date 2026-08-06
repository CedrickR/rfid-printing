import { Outlet } from "react-router-dom";

import Sidebar from "./Sidebar";
import Header from "./Header";

export default function Layout() {
    return (
        <div className="app-layout">
            <Sidebar />

            <main className="app-main">
                <Header />

                <div className="app-content">
                    <Outlet />
                </div>
            </main>
        </div>
    );
}