import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './App.css';

const API_BASE_URL = 'http://localhost:8000';

interface JobStatus {
  id: string;
  status: string;
  stages: Record<string, string>;
  files: Record<string, string>;
  error_message?: string;
}

function App() {
  const [jobId, setJobId] = useState<string | null>(null);
  const [job, setJob] = useState<JobStatus | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    setUploading(true);
    setJobId(null);
    setJob(null);

    try {
      const response = await axios.post(`${API_BASE_URL}/upload`, formData);
      setJobId(response.data.job_id);
    } catch (error) {
      console.error('Upload failed:', error);
      alert('Upload failed. Is the backend running?');
    } finally {
      setUploading(false);
    }
  };

  useEffect(() => {
    let interval: NodeJS.Timeout;

    if (jobId && (!job || job.status === 'processing')) {
      interval = setInterval(async () => {
        try {
          const response = await axios.get(`${API_BASE_URL}/jobs/${jobId}`);
          setJob(response.data);
          
          if (response.data.status !== 'processing') {
            clearInterval(interval);
          }
        } catch (error) {
          console.error('Failed to fetch job status:', error);
        }
      }, 2000);
    }

    return () => clearInterval(interval);
  }, [jobId, job]);

  const renderStage = (name: string, status: string, filePath?: string) => {
    return (
      <div className="stage-card" key={name}>
        <div className="stage-header">
          <div className="stage-title">
            {status === 'processing' && <div className="spinner"></div>}
            {name.replace('_', ' ')}
          </div>
          <div className={`status-badge status-${status}`}>
            {status}
          </div>
        </div>
        
        {status === 'completed' && filePath && (
          <div className="stage-content">
            <div className="preview-box">
              {name === 'extraction' && (
                <audio controls src={`${API_BASE_URL}${filePath}`} />
              )}
              {(name === 'transcription' || name === 'translation') && (
                <JsonPreview url={`${API_BASE_URL}${filePath}`} />
              )}
              {name === 'dubbing' && (
                <video controls src={`${API_BASE_URL}${filePath}`} style={{ maxWidth: '100%' }} />
              )}
              {name === 'original' && (
                <video controls src={`${API_BASE_URL}${filePath}`} style={{ maxWidth: '100%' }} />
              )}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="App">
      <div className="container">
        <header>
          <h1>Video Dubber AI</h1>
          <p className="subtitle">Seamlessly translate and dub your videos into Telugu</p>
        </header>

        {!jobId && (
          <div 
            className="upload-card" 
            onClick={() => fileInputRef.current?.click()}
          >
            <input 
              type="file" 
              ref={fileInputRef} 
              style={{ display: 'none' }} 
              accept="video/*" 
              onChange={handleFileUpload}
            />
            <span className="upload-icon">📁</span>
            <span className="upload-text">
              {uploading ? 'Uploading Video...' : 'Click or Drag Video to Upload'}
            </span>
            <span className="upload-hint">MP4, MOV supported. Max 50MB suggested.</span>
          </div>
        )}

        {jobId && (
          <div className="pipeline">
            <div className="pipeline-header">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <h3>Processing Pipeline</h3>
                <button className="btn" onClick={() => { setJobId(null); setJob(null); }}>Start New</button>
              </div>
              {job?.status === 'error' && (
                <div className="status-badge status-error" style={{ marginBottom: '1rem', display: 'block' }}>
                  Error: {job.error_message}
                </div>
              )}
            </div>

            {renderStage('original', 'completed', job?.files['original'])}
            
            {Object.entries(job?.stages || {
              extraction: 'pending',
              transcription: 'pending',
              translation: 'pending',
              dubbing: 'pending'
            }).map(([name, status]) => 
              renderStage(name, status, job?.files[name])
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function JsonPreview({ url }: { url: string }) {
  const [content, setContent] = useState<string>('Loading...');

  useEffect(() => {
    axios.get(url).then(res => {
      setContent(JSON.stringify(res.data, null, 2));
    }).catch(err => {
      setContent('Error loading content');
    });
  }, [url]);

  return <pre className="preview-text">{content}</pre>;
}

export default App;
