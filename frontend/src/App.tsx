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
            {name === 'translation' ? 'MT (Translation)' : name === 'dubbing' ? 'Text to Audio' : name.replace('_', ' ')}
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
          <h1>Video to Video translation</h1>
          <p className="subtitle">Seamlessly translate and dub your videos into Telugu</p>
        </header>

        {!jobId && (
          <div style={{ display: 'flex', gap: '20px', justifyContent: 'center', marginBottom: '30px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', textAlign: 'left' }}>
              <label style={{ marginBottom: '5px', fontWeight: 'bold', color: '#555' }}>Source Language</label>
              <select 
                value={srcLanguage} 
                onChange={(e) => setSrcLanguage(e.target.value)} 
                style={{ padding: '10px', borderRadius: '6px', border: '1px solid #ccc', fontSize: '14px', minWidth: '120px' }}
              >
                <option value="English">English</option>
                <option value="Hindi">Hindi</option>
                <option value="Telugu">Telugu</option>
                <option value="Tamil">Tamil</option>
                <option value="Kannada">Kannada</option>
                <option value="Malayalam">Malayalam</option>
                <option value="Marathi">Marathi</option>
                <option value="Gujarati">Gujarati</option>
                <option value="Bengali">Bengali</option>
                <option value="Punjabi">Punjabi</option>
                <option value="Odia">Odia</option>
                <option value="Urdu">Urdu</option>
                <option value="Assamese">Assamese</option>
                <option value="Nepali">Nepali</option>
              </select>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', textAlign: 'left' }}>
              <label style={{ marginBottom: '5px', fontWeight: 'bold', color: '#555' }}>Target Language</label>
              <select 
                value={targetLanguage} 
                onChange={(e) => setTargetLanguage(e.target.value)} 
                style={{ padding: '10px', borderRadius: '6px', border: '1px solid #ccc', fontSize: '14px', minWidth: '120px' }}
              >
                <option value="English">English</option>
                <option value="Hindi">Hindi</option>
                <option value="Telugu">Telugu</option>
                <option value="Tamil">Tamil</option>
                <option value="Kannada">Kannada</option>
                <option value="Malayalam">Malayalam</option>
                <option value="Marathi">Marathi</option>
                <option value="Gujarati">Gujarati</option>
                <option value="Bengali">Bengali</option>
                <option value="Punjabi">Punjabi</option>
                <option value="Odia">Odia</option>
                <option value="Urdu">Urdu</option>
              </select>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', textAlign: 'left' }}>
              <label style={{ marginBottom: '5px', fontWeight: 'bold', color: '#555' }}>Voice Gender</label>
              <select 
                value={gender} 
                onChange={(e) => setGender(e.target.value)} 
                style={{ padding: '10px', borderRadius: '6px', border: '1px solid #ccc', fontSize: '14px', minWidth: '120px' }}
              >
                <option value="Female">Female</option>
                <option value="Male">Male</option>
              </select>
            </div>
          </div>
        )}

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
            <div className="upload-icon-container">
              <span className="upload-icon">📁</span>
            </div>
            <span className="upload-text">
              {uploading ? 'Uploading Video...' : 'Click or Drag Video to Upload'}
            </span>
            <span className="upload-hint">MP4, MOV supported. Max 50MB suggested.</span>
          </div>
        )}

        {jobId && (
          <div className="pipeline">
            <div className="pipeline-header">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                <h3 className="section-title">Processing Pipeline</h3>
                <button className="btn btn-secondary" onClick={() => { setJobId(null); setJob(null); setActiveTab('all'); }}>Start New</button>
              </div>
              {job?.status === 'error' && (
                <div className="status-badge status-error" style={{ marginBottom: '1rem', display: 'block', textAlign: 'center' }}>
                  Error: {job.error_message}
                </div>
              )}
            </div>

            {/* Side by Side Comparison */}
            <div className="comparison-container">
              <div className="video-column">
                <h4>Original Video</h4>
                <div className="comparison-box">
                  {job?.files['original'] ? (
                    <video controls src={`${API_BASE_URL}${job.files['original']}`} />
                  ) : (
                    <div className="placeholder-box">Loading...</div>
                  )}
                </div>
              </div>
              <div className="video-column">
                <h4>Final Video</h4>
                <div className="comparison-box">
                  {job?.files['dubbing'] ? (
                    <video controls src={`${API_BASE_URL}${job.files['dubbing']}`} />
                  ) : (
                    <div className="placeholder-box">
                      {job?.stages['dubbing'] === 'processing' ? (
                        <div className="processing-indicator">
                          <div className="spinner large"></div>
                          <p>Dubbing in progress...</p>
                        </div>
                      ) : (
                        <p>Awaiting Dubbing...</p>
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
