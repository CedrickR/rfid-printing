import apiClient from "./apiClient";

export async function createPrintJob(assetIds) {
    const response = await apiClient.post(
        "/api/print/jobs",
        {
            asset_ids: assetIds,
        }
    );

    return response.data;
}

export async function getPrintJobs() {
    const response = await apiClient.get(
        "/api/print/jobs"
    );

    return response.data;
}

export async function getPrintJob(jobId) {
    const response = await apiClient.get(
        `/api/print/jobs/${jobId}`
    );

    return response.data;
}

export async function generatePrintJobFile(jobId) {
    const response = await apiClient.post(
        `/api/print/jobs/${jobId}/generate`
    );

    return response.data;
}

export async function reprintJob(jobId) {
    const response = await apiClient.post(
        `/api/print/jobs/${jobId}/reprint`
    );

    return response.data;
}

export async function downloadPrintJobFile(jobId) {
    const response = await apiClient.get(
        `/api/print/jobs/${jobId}/file`,
        {
            responseType: "blob",
        }
    );

    return response;
}