export interface VerdictPayload {
    type: 'PASS' | 'SECURITY_FAILURE' | 'PIPELINE_ERROR';
    score?: number;
    phash_score?: number;
    ring_score?: number;
    hist_score?: number;
    reason?: string;
}

export interface GuardianAPI {
    startPipeline: (dicomPath: string) => Promise<void>;
    onLog: (callback: (line: string) => void) => void;
    onVerdict: (callback: (data: VerdictPayload) => void) => void;
    removeAllListeners: () => void;
}

/** Electron extends the browser File object with a `path` property. */
export interface ElectronFile extends File {
    path: string;
}
