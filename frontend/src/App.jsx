import React, { useState, useEffect, useRef } from 'react';
import { Camera, Send, MessageSquare, Activity, Shield, Settings, FileText, Save, Menu, X, Link2, User } from 'lucide-react';
import { Routes, Route, Link, useLocation, useNavigate } from 'react-router-dom';
import { NativeBiometric } from '@capgo/capacitor-native-biometric';
import { App as CapApp } from '@capacitor/app';
import { PushNotifications } from '@capacitor/push-notifications';
import Connector from './Connector';

// Auto-detect backend URL - Fixed to live cloud for standalone testing
const isDev = false;
const API_BASE = 'https://yantrai-cloud-hub.web.app';
const WS_BASE = 'wss://yantrai-cloud-hub.web.app';

function App() {
  const [error, setError] = useState(null);

  // Global Error Handler for Mobile
  useEffect(() => {
    const handleError = (e) => {
      console.error("CRITICAL ERROR:", e);
      setError(e.message || "Unknown Runtime Error");
    };
    window.addEventListener('error', handleError);
    window.addEventListener('unhandledrejection', (e) => handleError(e.reason));
    return () => {
      window.removeEventListener('error', handleError);
    };
  }, []);

  if (error) {
    return (
      <div style={{ background: '#7f1d1d', color: '#fca5a5', padding: '20px', height: '100vh', fontFamily: 'monospace', overflow: 'auto' }}>
        <h1 style={{ fontSize: '1.5rem', marginBottom: '10px' }}>⚠️ YantrAI Safe Mode</h1>
        <p>The app crashed. Error details:</p>
        <pre style={{ background: '#450a0a', padding: '15px', borderRadius: '8px', marginTop: '10px', whiteSpace: 'pre-wrap' }}>
          {typeof error === 'object' ? JSON.stringify(error, null, 2) : String(error)}
        </pre>
        <button onClick={() => { setError(null); window.location.reload(); }} style={{ marginTop: '20px', padding: '10px 20px', background: '#dc2626', color: 'white', border: 'none', borderRadius: '4px' }}>
          Retry / Reload
        </button>
      </div>
    );
  }

  const location = useLocation();
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [logs, setLogs] = useState([]);
  const [models, setModels] = useState([]);
  const [inputText, setInputText] = useState('');
  const [isMotion, setIsMotion] = useState(false);
  const [frame, setFrame] = useState(null);
  const [isInferencing, setIsInferencing] = useState(false);
  
  const [activeTab, setActiveTab] = useState('logs'); // 'logs' | 'instr'
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);
  const [isLocked, setIsLocked] = useState(true);
  const [selectedCameraId, setSelectedCameraId] = useState('cam-01');
  const [instruction, setInstruction] = useState("Loading role...");
  const [loggingFrequency, setLoggingFrequency] = useState(15);
  const [activeSourceName, setActiveSourceName] = useState('Integrated Camera');
  const [activeSource, setActiveSource] = useState('0');
  const [sites, setSites] = useState([]);
  
  const activePage = (location.pathname === '/' || location.pathname === '/camera_trainer') ? 'trainer' : location.pathname.substring(1);
  
  // Fetch instruction when camera changes
  useEffect(() => {
    const fetchInstruction = async () => {
        try {
            const res = await fetch(`${API_BASE}/config/instruction/${selectedCameraId}`);
            if (res.ok) {
                const data = await res.json();
                setInstruction(data.instruction);
            }
        } catch (err) {
            console.error("Fetch instruction error:", err);
            setInstruction("Could not load role. Check server connection.");
        }
    };
    fetchInstruction();
  }, [selectedCameraId]);
  
  const videoWs = useRef(null);
  const chatWs = useRef(null);
  const messagesEndRef = useRef(null);
  const logsEndRef = useRef(null);
  const reconnectTimeout = useRef(null);

  useEffect(() => {
    // Fetch Model Status periodically
    const fetchStatus = async () => {
        try {
            const res = await fetch(`${API_BASE}/status`);
            const data = await res.json();
            setModels(data.models || []);
        } catch (err) {
            console.error("Status fetch error:", err);
        }
    };
    const interval = setInterval(fetchStatus, 3000);
    fetchStatus();
    return () => clearInterval(interval);
  }, []);

  // Fetch Logging Frequency on mount
  useEffect(() => {
    const fetchFrequency = async () => {
        try {
            const res = await fetch(`${API_BASE}/config/logging_frequency`);
            if (res.ok) {
                const data = await res.json();
                setLoggingFrequency(data.interval);
            }
        } catch (err) {
            console.error("Fetch frequency error:", err);
        }
    };
    fetchFrequency();
  }, []);

  // Fetch Active Source
  useEffect(() => {
    const fetchSource = async () => {
        try {
            const res = await fetch(`${API_BASE}/api/get_source`);
            if (res.ok) {
                const data = await res.json();
                const source = data.source;
                setActiveSource(source);
                if (source === '0') {
                    setActiveSourceName('Integrated Camera');
                } else if (source.includes('BigBuckBunny.mp4')) {
                    setActiveSourceName('Sample Video (Big Buck Bunny)');
                } else {
                    setActiveSourceName(source);
                }
            }
        } catch (err) {
            console.error("Fetch source error:", err);
        }
    };
    fetchSource();
    const interval = setInterval(fetchSource, 5000);
    return () => clearInterval(interval);
  }, []);

  // Fetch Sites
  useEffect(() => {
    const fetchSites = async () => {
        try {
            const res = await fetch(`${API_BASE}/api/agent/sites`);
            if (res.ok) {
                const data = await res.json();
                setSites(data.sites || []);
            }
        } catch (err) {
            console.error("Fetch sites error:", err);
        }
    };
    fetchSites();
    const interval = setInterval(fetchSites, 10000);
    return () => clearInterval(interval);
  }, []);

  // Mobile detection
  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Biometric Auth Handshake
  const performBiometricCheck = async () => {
    // Only lock if running inside the Android shell (detected via window.Capacitor)
    if (!window.Capacitor) {
        setIsLocked(false);
        return;
    }
    
    try {
        const result = await NativeBiometric.isAvailable();
        if (result.isAvailable) {
            await NativeBiometric.verifyIdentity({
                reason: "Identify yourself to access YantrAI",
                title: "Security Check",
                subtitle: "Biometric Authentication Required",
                description: "Authorize access to your surveillance hub",
            });
            setIsLocked(false);
        } else {
            setIsLocked(false); // Fallback if no biometrics are set up
        }
    } catch (err) {
        console.error("Biometric error:", err);
        // If user cancels or fails, stay locked
        setIsLocked(true);
    }
  };

  useEffect(() => {
    performBiometricCheck();
    
    // Re-lock on app resume - Commented out to prevent loops until state management is refined
    /*
    const resumeListener = CapApp.addListener('appRestoredResult', () => {
        setIsLocked(true);
        performBiometricCheck();
    });

    const stateListener = CapApp.addListener('appStateChange', ({ isActive }) => {
        if (isActive) {
            setIsLocked(true);
            performBiometricCheck();
        }
    });

    return () => {
        resumeListener.then(l => l.remove());
        stateListener.then(l => l.remove());
    };
    */
  }, []);

  // Push Notifications - Disabled temporarily due to missing google-services.json crash
  useEffect(() => {
    /*
    if (!window.Capacitor) return;

    // Request & Register
    const initPush = async () => {
        try {
            const perm = await PushNotifications.requestPermissions();
            if (perm.receive === 'granted') {
                await PushNotifications.register();
            }
        } catch (err) {
            console.warn("Push error (ignore if google-services.json is missing):", err);
        }
    };
    initPush();

    // Listeners
    const regListener = PushNotifications.addListener('registration', (token) => {
        console.log('Mobile Push Token:', token.value);
    });

    const pushListener = PushNotifications.addListener('pushNotificationReceived', (notification) => {
        console.log('Foreground Push:', notification);
    });

    const actionListener = PushNotifications.addListener('pushNotificationActionPerformed', (action) => {
        const data = action.notification.data;
        if (data.camera_id) {
            setSelectedCameraId(data.camera_id);
            setActiveTab('logs');
            navigate('/camera_trainer');
        }
    });

    return () => {
        regListener.then(l => l.remove());
        pushListener.then(l => l.remove());
        actionListener.then(l => l.remove());
    };
    */
  }, [navigate]);

  useEffect(() => {
    const connectWebSockets = () => {
        console.log("LOG: Attempting to connect WebSockets...");
        
        // Video Stream WebSocket
        videoWs.current = new WebSocket(`${WS_BASE}/ws/stream`);
        videoWs.current.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            setFrame(`data:image/jpeg;base64,${data.frame}`);
            setIsMotion(data.motion);
          } catch (err) {
            console.error("Video WS message error:", err);
          }
        };
        videoWs.current.onclose = () => {
            console.warn("Video WS closed. Retrying in 3s...");
            clearTimeout(reconnectTimeout.current);
            reconnectTimeout.current = setTimeout(connectWebSockets, 3000);
        };

        // Chat WebSocket
        chatWs.current = new WebSocket(`${WS_BASE}/ws/chat`);
        chatWs.current.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === 'log') {
              setLogs(prev => [...prev, { text: data.text, timestamp: data.timestamp }].slice(-50));
            } else {
              setMessages(prev => [...prev, { role: 'ai', text: data.text }]);
              setIsInferencing(false);
            }
          } catch (err) {
            console.error("Chat WS message error:", err);
            setIsInferencing(false);
          }
        };
        chatWs.current.onclose = () => {
            console.warn("Chat WS closed. Retrying in 3s...");
            clearTimeout(reconnectTimeout.current);
            reconnectTimeout.current = setTimeout(connectWebSockets, 3000);
        };
    };

    connectWebSockets();

    return () => {
      clearTimeout(reconnectTimeout.current);
      videoWs.current?.close();
      chatWs.current?.close();
    };
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs, activeTab]);

  const handleSetSource = async (url) => {
    try {
        const res = await fetch(`${API_BASE}/api/set_source`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ source: url })
        });
        if (res.ok) {
            setActiveSource(url);
            if (url === '0') {
                setActiveSourceName('Integrated Camera');
            } else if (url.includes('BigBuckBunny.mp4')) {
                setActiveSourceName('Sample Video (Big Buck Bunny)');
            } else {
                setActiveSourceName(url);
            }
            return true;
        }
    } catch (err) {
        console.error("Set source error:", err);
    }
    return false;
  };

  const handleSendMessage = () => {
    if (!inputText.trim()) return;

    const userMessage = { role: 'user', text: inputText };
    setMessages(prev => [...prev, userMessage]);
    
    if (chatWs.current?.readyState === WebSocket.OPEN) {
        setIsInferencing(true);
        chatWs.current.send(JSON.stringify({ text: inputText }));
    } else {
        setMessages(prev => [...prev, { role: 'ai', text: "Error: Chat server is not connected." }]);
    }
    setInputText('');
  };

  const handleSaveInstruction = async () => {
    try {
        const res = await fetch(`${API_BASE}/config/instruction`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ camera_id: selectedCameraId, instruction: instruction })
        });
        const data = await res.json();
        if (data.status === 'success') {
            alert('Instructions updated successfully!');
        }
    } catch (err) {
        console.error("Save instruction error:", err);
    }
  };

   const TrainerDashboard = () => (
    <div className={`dashboard-grid ${isMobile ? 'mobile-layout' : ''}`}>
        <div className="sidebar left">
          <div className="interaction-panel">
              {!isMobile && (
                <div className="panel-tabs">
                    <button 
                        className={`tab-btn ${activeTab === 'logs' ? 'active' : ''}`}
                        onClick={() => setActiveTab('logs')}
                    >
                        <Activity size={16} />
                        Logs
                    </button>
                    <button 
                        className={`tab-btn ${activeTab === 'instr' ? 'active' : ''}`}
                        onClick={() => setActiveTab('instr')}
                    >
                        <FileText size={16} />
                        Instructions
                    </button>
                </div>
              )}

              <div className="content-area">
                  {(activeTab === 'logs' || isMobile) && (
                      <section className="log-panel">
                          <div className="log-entries">
                              {logs.length === 0 ? (
                                  <div className="empty-state-small">
                                      <p>Waiting for observations...</p>
                                  </div>
                              ) : (
                                  [...logs].reverse().map((log, i) => (
                                      <div key={i} className="log-entry">
                                          <span className="log-time">{log.timestamp}</span>
                                          <span className="log-text">{log.text}</span>
                                      </div>
                                  ))
                              )}
                              <div ref={logsEndRef} />
                          </div>
                      </section>
                  )}

                  {(activeTab === 'instr' && !isMobile) && (
                      <section className="instruction-panel">
                          <div style={{ marginBottom: '12px', fontSize: '14px', color: 'var(--accent-secondary)' }}>
                              Editing Role for: {selectedCameraId.toUpperCase()}
                          </div>
                          <textarea 
                              value={instruction}
                              onChange={(e) => setInstruction(e.target.value)}
                              placeholder="Set AI observation role for this camera..."
                          />
                          
                          <div className="frequency-control">
                              <div className="frequency-label">
                                  <span>Observation Frequency: <strong>{loggingFrequency}s</strong></span>
                              </div>
                              <input 
                                  type="range" 
                                  min="5" 
                                  max="300" 
                                  step="5"
                                  value={loggingFrequency}
                                  onChange={(e) => setLoggingFrequency(parseInt(e.target.value))}
                                  onMouseUp={async () => {
                                      try {
                                          await fetch(`${API_BASE}/config/logging_frequency`, {
                                              method: 'POST',
                                              headers: { 'Content-Type': 'application/json' },
                                              body: JSON.stringify({ interval: loggingFrequency })
                                          });
                                      } catch (err) {
                                          console.error("Update frequency error:", err);
                                      }
                                  }}
                                  className="frequency-slider"
                              />
                              <div className="frequency-range">
                                  <span>5s</span>
                                  <span>5m</span>
                              </div>
                          </div>

                          <button className="save-btn" onClick={handleSaveInstruction}>
                              <Save size={18} />
                              Apply Instructions
                          </button>
                      </section>
                  )}
              </div>
          </div>
        </div>

        <main className="video-main">
          <div className="cctv-container">
              {/* Main Feed (Camera 1) */}
              <div 
                  className={`cctv-feed main-feed ${selectedCameraId === 'cam-01' ? 'active-camera' : ''}`}
                  onClick={() => setSelectedCameraId('cam-01')}
              >
                  <div className="cam-label">CAM 01 - {activeSourceName}</div>
                  {frame ? (
                      <img src={frame} alt="Video Feed" className="video-feed" />
                  ) : (
                      <div className="empty-state">
                          <Camera size={48} color="#475569" />
                          <p>Waiting for camera stream...</p>
                      </div>
                  )}
                  
                  {isMotion && (
                      <div className="motion-overlay">
                          <Activity size={16} />
                          <span>MOTION DETECTED</span>
                      </div>
                  )}
              </div>

              {/* Dummy Feeds (Cameras 2-24) */}
              {!isMobile && Array.from({ length: 23 }).map((_, i) => {
                  const cid = `cam-${String(i+2).padStart(2, '0')}`;
                  return (
                      <div 
                          key={cid} 
                          className={`cctv-feed dummy-feed ${selectedCameraId === cid ? 'active-camera' : ''}`}
                          onClick={() => setSelectedCameraId(cid)}
                      >
                          <div className="cam-label">CAM {String(i+2).padStart(2, '0')} - OFFLINE</div>
                          <div className="empty-state-small">
                              <Camera size={24} color="#334155" />
                          </div>
                      </div>
                  );
              })}
          </div>
        </main>
    </div>
  );

  if (isLocked && window.Capacitor) {
    return (
      <div className="lock-screen-overlay">
          <div className="lock-card">
              <Shield size={64} className="lock-icon" />
              <h2>System Locked</h2>
              <p>Authentication required to access YantrAI Hub</p>
              <button className="auth-btn" onClick={performBiometricCheck}>
                  Unlock with Biometrics
              </button>
          </div>
      </div>
    );
  }

  return (
    <div className={`app-container ${activePage}`}>
      {/* Drawer Overlay */}
      <div className={`drawer-overlay ${isDrawerOpen ? 'open' : ''}`} onClick={() => setIsDrawerOpen(false)} />
      
      {/* Drawer Menu */}
      <nav className={`drawer ${isDrawerOpen ? 'open' : ''}`}>
          <div className="drawer-header">
              <span className="drawer-title">Menu</span>
              <button className="close-drawer" onClick={() => setIsDrawerOpen(false)}><X size={20}/></button>
          </div>
          <div className="drawer-items">
              <Link to="/connector" className={`drawer-item ${activePage === 'connector' ? 'active' : ''}`} onClick={() => setIsDrawerOpen(false)}>
                  <Link2 size={18}/> Connector
              </Link>
              <Link to="/camera_trainer" className={`drawer-item ${activePage === 'trainer' ? 'active' : ''}`} onClick={() => setIsDrawerOpen(false)}>
                  <Camera size={18}/> Camera Trainer
              </Link>
              <Link to="/chat" className={`drawer-item ${activePage === 'chat' ? 'active' : ''}`} onClick={() => setIsDrawerOpen(false)}>
                  <MessageSquare size={18}/> Chat
              </Link>
              <Link to="/profile" className={`drawer-item ${activePage === 'profile' ? 'active' : ''}`} onClick={() => setIsDrawerOpen(false)}>
                  <User size={18}/> Profile
              </Link>
          </div>
      </nav>

      {/* Main Header */}
      <header className="header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            {!isMobile && (
                <button className="menu-btn" onClick={() => setIsDrawerOpen(true)}>
                    <Menu size={24} color="#f8fafc" />
                </button>
            )}
            <div className="logo">
              <Shield size={isMobile ? 22 : 28} />
              <span style={{ fontSize: isMobile ? '1.1rem' : 'inherit' }}>YantrAI Hub</span>
            </div>
        </div>
        
        <div className="status-bar">
            {models.map((m, i) => (
                <div key={i} className="status-badge">
                    <span className="dot" data-status={m.status}></span>
                    <span className="model-name">{m.name}</span>
                    <span className="model-status">
                        {m.status} 
                        {m.status === "Initializing" && m.progress > 0 && ` (${m.progress}%)`}
                    </span>
                </div>
            ))}
        </div>

        <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
            {isMotion && <span className="motion-dot"></span>}
            <Settings size={20} color="#94a3b8" />
        </div>
      </header>

      {/* Pages Content */}
      <div className="page-content">
        <Routes>
          <Route path="/" element={<Connector currentSource={activeSource} onSetSource={handleSetSource} frame={frame} sites={sites} />} />
          <Route path="/connector" element={<Connector currentSource={activeSource} onSetSource={handleSetSource} frame={frame} sites={sites} />} />
          <Route path="/camera_trainer" element={<TrainerDashboard />} />

          <Route path="/profile" element={
              <div className="placeholder-view">
                  <User size={48} color="#475569" />
                  <h2>Profile</h2>
                  <p>User settings coming soon.</p>
              </div>
          } />

          <Route path="/chat" element={
              <div className="standalone-chat-view">
                  <section className="chat-panel">
                        <div className="chat-messages">
                        {messages.length === 0 ? (
                            <div className="empty-state-small">
                            <p>Ask about the stream...</p>
                            </div>
                        ) : (
                            messages.map((msg, i) => (
                            <div key={i} className={`message ${msg.role}`}>
                                {msg.text}
                            </div>
                            ))
                        )}
                        {isInferencing && (
                            <div className="typing-indicator">
                                <div className="typing-dot"></div>
                                <div className="typing-dot"></div>
                                <div className="typing-dot"></div>
                            </div>
                        )}
                        <div ref={messagesEndRef} />
                        </div>

                        <div className="chat-input-area">
                            <input 
                                type="text" 
                                className="chat-input" 
                                placeholder="Type message..."
                                value={inputText}
                                onChange={(e) => setInputText(e.target.value)}
                                onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                            />
                            <button className="send-btn" onClick={handleSendMessage}>
                                <Send size={16} />
                            </button>
                        </div>
                    </section>
              </div>
          } />
        </Routes>
      </div>

      {/* Micro-UI: Bottom navigation for mobile */}
      {isMobile && (
        <nav className="mobile-nav">
            <Link to="/connector" className={`nav-item ${activePage === 'connector' ? 'active' : ''}`}>
                <Link2 />
                <span>Connector</span>
            </Link>
            <Link to="/camera_trainer" className={`nav-item ${activePage === 'trainer' ? 'active' : ''}`}>
                <Camera />
                <span>Dashboard</span>
            </Link>
            <Link to="/chat" className={`nav-item ${activePage === 'chat' ? 'active' : ''}`}>
                <MessageSquare />
                <span>AI Chat</span>
            </Link>
            <Link to="/profile" className={`nav-item ${activePage === 'profile' ? 'active' : ''}`}>
                <User />
                <span>Profile</span>
            </Link>
        </nav>
      )}
    </div>
  );
}

export default App;
