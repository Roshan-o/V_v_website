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
  const [isProcessing, setIsProcessing] = useState(false);
  const [activeTab, setActiveTab] = useState<string>('all');
  const [srcLanguage, setSrcLanguage] = useState<string>('English');
  const [targetLanguage, setTargetLanguage] = useState<string>('Telugu');
  const [gender, setGender] = useState<string>('Female');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('src_language', srcLanguage);
    formData.append('target_language', targetLanguage);
    formData.append('gender', gender);

    setUploading(true);
    setJobId(null);
    setJob(null);
    setActiveTab('all');

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

  const convert = async () => {
    if (!jobId) return;
    setIsProcessing(true);
    try {
      await axios.post(`${API_BASE_URL}/convert/${jobId}`);
      const response = await axios.get(`${API_BASE_URL}/jobs/${jobId}`);
      setJob(response.data);
    } catch (error) {
      console.error('Conversion failed:', error);
      alert('Failed to start conversion.');
      setIsProcessing(false);
    }
  };

  const stop = async () => {
    if (!jobId) return;
    try {
      await axios.post(`${API_BASE_URL}/jobs/${jobId}/stop`);
      setIsProcessing(false);
    } catch (error) {
      console.error('Stop failed:', error);
    }
  };

  useEffect(() => {
    let interval: NodeJS.Timeout;

    const shouldPoll = jobId && (
      !job || 
      job.status === 'processing' || 
      (job.status === 'waiting_for_conversion' && job.stages.extraction === 'processing')
    );

    if (shouldPoll && job?.status !== 'cancelled') {
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
        {name === 'translation' ? 'Translation' : name === 'dubbing' ? 'Audio Generation' : name.replace('_', ' ')}
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

        {name === 'transcription' && status === 'pending' && job?.status === 'waiting_for_conversion' && (
          <div className="stage-content" style={{ paddingTop: '0.5rem' }}>
            <button 
              className="btn btn-small" 
              onClick={convert} 
              disabled={isProcessing}
            >
              {isProcessing ? 'Processing...' : 'Start Processing'}
            </button>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="App">
      <div className="container">
        <header style={{ marginBottom: '1rem' }}>
          <h1 style={{ fontSize: '1.5rem', margin: 0 }}>Video Translation</h1>
          <p style={{ fontSize: '0.9rem', color: '#666', margin: 0 }}>Translate and dub videos</p>
        </header>

        <div style={{ display: 'flex', gap: '10px', justifyContent: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', fontSize: '0.85rem' }}>
          <select value={srcLanguage} onChange={(e) => setSrcLanguage(e.target.value)} style={{ padding: '6px', borderRadius: '4px', border: '1px solid #ccc' }}>
            {['English', 'Hindi', 'Bengali', 'Tamil', 'Telugu', 'Marathi', 'Malayalam', 'Kannada', 'Gujarati', 'Punjabi', 'Urdu', 'Odia', 'Assamese', 'Nepali', 'Sanskrit', 'Sindhi'].map(lang => (
              <option key={lang} value={lang}>{lang}</option>
            ))}
          </select>
          <span style={{ alignSelf: 'center' }}>to</span>
          <select value={targetLanguage} onChange={(e) => setTargetLanguage(e.target.value)} style={{ padding: '6px', borderRadius: '4px', border: '1px solid #ccc' }}>
            {['Telugu', 'English', 'Hindi', 'Tamil', 'Kannada', 'Malayalam', 'Marathi', 'Gujarati', 'Bengali', 'Punjabi', 'Odia', 'Urdu'].map(lang => (
              <option key={lang} value={lang}>{lang}</option>
            ))}
          </select>
          <select value={gender} onChange={(e) => setGender(e.target.value)} style={{ padding: '6px', borderRadius: '4px', border: '1px solid #ccc' }}>
            <option value="Female">Female</option>
            <option value="Male">Male</option>
          </select>
          {jobId && <button className="btn btn-secondary btn-small" onClick={() => { setJobId(null); setJob(null); setActiveTab('all'); setIsProcessing(false); }}>New</button>}
        </div>

        <div className="upload-card" style={{ padding: jobId ? '1rem' : '2rem' }}>
          <input
            type="file"
            ref={fileInputRef}
            style={{ display: 'none' }}
            accept="video/*"
            onChange={handleFileUpload}
          />
          
          {!jobId ? (
            <div onClick={() => fileInputRef.current?.click()}>
              <div className="upload-icon-container">
                <span>{uploading ? '...' : 'Upload'}</span>
              </div>
              <span className="upload-text">
                {uploading ? 'Uploading...' : 'Select Video'}
              </span>
            </div>
          ) : (
            <div className="preview-container" style={{ display: 'flex', justifyContent: 'center' }}>
              {job?.files['original'] ? (
                <video controls src={`${API_BASE_URL}${job.files['original']}`} style={{ maxHeight: '200px', maxWidth: '100%', borderRadius: '8px' }} />
              ) : (
                <div className="placeholder-box">Loading preview...</div>
              )}
            </div>
          )}
        </div>

        {job?.status === 'waiting_for_conversion' && (
          <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
            <button 
              className="btn" 
              onClick={convert}
              disabled={isProcessing}
              style={{ width: '100%', maxWidth: '400px' }}
            >
              {isProcessing ? 'Processing...' : 'Start Processing'}
            </button>
          </div>
        )}

        {jobId && (
          <div className="pipeline">
            <div className="pipeline-header">
              {job?.status === 'error' && (
                <div className="status-badge status-error" style={{ marginBottom: '1rem' }}>
                  {job.error_message}
                </div>
              )}
              {(isProcessing || job?.status === 'processing') && (
                <div style={{ textAlign: 'center', marginBottom: '1rem' }}>
                  <button className="btn btn-secondary btn-small" onClick={stop}>Stop Processing</button>
                </div>
              )}
            </div>

            {/* Final Result Preview */}
            <div className="comparison-container" style={{ gridTemplateColumns: '1fr' }}>
              <div className="video-column">
                <h4>Generated Video</h4>
                <div className="comparison-box" style={{ maxHeight: '300px' }}>
                  {job?.files['dubbing'] ? (
                    <video controls src={`${API_BASE_URL}${job.files['dubbing']}`} style={{ maxHeight: '100%', width: 'auto' }} />
                  ) : (
                    <div className="placeholder-box">
                      {job?.stages['dubbing'] === 'processing' ? (
                        <div className="processing-indicator">
                          <div className="spinner large"></div>
                          <p>Dubbing in progress...</p>
                        </div>
                      ) : (
                        <p>Awaiting Results...</p>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Module Tabs */}
            <div className="tabs-container">
              {['all', 'extraction', 'transcription', 'translation', 'dubbing'].map((tab) => (
                <button
                  key={tab}
                  className={`tab-btn ${activeTab === tab ? 'active' : ''}`}
                  onClick={() => setActiveTab(tab)}
                >
                  {tab === 'all' ? 'All Steps' : 
                   tab === 'translation' ? 'MT' : 
                   tab === 'dubbing' ? 'Text to Audio' : 
                   tab.charAt(0).toUpperCase() + tab.slice(1)}
                </button>
              ))}
            </div>

            <div className="tab-content">
              {activeTab === 'all' ? (
                <>
                  {Object.entries(job?.stages || {
                    extraction: 'pending',
                    transcription: 'pending',
                    translation: 'pending',
                    dubbing: 'pending'
                  }).map(([name, status]) =>
                    renderStage(name, status, job?.files[name])
                  )}
                </>
              ) : (
                renderStage(activeTab, job?.stages[activeTab] || 'pending', job?.files[activeTab])
              )}
            </div>
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
