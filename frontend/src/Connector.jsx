import React, { useState, useEffect } from 'react';
import { Search, Globe, Link2, Monitor, Loader2, Play, CheckCircle2, Activity, Shield, Wifi, Globe2, Camera, Eye, EyeOff, RefreshCw } from 'lucide-react';

const isDev = window.location.port === '5173';
const API_BASE = isDev ? `http://${window.location.hostname}:8000` : '';

function Connector({ currentSource, onSetSource, frame, sites = [] }) {
    const [isScanning, setIsScanning] = useState(false);
    const [smartConnectLoading, setSmartConnectLoading] = useState(false);
    const [username, setUsername] = useState('admin');
    const [password, setPassword] = useState('password');
    const [showPassword, setShowPassword] = useState(false);
    const [manualUrl, setManualUrl] = useState('');

    const handleSmartConnect = async () => {
        setSmartConnectLoading(true);
        try {
            const res = await fetch(`${API_BASE}/api/smart_connect`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            const data = await res.json();
            if (data.status === 'success') {
                alert(data.message);
                onSetSource(data.uri);
            } else {
                alert(data.message || "Smart Connect failed. No devices found or wrong credentials.");
            }
        } catch (err) {
            console.error("Smart Connect error:", err);
            alert("Failed to reach backend.");
        } finally {
            setSmartConnectLoading(false);
        }
    };

    const handleManualConnect = async () => {
        if (!manualUrl) {
            alert("Please enter an RTSP URL.");
            return;
        }
        onSetSource(manualUrl);
    };

    const isLocalCCTV = !['0', 'http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4'].includes(currentSource) && 
                      currentSource !== '' && 
                      !sites.some(s => s.remote_url === currentSource);

    return (
        <div className="connector-view">
            <div className="connector-header">
                <h1>YantrAI Hub Integrator</h1>
                <p>Configure your 4 primary video stream categories for the Cloud Hub</p>
            </div>

            <div className="connector-grid">
                {/* Left: Quick Categories */}
                <div className="connector-left-col">
                    <section className="connector-card">
                        <div className="card-header">
                            <Activity size={20} className="icon-blue" />
                            <h2>Stream Categories</h2>
                        </div>
                        <div className="quick-connect-grid">
                            {/* Category 1: Sample */}
                            <div 
                                className={`quick-option ${currentSource === 'http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4' ? 'active' : ''}`} 
                                onClick={() => onSetSource('http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4')}
                            >
                                <div className="option-icon"><Play size={24} /></div>
                                <div className="option-label">1. Sample Video</div>
                                <div className="option-desc">Cloud-based test stream</div>
                            </div>

                            {/* Category 2: Device */}
                            <div 
                                className={`quick-option ${currentSource === '0' ? 'active' : ''}`} 
                                onClick={() => onSetSource('0')}
                            >
                                <div className="option-icon"><Camera size={24} /></div>
                                <div className="option-label">2. Device Camera</div>
                                <div className="option-desc">System integrated webcam</div>
                            </div>

                            {/* Category 3: Local CCTV */}
                            <div 
                                className={`quick-option ${isLocalCCTV ? 'active' : ''}`} 
                                onClick={() => document.getElementById('smart-connect-form')?.scrollIntoView({ behavior: 'smooth' })}
                            >
                                <div className="option-icon"><Wifi size={24} /></div>
                                <div className="option-label">3. CCTV (Local)</div>
                                <div className="option-desc">Auto-discovery via WiFi</div>
                            </div>
                        </div>
                    </section>

                    <section className="connector-card" id="smart-connect-form">
                        <div className="card-header">
                            <Shield size={20} className="icon-blue" />
                            <h2>Category 3: Smart Connect (Local CCTV)</h2>
                        </div>
                        <p className="section-desc">App will scan your local network and auto-connect to found cameras using these credentials.</p>
                        
                        <div className="smart-connect-form">
                            <div className="input-group">
                                <label>Username</label>
                                <input 
                                    type="text" 
                                    value={username} 
                                    onChange={(e) => setUsername(e.target.value)} 
                                    placeholder="e.g. admin"
                                />
                            </div>
                            <div className="input-group">
                                <label>Password</label>
                                <div className="password-input-container">
                                    <input 
                                        type={showPassword ? "text" : "password"} 
                                        value={password} 
                                        onChange={(e) => setPassword(e.target.value)} 
                                        placeholder="e.g. Mohit@123"
                                    />
                                    <button 
                                        type="button"
                                        className="password-toggle"
                                        onClick={() => setShowPassword(!showPassword)}
                                    >
                                        {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                                    </button>
                                </div>
                            </div>
                            <button 
                                className={`scan-btn ${smartConnectLoading ? 'scanning' : ''}`}
                                onClick={handleSmartConnect}
                                disabled={smartConnectLoading}
                            >
                                {smartConnectLoading ? <Loader2 className="spin" size={18} /> : <Search size={18} />}
                                {smartConnectLoading ? 'Probing Network...' : 'Discover & Auto-Connect'}
                            </button>
                        </div>
                    </section>
                </div>

                {/* Right: Manual & Active Source */}
                <div className="connector-right-col">
                    <section className="connector-card">
                        <div className="card-header">
                            <Globe2 size={20} className="icon-purple" />
                            <h2>Remote Sites (Onsite Hubs)</h2>
                            <a 
                                href="/api/onsite/static/OnsiteAgent.exe" 
                                className="download-onsite-btn"
                                title="Download the Onsite Windows Agent"
                            >
                                <Monitor size={16} />
                                Download Onsite
                            </a>
                        </div>
                        <div className="manual-input-area">
                            <p className="section-desc">Active Onsite Hubs (Bridge your local cams with Onsite software):</p>
                            <div className="registered-sites-list">
                                {sites.length === 0 ? (
                                    <p className="empty-sites-msg">No Onsite agents active yet.</p>
                                ) : (
                                    sites.map((site, i) => {
                                        const isNative = site.remote_url.startsWith('yantrai://') || site.site_id;
                                        const siteSource = site.site_id ? `native://${site.site_id}` : site.remote_url;
                                        
                                        return (
                                            <div key={i} className={`site-item ${currentSource === siteSource ? 'active-site' : ''}`}>
                                                <div className="site-info">
                                                    <span className="site-name">
                                                        {isNative ? '🚀 ' : '🏠 '}
                                                        {site.site_name}
                                                    </span>
                                                    <span className="site-url">
                                                        {isNative ? 'Native Bridge' : site.remote_url}
                                                    </span>
                                                </div>
                                                <button className="site-connect-btn" onClick={() => onSetSource(siteSource)}>
                                                    {currentSource === siteSource ? 'Active' : 'Connect'}
                                                </button>
                                            </div>
                                        );
                                    })
                                )}
                            </div>

                            <hr style={{ margin: '15px 0', border: '0', borderTop: '1px solid #334155' }} />
                            
                            <p className="section-desc">Manual Entry (RTSP or Onsite Bridge):</p>
                            <input 
                                type="text" 
                                placeholder="native://site-id OR rtsp://admin:pass@ip:port/..."
                                value={manualUrl}
                                onChange={(e) => setManualUrl(e.target.value)}
                            />
                            <button 
                                className="apply-btn"
                                onClick={handleManualConnect}
                            >
                                <Globe size={16} />
                                Connect Manual / Onsite Link
                            </button>
                            <p className="hint-text" style={{ fontSize: '11px', color: '#8892b0', marginTop: '8px' }}>
                                💡 Tip: Copy the "Connection Link" from the Onsite app (e.g. <code>native://abcd-1234</code>) and paste it here.
                            </p>
                        </div>
                    </section>

                    <section className="connector-card active-source-card">
                        <div className="card-header">
                            <CheckCircle2 size={20} className="icon-green" />
                            <h2>Active Integration</h2>
                            <button 
                                className="refresh-btn"
                                onClick={() => onSetSource(currentSource)}
                                title="Refresh stream"
                            >
                                <RefreshCw size={16} />
                            </button>
                        </div>
                        <div className="active-source-display">
                            <div className="source-tag">
                                {currentSource === '0' ? 'DEVICE_CAMERA' : 
                                 (currentSource.includes('google') ? 'SAMPLE_VIDEO' : 
                                 (currentSource.startsWith('native://') ? 'YANTRAI_BRIDGE' : 'NETWORK_STREAM'))}
                            </div>
                            
                            <div className="connector-preview-area">
                                {frame ? (
                                    <div className="mini-preview-container">
                                        <img src={frame} alt="Live Stream" className="mini-video-feed" />
                                        <div className="live-indicator">
                                            <span className="pulse-dot"></span>
                                            LIVE
                                        </div>
                                    </div>
                                ) : (
                                    <div className="mini-preview-placeholder">
                                        <Monitor size={32} />
                                        <p>No active stream</p>
                                    </div>
                                )}
                            </div>

                            <code className="source-url">
                                {currentSource === '0' ? 'Integrated Webcam' : 
                                 (currentSource === 'http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4' ? 'Cloud Sample Video' : 
                                 (currentSource.startsWith('native://') ? 'Native Bridge Tunnel' : currentSource))}
                            </code>
                        </div>
                    </section>
                </div>
            </div>
        </div>
    );
}

export default Connector;
