import apiClient from "./apiClient";

export async function getDashboardStats() {

    const response =
        await apiClient.get(
            "/api/dashboard"
        );

    return response.data;
}

export async function getRecentActivity() {

    const response =
        await apiClient.get(
            "/api/dashboard/recent"
        );

    return response.data;
}