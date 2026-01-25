const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001';

export interface FilterOptions {
    music: boolean;
    profanity: boolean;
    nudity: boolean;
}

export interface ProcessingOptions {
    threshold?: number;      // Detection sensitivity (0.0-1.0, default: 0.4)
    resolution?: string;     // Video resolution for replacements (default: "720p")
    strict?: boolean;        // Use stricter visual detection (default: false)
}

export interface ProcessingResponse {
    success: boolean;
    videoBlob?: Blob;
    error?: string;
}

/**
 * Upload a video file to the Flask backend for processing
 * @param file - The MP4 file to process
 * @param filters - The content filters to apply (music, profanity, nudity/sexual)
 * @param options - Additional processing options (optional)
 * @returns Promise with the processed video blob
 */
export async function processVideo(
    file: File,
    filters: FilterOptions,
    options?: ProcessingOptions
): Promise<ProcessingResponse> {
    const formData = new FormData();

    // Add the video file
    formData.append('video', file);

    // Add filter booleans as separate form fields (Flask expects these as strings)
    formData.append('filter_music', filters.music.toString());
    formData.append('filter_profanity', filters.profanity.toString());
    formData.append('filter_sexual_nudity', filters.nudity.toString());

    // Add optional processing parameters
    if (options?.threshold !== undefined) {
        formData.append('threshold', options.threshold.toString());
    }
    if (options?.resolution) {
        formData.append('resolution', options.resolution);
    }
    if (options?.strict !== undefined) {
        formData.append('strict', options.strict.toString());
    }

    try {
        const response = await fetch(`${API_BASE_URL}/api/process`, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            // Try to parse error message from JSON response
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                const errorData = await response.json();
                throw new Error(errorData.error || `Server error: ${response.status}`);
            }
            throw new Error(`Server error: ${response.status}`);
        }

        // The backend returns the processed video as a blob (MP4 file)
        const videoBlob = await response.blob();

        // Verify we got a video file
        if (videoBlob.size === 0) {
            throw new Error('Received empty response from server');
        }

        return {
            success: true,
            videoBlob,
        };
    } catch (error) {
        console.error('Error processing video:', error);
        return {
            success: false,
            error: error instanceof Error ? error.message : 'Unknown error occurred',
        };
    }
}

/**
 * Check the health/status of the backend server
 * @returns Object with health status and configuration info
 */
export async function checkServerHealth(): Promise<{
    healthy: boolean;
    version?: string;
    openaiConfigured?: boolean;
    falConfigured?: boolean;
}> {
    try {
        const response = await fetch(`${API_BASE_URL}/api/health`);
        if (response.ok) {
            const data = await response.json();
            return {
                healthy: data.status === 'healthy',
                version: data.version,
                openaiConfigured: data.openai_configured,
                falConfigured: data.fal_configured,
            };
        }
        return { healthy: false };
    } catch {
        return { healthy: false };
    }
}

/**
 * Download the processed video blob as a file
 * @param blob - The video blob to download
 * @param filename - The filename for the downloaded file
 */
export function downloadVideoBlob(blob: Blob, filename: string = 'processed_video.mp4'): void {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}
