import React, { useState, useEffect } from 'react';
import { GuardianAPI, VerdictPayload } from '../types';

export default function App() {
    const [logs, setLogs] = useState<string[]>([]);
    const [verdict, setVerdict] = useState<VerdictPayload | null>(null);

    useEffect(() => {
        window.guardian.onLog((line) => {
            setLogs((prev) => [...prev, line]);
        });

        window.guardian.onVerdict((data) => {
            setVerdict(data);
        });

        return () => {
            window.guardian.removeAllListeners();
        };
    }, []);

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        const filePath = e.dataTransfer.files[0]?.path;
        if (filePath) {
            setLogs([]);
            setVerdict(null);
            window.guardian.startPipeline(filePath);
        }
    };

    return (
        <div
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
            style={{ width: '100vw', height: '100vh', padding: 20, boxSizing: 'border-box' }}
        >
            <h1>DICOM Guardian</h1>
            <p>Drop a DICOM file here to start the pipeline.</p>

            {verdict && (
                <div style={{ padding: 10, border: '1px solid black', marginTop: 20 }}>
                    <h2>Verdict: {verdict.type}</h2>
                    {verdict.score && <p>Score: {verdict.score}</p>}
                    {verdict.reason && <p>Reason: {verdict.reason}</p>}
                </div>
            )}

            <div style={{ marginTop: 20, height: 300, overflowY: 'auto', background: '#eee', padding: 10 }}>
                {logs.map((log, i) => <div key={i}>{log}</div>)}
            </div>
        </div>
    );
}
