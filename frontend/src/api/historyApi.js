import apiClient from "./apiClient";

export async function getHistory() {
    const response = await apiClient.get(
        "/api/history"
    );

    return response.data;
}

export async function getMyHistory() {
    const response = await apiClient.get(
        "/api/history/me"
    );

    return response.data;
}

export async function getJobHistory(jobId) {
    const response = await apiClient.get(
        `/api/history/${jobId}`
    );

    return response.data;
}