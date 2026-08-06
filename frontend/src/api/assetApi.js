import apiClient from "./apiClient";

export async function getAssets(page = 1, size = 100) {
    const response = await apiClient.get(
        "/api/import/assets",
        {
            params: {
                page,
                size,
            },
        }
    );

    return response.data;
}

export async function getActiveAssetsCount() {
    const response = await apiClient.get(
        "/api/import/assets/active"
    );

    return response.data;
}

export async function searchAssets(query) {
    const response = await apiClient.get(
        "/api/import/assets/search",
        {
            params: {
                q: query,
            },
        }
    );

    return response.data;
}