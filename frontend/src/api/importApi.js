import apiClient from "./apiClient";

export async function uploadCsv(file) {
    const formData = new FormData();

    formData.append("file", file);

    const response = await apiClient.post(
        "/api/import/",
        formData,
        {
            headers: {
                "Content-Type": "multipart/form-data",
            },
        }
    );

    return response.data;
}

export async function getAssetsCount() {
    const response = await apiClient.get(
        "/api/import/assets-count"
    );

    return response.data;
}