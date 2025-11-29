import { useState, useEffect, useRef } from 'react';
import '../css/Documents.css';

interface Protocol {
  id: string;
  title: string;
  category: string;
  content: string;
  updated_at: string;
  keywords: string[];
}

interface DocumentStats {
  total_documents: number;
  total_protocols: number;
  categories: Record<string, number>;
}

interface VoiceNote {
  id: string;
  transcript: string;
  formatted_notes: string;
  timestamp: string;
  duration: number;
  status: 'recording' | 'processing' | 'completed' | 'error';
}

export default function Documents() {
  const [protocols, setProtocols] = useState<Protocol[]>([]);
  const [stats, setStats] = useState<DocumentStats | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  // Voice recording states
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [formattedNotes, setFormattedNotes] = useState('');
  const [recordingTime, setRecordingTime] = useState(0);
  const [voiceNotes, setVoiceNotes] = useState<VoiceNote[]>([]);
  const [recordingError, setRecordingError] = useState<string | null>(null);

  // Modal states
  const [showGenerateModal, setShowGenerateModal] = useState(false);
  const [showVoiceModal, setShowVoiceModal] = useState(false);
  const [generateParams, setGenerateParams] = useState({
    title: '',
    category: 'Treatment Guidelines',
    content_type: 'clinical_notes',
    patient_context: ''
  });

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    fetchData();
    loadVoiceNotes();
  }, []);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const fetchData = async () => {
    try {
      const statsResponse = await fetch('http://localhost:8000/api/v1/documents/stats');
      const statsData = await statsResponse.json();
      setStats(statsData);

      const protocolsResponse = await fetch('http://localhost:8000/api/v1/documents/protocols/list?limit=10');
      const protocolsData = await protocolsResponse.json();
      setProtocols(protocolsData.protocols || []);

      setIsLoading(false);
    } catch (error) {
      console.error('Error fetching documents:', error);
      setIsLoading(false);
    }
  };

  const loadVoiceNotes = () => {
    const saved = localStorage.getItem('voice_notes');
    if (saved) {
      setVoiceNotes(JSON.parse(saved));
    }
  };

  const saveVoiceNote = (note: VoiceNote) => {
    const updated = [note, ...voiceNotes];
    setVoiceNotes(updated);
    localStorage.setItem('voice_notes', JSON.stringify(updated));
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    try {
      const response = await fetch(`http://localhost:8000/api/v1/documents/protocols/search?query=${encodeURIComponent(searchQuery)}&limit=10`);
      const data = await response.json();
      setProtocols(data.protocols || []);
    } catch (error) {
      console.error('Error searching protocols:', error);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSearch();
  };

  // Voice Recording Functions
  const startRecording = async () => {
    try {
      setRecordingError(null);

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 44100
        }
      });

      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : MediaRecorder.isTypeSupported('audio/webm')
          ? 'audio/webm'
          : MediaRecorder.isTypeSupported('audio/mp4')
            ? 'audio/mp4'
            : 'audio/wav';

      console.log('Using MIME type:', mimeType);

      const mediaRecorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
          console.log('Audio chunk collected:', event.data.size, 'bytes');
        }
      };

      mediaRecorder.onstop = async () => {
        console.log('Recording stopped, processing...');

        if (timerRef.current) clearInterval(timerRef.current);
        stream.getTracks().forEach(track => track.stop());

        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });

        if (audioBlob.size === 0) {
          setRecordingError('Recording is empty. Please try again.');
          setIsProcessing(false);
          return;
        }

        console.log(`Audio blob created: ${audioBlob.size} bytes`);
        await processAudioToText(audioBlob, mimeType);
      };

      mediaRecorder.start(1000);
      setIsRecording(true);
      setRecordingTime(0);

      timerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);

    } catch (error: any) {
      console.error('Error starting recording:', error);
      setRecordingError(`Failed to access microphone: ${error.message}`);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      console.log('Stopping recording...');
      setIsProcessing(true);
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const processAudioToText = async (audioBlob: Blob, mimeType: string) => {
    setIsProcessing(true);
    setTranscript('');
    setFormattedNotes('');
    setRecordingError(null);

    try {
      const extension = mimeType.includes('webm') ? 'webm'
        : mimeType.includes('mp4') ? 'mp4'
          : 'wav';

      // Generate unique filename with timestamp
      const timestamp = Date.now();
      const uniqueFilename = `recording_${timestamp}.${extension}`;

      // Log audio blob details for debugging
      console.log('🎵 Audio Blob Details:', {
        size: audioBlob.size,
        type: audioBlob.type,
        timestamp: timestamp,
        filename: uniqueFilename
      });

      // Step 1: Transcribe audio
      const formData = new FormData();
      const audioFile = new File(
        [audioBlob],
        uniqueFilename,
        { type: mimeType }
      );

      formData.append('audio_file', audioFile);

      console.log('📤 Sending to backend:', {
        filename: audioFile.name,
        size: audioFile.size,
        type: audioFile.type,
        lastModified: audioFile.lastModified
      });

      const transcriptResponse = await fetch('http://localhost:8000/api/v1/voice/transcribe', {
        method: 'POST',
        body: formData
      });

      if (!transcriptResponse.ok) {
        const errorData = await transcriptResponse.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(errorData.detail || `Transcription failed: ${transcriptResponse.status}`);
      }

      const transcriptData = await transcriptResponse.json();
      console.log('📥 Transcription response:', transcriptData);

      const transcriptText = transcriptData.transcript || transcriptData.text || '';

      if (!transcriptText) {
        throw new Error('No transcript returned from server');
      }

      console.log('✅ Transcript received:', transcriptText.substring(0, 100) + '...');
      setTranscript(transcriptText);

      // Step 2: Format notes with AI
      let formatted = transcriptText; // Default to transcript

      console.log('🔄 Formatting transcript...');
      const formatResponse = await fetch('http://localhost:8000/api/v1/documents/format-clinical-notes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          transcript: transcriptText,
          note_type: 'clinical_notes'
        })
      });

      if (!formatResponse.ok) {
        console.warn('⚠️ Formatting failed, using raw transcript');
        formatted = transcriptText;
      } else {
        const formatData = await formatResponse.json();
        formatted = formatData.formatted_notes || formatData.content || transcriptText;
        console.log('✅ Formatted notes received:', formatted.substring(0, 100) + '...');
      }

      setFormattedNotes(formatted);

      // Save voice note with unique ID and current recording time
      const noteId = `note_${timestamp}_${Math.random().toString(36).substr(2, 9)}`;
      const note: VoiceNote = {
        id: noteId,
        transcript: transcriptText,
        formatted_notes: formatted,
        timestamp: new Date().toISOString(),
        duration: recordingTime,
        status: 'completed'
      };

      console.log('💾 Saving voice note:', {
        id: note.id,
        transcriptLength: transcriptText.length,
        formattedLength: formatted.length,
        duration: recordingTime
      });

      saveVoiceNote(note);
      console.log('✅ Voice note saved successfully');

    } catch (error: any) {
      console.error('❌ Error processing audio:', error);
      setRecordingError(error.message || 'Failed to process recording');
    } finally {
      setIsProcessing(false);
    }
  };

  const generateDocument = async () => {
    if (!generateParams.title.trim()) {
      alert('Please enter a document title');
      return;
    }

    setIsProcessing(true);

    try {
      const response = await fetch('http://localhost:8000/api/v1/documents/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(generateParams)
      });

      if (!response.ok) throw new Error('Document generation failed');

      const data = await response.json();

      const newProtocol: Protocol = {
        id: Date.now().toString(),
        title: generateParams.title,
        category: generateParams.category,
        content: data.content || data.document?.content || '',
        updated_at: new Date().toISOString(),
        keywords: data.keywords || []
      };

      setProtocols([newProtocol, ...protocols]);
      setShowGenerateModal(false);
      setGenerateParams({
        title: '',
        category: 'Treatment Guidelines',
        content_type: 'clinical_notes',
        patient_context: ''
      });

      alert('Document generated successfully!');

    } catch (error) {
      console.error('Error generating document:', error);
      alert('Failed to generate document. Please try again.');
    } finally {
      setIsProcessing(false);
    }
  };

  const exportToPDF = async (noteId: string) => {
    const note = voiceNotes.find(n => n.id === noteId);
    if (!note) {
      alert('Voice note not found');
      return;
    }

    try {
      console.log('Exporting PDF for note:', noteId);

      const requestBody = {
        title: `Clinical Notes - ${new Date(note.timestamp).toLocaleDateString()}`,
        content: note.formatted_notes,
        metadata: {
          date: note.timestamp,
          duration: note.duration
        }
      };

      console.log('PDF request:', requestBody);

      const response = await fetch('http://localhost:8000/api/v1/documents/export-pdf', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody)
      });

      console.log('PDF response status:', response.status);

      if (!response.ok) {
        const errorText = await response.text();
        console.error('PDF export error:', errorText);
        throw new Error(`PDF export failed: ${response.status} - ${errorText}`);
      }

      const blob = await response.blob();

      if (blob.size === 0) {
        throw new Error('PDF is empty');
      }

      console.log('PDF blob size:', blob.size);

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `clinical-notes-${Date.now()}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      alert('PDF exported successfully!');

    } catch (error: any) {
      console.error('Error exporting PDF:', error);
      alert(`Failed to export PDF: ${error.message}`);
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getTimeAgo = (dateString: string) => {
    const date = new Date(dateString);
    const seconds = Math.floor((new Date().getTime() - date.getTime()) / 1000);
    if (seconds < 60) return 'Just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)} hours ago`;
    const days = Math.floor(seconds / 86400);
    if (days === 1) return '1 day ago';
    if (days < 7) return `${days} days ago`;
    return new Date(dateString).toLocaleDateString();
  };

  const getCategoryIcon = (category: string) => {
    const lower = category.toLowerCase();
    if (lower.includes('emergency')) return '🚨';
    if (lower.includes('treatment') || lower.includes('medication')) return '💊';
    if (lower.includes('lab') || lower.includes('test')) return '🔬';
    if (lower.includes('surgery') || lower.includes('surgical')) return '🏥';
    if (lower.includes('cardiac') || lower.includes('heart')) return '❤️';
    if (lower.includes('respiratory')) return '🫁';
    return '📄';
  };

  return (
    <div className="container">
      <div className="header">
        <div className="header-content">
          <h1>📚 Documents & Protocols</h1>
          <p style={{ color: '#6B7280', marginTop: '8px' }}>
            AI-powered document management with voice transcription
          </p>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button
            className="btn btn-primary"
            onClick={() => setShowVoiceModal(true)}
          >
            🎤 Voice Notes
          </button>
          <button
            className="btn btn-primary"
            onClick={() => setShowGenerateModal(true)}
          >
            ✨ Generate
          </button>
        </div>
      </div>

      <div className="search-bar">
        <input
          type="text"
          placeholder="Search protocols and documents..."
          className="search-input"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyPress={handleKeyPress}
        />
        <button className="btn btn-primary" onClick={handleSearch}>
          Search
        </button>
      </div>

      {isLoading ? (
        <div style={{ textAlign: 'center', padding: '40px', color: '#6B7280' }}>
          Loading protocols...
        </div>
      ) : (
        <>
          <div className="categories-grid">
            {stats?.categories && Object.keys(stats.categories).length > 0 ? (
              Object.entries(stats.categories).map(([category, count]) => (
                <div key={category} className="category-card">
                  <div className="category-icon">{getCategoryIcon(category)}</div>
                  <div className="category-name">{category}</div>
                  <div className="doc-count">{count} protocol{count !== 1 ? 's' : ''}</div>
                </div>
              ))
            ) : (
              <>
                <div className="category-card">
                  <div className="category-icon">🚨</div>
                  <div className="category-name">Emergency Protocols</div>
                  <div className="doc-count">0 protocols</div>
                </div>
                <div className="category-card">
                  <div className="category-icon">💊</div>
                  <div className="category-name">Treatment Guidelines</div>
                  <div className="doc-count">0 protocols</div>
                </div>
                <div className="category-card">
                  <div className="category-icon">🔬</div>
                  <div className="category-name">Lab Procedures</div>
                  <div className="doc-count">0 protocols</div>
                </div>
              </>
            )}
          </div>

          <div className="panel">
            <h3>📄 Recent Protocols ({protocols.length})</h3>
            <div className="documents-list">
              {protocols.length === 0 ? (
                <div style={{ padding: '40px', textAlign: 'center', color: '#6B7280' }}>
                  <div style={{ fontSize: '48px', marginBottom: '16px' }}>📝</div>
                  <div style={{ fontSize: '18px', fontWeight: 500, marginBottom: '8px' }}>
                    No documents yet
                  </div>
                  <div style={{ fontSize: '14px' }}>
                    Generate documents with AI or record voice notes to get started
                  </div>
                </div>
              ) : (
                protocols.map((protocol) => (
                  <div key={protocol.id} className="doc-item">
                    <div className="doc-icon">{getCategoryIcon(protocol.category)}</div>
                    <div className="doc-info">
                      <div className="doc-title">{protocol.title}</div>
                      <div className="doc-meta">
                        {protocol.category} • Updated {getTimeAgo(protocol.updated_at)}
                        {protocol.keywords && protocol.keywords.length > 0 && (
                          <span> • {protocol.keywords.slice(0, 3).join(', ')}</span>
                        )}
                      </div>
                    </div>
                    <button className="btn">View</button>
                  </div>
                ))
              )}
            </div>
          </div>
        </>
      )}

      {/* Voice Notes Modal */}
      {showVoiceModal && (
        <div style={modalOverlayStyle} onClick={() => !isRecording && setShowVoiceModal(false)}>
          <div style={modalContentStyle} onClick={(e) => e.stopPropagation()}>
            <div style={modalHeaderStyle}>
              <h2 style={{ margin: 0, fontSize: '20px' }}>🎤 Voice Clinical Notes</h2>
              <button
                style={closeBtnStyle}
                onClick={() => !isRecording && setShowVoiceModal(false)}
                disabled={isRecording}
              >
                ×
              </button>
            </div>

            <div style={{ padding: '24px' }}>
              {recordingError && (
                <div style={{
                  background: '#fee2e2',
                  border: '1px solid #ef4444',
                  borderRadius: '8px',
                  padding: '12px',
                  marginBottom: '16px',
                  color: '#991b1b'
                }}>
                  ⚠️ {recordingError}
                </div>
              )}

              <div style={{ textAlign: 'center', padding: '32px', background: '#f9fafb', borderRadius: '12px' }}>
                {!isRecording && !isProcessing && (
                  <>
                    <div style={{ fontSize: '64px', marginBottom: '16px' }}>🎤</div>
                    <div style={{ fontSize: '18px', fontWeight: 600, marginBottom: '8px' }}>
                      Ready to Record
                    </div>
                    <div style={{ fontSize: '14px', color: '#6B7280', marginBottom: '24px' }}>
                      Click start to begin voice dictation
                    </div>
                    <button
                      className="btn btn-primary"
                      onClick={startRecording}
                      style={{ padding: '12px 32px', fontSize: '16px' }}
                    >
                      🔴 Start Recording
                    </button>
                  </>
                )}

                {isRecording && (
                  <>
                    <div style={{ fontSize: '64px', marginBottom: '16px', animation: 'pulse 1.5s ease-in-out infinite' }}>🔴</div>
                    <div style={{ fontSize: '24px', fontWeight: 600, marginBottom: '8px', color: '#ef4444' }}>
                      Recording...
                    </div>
                    <div style={{ fontSize: '32px', fontFamily: 'monospace', marginBottom: '24px' }}>
                      {formatTime(recordingTime)}
                    </div>
                    <button
                      className="btn"
                      onClick={stopRecording}
                      style={{ padding: '12px 32px', fontSize: '16px', background: '#ef4444', color: 'white', border: 'none' }}
                    >
                      ⏹️ Stop Recording
                    </button>
                  </>
                )}

                {isProcessing && (
                  <>
                    <div style={{ fontSize: '64px', marginBottom: '16px', animation: 'spin 2s linear infinite' }}>⚙️</div>
                    <div style={{ fontSize: '18px', fontWeight: 600, marginBottom: '8px' }}>
                      Processing Audio...
                    </div>
                    <div style={{ fontSize: '14px', color: '#6B7280' }}>
                      Transcribing and formatting your notes with AI
                    </div>
                  </>
                )}
              </div>

              {transcript && (
                <div style={{ marginTop: '24px' }}>
                  <h4 style={{ marginBottom: '8px' }}>📝 Raw Transcript:</h4>
                  <div style={{
                    padding: '12px',
                    background: '#f3f4f6',
                    borderRadius: '8px',
                    fontSize: '14px',
                    maxHeight: '150px',
                    overflowY: 'auto'
                  }}>
                    {transcript}
                  </div>

                  {formattedNotes && (
                    <div style={{ marginTop: '16px' }}>
                      <h4 style={{ marginBottom: '8px' }}>✨ AI-Formatted Clinical Notes:</h4>
                      <div style={{
                        padding: '16px',
                        background: '#ffffff',
                        border: '2px solid #10b981',
                        borderRadius: '8px',
                        fontSize: '14px',
                        whiteSpace: 'pre-wrap',
                        maxHeight: '300px',
                        overflowY: 'auto'
                      }}>
                        {formattedNotes}
                      </div>
                      <div style={{ marginTop: '16px', display: 'flex', gap: '12px' }}>
                        <button
                          className="btn btn-primary"
                          onClick={() => {
                            navigator.clipboard.writeText(formattedNotes);
                            alert('Copied to clipboard!');
                          }}
                        >
                          📋 Copy Notes
                        </button>
                        <button
                          className="btn"
                          onClick={() => {
                            // Export the current recording (most recent)
                            if (voiceNotes.length > 0) {
                              exportToPDF(voiceNotes[0].id);
                            }
                          }}
                        >
                          📄 Export PDF
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {voiceNotes.length > 0 && (
                <div style={{ marginTop: '32px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                    <h4 style={{ margin: 0 }}>📚 Previous Voice Notes ({voiceNotes.length})</h4>
                    <button
                      className="btn"
                      onClick={() => {
                        if (confirm('Clear all voice notes?')) {
                          localStorage.removeItem('voice_notes');
                          setVoiceNotes([]);
                          alert('Voice notes cleared!');
                        }
                      }}
                      style={{ padding: '4px 12px', fontSize: '12px', background: '#ef4444', color: 'white', border: 'none' }}
                    >
                      🗑️ Clear All
                    </button>
                  </div>
                  <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
                    {voiceNotes.slice(0, 5).map((note) => (
                      <div
                        key={note.id}
                        style={{
                          padding: '12px',
                          background: '#f9fafb',
                          borderRadius: '8px',
                          marginBottom: '8px',
                          border: '1px solid #e5e7eb'
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', alignItems: 'center' }}>
                          <span style={{ fontSize: '12px', color: '#6B7280' }}>
                            {getTimeAgo(note.timestamp)} • {formatTime(note.duration)}
                          </span>
                          <button
                            className="btn"
                            onClick={() => {
                              console.log('Exporting note:', note.id);
                              exportToPDF(note.id);
                            }}
                            style={{ padding: '4px 12px', fontSize: '12px' }}
                          >
                            📄 PDF
                          </button>
                        </div>
                        <div style={{
                          fontSize: '11px',
                          color: '#9ca3af',
                          marginBottom: '4px',
                          fontFamily: 'monospace'
                        }}>
                          ID: {note.id.substring(0, 20)}...
                        </div>
                        <div style={{
                          fontSize: '13px',
                          color: '#374151',
                          maxHeight: '60px',
                          overflow: 'hidden',
                          lineHeight: '1.4'
                        }}>
                          <strong>Transcript:</strong> {note.transcript.substring(0, 80)}...
                          <br />
                          <strong>Formatted:</strong> {note.formatted_notes.substring(0, 80)}...
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Generate Document Modal */}
      {showGenerateModal && (
        <div style={modalOverlayStyle} onClick={() => setShowGenerateModal(false)}>
          <div style={modalContentStyle} onClick={(e) => e.stopPropagation()}>
            <div style={modalHeaderStyle}>
              <h2 style={{ margin: 0, fontSize: '20px' }}>✨ AI Document Generation</h2>
              <button style={closeBtnStyle} onClick={() => setShowGenerateModal(false)}>×</button>
            </div>

            <div style={{ padding: '24px' }}>
              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: 600, fontSize: '14px' }}>
                  Document Title
                </label>
                <input
                  type="text"
                  className="search-input"
                  placeholder="e.g., Post-Operative Care Protocol"
                  value={generateParams.title}
                  onChange={(e) => setGenerateParams({ ...generateParams, title: e.target.value })}
                />
              </div>

              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: 600, fontSize: '14px' }}>
                  Category
                </label>
                <select
                  className="search-input"
                  value={generateParams.category}
                  onChange={(e) => setGenerateParams({ ...generateParams, category: e.target.value })}
                >
                  <option>Treatment Guidelines</option>
                  <option>Emergency Protocols</option>
                  <option>Lab Procedures</option>
                  <option>Surgical Protocols</option>
                  <option>Medication Guidelines</option>
                </select>
              </div>

              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: 600, fontSize: '14px' }}>
                  Additional Context (Optional)
                </label>
                <textarea
                  className="search-input"
                  rows={4}
                  placeholder="Provide any specific requirements..."
                  value={generateParams.patient_context}
                  onChange={(e) => setGenerateParams({ ...generateParams, patient_context: e.target.value })}
                  style={{ resize: 'vertical' }}
                />
              </div>

              <button
                className="btn btn-primary"
                onClick={generateDocument}
                disabled={isProcessing}
                style={{ width: '100%' }}
              >
                {isProcessing ? '⚙️ Generating...' : '✨ Generate Document'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Inline styles for modals
const modalOverlayStyle: React.CSSProperties = {
  position: 'fixed',
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  background: 'rgba(0, 0, 0, 0.5)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  zIndex: 1000,
  padding: '20px'
};

const modalContentStyle: React.CSSProperties = {
  background: 'white',
  borderRadius: '16px',
  maxWidth: '700px',
  width: '100%',
  maxHeight: '90vh',
  overflowY: 'auto',
  boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)'
};

const modalHeaderStyle: React.CSSProperties = {
  padding: '24px',
  borderBottom: '1px solid #e5e7eb',
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center'
};

const closeBtnStyle: React.CSSProperties = {
  background: 'none',
  border: 'none',
  fontSize: '28px',
  cursor: 'pointer',
  color: '#6B7280',
  width: '32px',
  height: '32px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  borderRadius: '4px'
};