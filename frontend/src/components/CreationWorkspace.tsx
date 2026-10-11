import { useEffect, useState } from 'react';
import type { CreationSession, ImageResult } from '../types';
import { apiService } from '../services/apiService';
import { Download, RefreshCcw, AlertTriangle, CheckCircle, Search, Info, ChevronLeft, ChevronRight, Maximize2, X, ZoomIn, ZoomOut, FileText } from 'lucide-react';

interface CreationWorkspaceProps {
  session: CreationSession;
  onUpdateSession: (session: CreationSession | ((prev: CreationSession) => CreationSession)) => void;
  onCreateAnother: () => void;
}

const startedSessions = new Set<string>(); // stops React dev mode from starting the same session twice

export function CreationWorkspace({ session, onUpdateSession, onCreateAnother }: CreationWorkspaceProps) {
  const [, setIsProcessing] = useState(false);
  const [error, setError] = useState('');
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [zoomLevel, setZoomLevel] = useState(1);
  const [showPdfExport, setShowPdfExport] = useState(false);
  const handleDownloadAll = () => {
    if (!session.planId) return;
    const a = document.createElement('a');
    a.href = apiService.imagesZipUrl(session.planId);
    a.download = `educreate-${session.planId}-images.zip`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  useEffect(() => {
    setCurrentIndex(0);
  }, [session.id]);

  useEffect(() => {
    // If the session has no images or all are ready, start processing
    if ((!session.images || session.images.length === 0 || session.images.every(i => i.status === 'Ready')) && !startedSessions.has(session.id)) {
      startedSessions.add(session.id);
      startProcessing();
    }
  }, [session.id]);

  const startProcessing = async () => {
    setIsProcessing(true);
    setError('');
    try {
      const result = await apiService.processImages(
        session,
        (updatedImages) => {
          onUpdateSession(prev => ({ ...prev, images: updatedImages }));
        },
        (p) => onUpdateSession(prev => ({ ...prev, planId: p.planId, tier: p.tier, colourMode: p.colourMode }))
      );
      onUpdateSession(prev => ({ ...prev, metrics: result.metrics, planId: result.planId, tier: result.tier, colourMode: result.colourMode }));
    } catch (err: any) {
      setError(err.message || 'An error occurred during processing.');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDownload = async (url: string, id: string) => {
    try {
      const blob = await (await fetch(url)).blob();
      const href = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = href;
      a.download = `educreate-${id}.png`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(href);
    } catch {
      setError('Download failed. Please try again.');
    }
  };

  const [pdfBusy, setPdfBusy] = useState(false);
  const handleExportPdf = async () => {
    if (!session.planId) return;
    setPdfBusy(true);
    setError('');
    try {
      const url = await apiService.exportPdf(session.planId);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${session.planId}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setShowPdfExport(false);
    } catch (e: any) {
      setError(e.message?.includes('409') ? 'The PDF can only be made when every image is completed. Retry the failed ones first.' : (e.message || 'PDF export failed.'));
    } finally {
      setPdfBusy(false);
    }
  };

  const renderStatusBadge = (status: ImageResult['status']) => {
    switch (status) {
      case 'Checking': return <span className="badge badge-info"><Search size={12} style={{ marginRight: 4, display: 'inline' }} /> Checking library...</span>;
      case 'Generating': return <span className="badge badge-info"><RefreshCcw size={12} className="spin" style={{ marginRight: 4, display: 'inline' }} /> Generating...</span>;
      case 'Completed': return <span className="badge badge-success"><CheckCircle size={12} style={{ marginRight: 4, display: 'inline' }} /> Completed</span>;
      case 'Failed':
      case 'Error': return <span className="badge badge-warning"><AlertTriangle size={12} style={{ marginRight: 4, display: 'inline' }} /> Failed</span>;
      default: return <span className="badge badge-info">Waiting...</span>;
    }
  };

  return (
    <div className="workspace animate-fade-in">
      <div className="full-container">
        
        <div style={{ display: 'flex', gap: '2rem', flexDirection: 'row', flexWrap: 'wrap' }}>
          
          <div style={{ flex: '1 1 300px' }}>
            <h2 style={{ marginBottom: '1.5rem', color: 'var(--accent-primary)' }}>Creation Results</h2>
            
            <div className="card" style={{ marginBottom: '2rem' }}>
              <h3 style={{ fontSize: '1rem', marginBottom: '1rem' }}>Request Details</h3>
              <p style={{ margin: 0 }}><strong>Prompt:</strong> {session.prompt}</p>
              <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem', fontSize: '0.875rem' }}>
                <span className="badge" style={{ backgroundColor: 'var(--bg-color)' }}>{session.category}</span>
                <span className="badge" style={{ backgroundColor: 'var(--bg-color)' }}>{session.ageGroup}</span>
                <span className="badge" style={{ backgroundColor: 'var(--bg-color)' }}>Qty: {session.quantity}</span>
                {session.tier && <span className="badge" style={{ backgroundColor: 'var(--bg-color)' }}>Quality: {session.tier}</span>}
                {session.colourMode && <span className="badge" style={{ backgroundColor: 'var(--bg-color)' }}>{session.colourMode === 'outline' ? 'Black & white outline' : 'Colour'}</span>}
              </div>
            </div>

            {session.metrics && (
              <div className="card" style={{ backgroundColor: 'var(--selected-bg)', borderColor: 'transparent' }}>
                <h3 style={{ fontSize: '1rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Info size={16} />
                  Session Usage Summary
                </h3>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', fontSize: '0.875rem' }}>
                  <div>
                    <span style={{ color: 'var(--text-secondary)' }}>Generated:</span>
                    <strong style={{ display: 'block' }}>{session.metrics.generated} images</strong>
                  </div>
                  <div>
                    <span style={{ color: 'var(--text-secondary)' }}>Reused from library:</span>
                    <strong style={{ display: 'block', color: 'var(--success-color)' }}>{session.metrics.reused} images</strong>
                  </div>
                  <div>
                    <span style={{ color: 'var(--text-secondary)' }}>Resource Usage:</span>
                    <strong style={{ display: 'block' }}>{session.metrics.resourceUsage}</strong>
                  </div>
                  <div>
                    <span style={{ color: 'var(--text-secondary)' }}>Estimated Cost:</span>
                    <strong style={{ display: 'block' }}>{session.metrics.estimatedCost}</strong>
                  </div>
                  <div>
                    <span style={{ color: 'var(--text-secondary)' }}>Time saved vs maximum:</span>
                    <strong style={{ display: 'block' }}>{session.metrics.timeSavingPercent != null ? `${session.metrics.timeSavingPercent}%` : '-'}</strong>
                  </div>
                  <div>
                    <span style={{ color: 'var(--text-secondary)' }}>Resources Saved:</span>
                    <strong style={{ display: 'block', color: 'var(--success-color)' }}>{session.metrics.savings}</strong>
                  </div>
                </div>
              </div>
            )}
            
            <div style={{ marginTop: '2rem' }}>
              <button className="btn btn-primary" onClick={onCreateAnother} style={{ width: '100%' }}>
                <Plus size={18} /> Create Another
              </button>
            </div>
            
            {session.images.some(img => img.status === 'Completed') && (
              <div style={{ marginTop: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <button className="btn btn-secondary" onClick={handleDownloadAll} style={{ width: '100%', justifyContent: 'center' }}>
                  <Download size={18} /> Download All Completed
                </button>
                <button className="btn btn-secondary" onClick={() => setShowPdfExport(true)} style={{ width: '100%', justifyContent: 'center' }}>
                  <FileText size={18} /> Export to PDF
                </button>
              </div>
            )}
          </div>

          <div style={{ flex: '2 1 600px' }}>
            {error && (
              <div className="card" style={{ backgroundColor: 'rgba(166, 107, 36, 0.1)', borderColor: 'var(--warning-color)', marginBottom: '1.5rem' }}>
                <p style={{ color: 'var(--warning-color)', margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <AlertTriangle size={18} /> {error}
                </p>
              </div>
            )}
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: 0 }}>
              {session.images.length > 0 && (() => {
                const img = session.images[currentIndex];
                if (!img) return null;
                
                return (
                  <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
                    <div style={{ position: 'relative' }}>
                      {img.url ? (
                        <img src={img.url} alt="Result" className="image-preview" style={{ maxHeight: '400px', objectFit: 'contain', backgroundColor: 'var(--bg-color)' }} />
                      ) : (
                        <div className="image-preview skeleton" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)', height: '300px' }}>
                          {img.status === 'Failed' ? <AlertTriangle size={32} /> : 'Processing...'}
                        </div>
                      )}
                      
                      {session.images.length > 1 && (
                        <>
                          <button 
                            className="btn-icon" 
                            style={{ position: 'absolute', left: '1rem', top: '50%', transform: 'translateY(-50%)', backgroundColor: 'var(--surface-color)', boxShadow: '0 2px 8px rgba(0,0,0,0.1)' }}
                            onClick={() => setCurrentIndex(i => Math.max(0, i - 1))}
                            disabled={currentIndex === 0}
                            aria-label="Previous image"
                          >
                            <ChevronLeft size={24} />
                          </button>
                          
                          <button 
                            className="btn-icon" 
                            style={{ position: 'absolute', right: '1rem', top: '50%', transform: 'translateY(-50%)', backgroundColor: 'var(--surface-color)', boxShadow: '0 2px 8px rgba(0,0,0,0.1)' }}
                            onClick={() => setCurrentIndex(i => Math.min(session.images.length - 1, i + 1))}
                            disabled={currentIndex === session.images.length - 1}
                            aria-label="Next image"
                          >
                            <ChevronRight size={24} />
                          </button>
                          
                          <div style={{ position: 'absolute', bottom: '1rem', right: '1rem', backgroundColor: 'rgba(0,0,0,0.6)', color: 'white', padding: '0.25rem 0.75rem', borderRadius: '12px', fontSize: '0.875rem', fontWeight: 500 }}>
                            {currentIndex + 1} of {session.images.length}
                          </div>
                        </>
                      )}
                      
                      {img.url && (
                        <button 
                          className="btn-icon" 
                          style={{ position: 'absolute', top: '1rem', right: '1rem', backgroundColor: 'rgba(255,255,255,0.8)' }}
                          onClick={() => { setIsFullscreen(true); setZoomLevel(1); }}
                          title="View Fullscreen"
                        >
                          <Maximize2 size={20} />
                        </button>
                      )}
                    </div>
                    
                    <div className="image-details" style={{ padding: '1.5rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <div>
                          <div className="image-status" style={{ marginBottom: '0.75rem' }}>
                            {renderStatusBadge(img.status)}
                          </div>
                          
                          {img.isRetrieved && (
                            <p style={{ fontSize: '0.875rem', color: 'var(--success-color)', margin: '0 0 0.5rem 0' }}>
                              Retrieved from existing library
                            </p>
                          )}
                          
                          {img.status === 'Completed' && !img.isRetrieved && (
                            <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', margin: '0 0 0.5rem 0' }}>
                              New image created
                            </p>
                          )}

                          {img.errorMessage && (
                            <p style={{ fontSize: '0.875rem', color: 'var(--warning-color)', margin: '0 0 0.5rem 0' }}>
                              {img.errorMessage}
                            </p>
                          )}
                        </div>
                        
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                          {img.status === 'Completed' && img.url && (
                            <button className="btn btn-secondary" onClick={() => handleDownload(img.url!, img.id)}>
                              <Download size={16} /> Download
                            </button>
                          )}
                          {img.status === 'Failed' && (
                            <button className="btn btn-primary" onClick={startProcessing}>
                              <RefreshCcw size={16} /> Retry
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })()}
              
              {session.images.length > 1 && (
                <div style={{ display: 'flex', gap: '0.5rem', overflowX: 'auto', paddingBottom: '0.5rem' }}>
                  {session.images.map((img, idx) => (
                    <button
                      key={img.id}
                      onClick={() => setCurrentIndex(idx)}
                      style={{ 
                        width: '64px', 
                        height: '64px', 
                        flexShrink: 0,
                        padding: 0,
                        border: currentIndex === idx ? '2px solid var(--accent-primary)' : '2px solid transparent',
                        borderRadius: '8px',
                        overflow: 'hidden',
                        cursor: 'pointer',
                        backgroundColor: 'var(--bg-color)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center'
                      }}
                    >
                      {img.url ? (
                        <img src={img.url} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                      ) : (
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{idx + 1}</span>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>
            
          </div>
        </div>

      </div>

      {isFullscreen && session.images[currentIndex]?.url && (
        <div className="modal-overlay fullscreen-modal">
          <div style={{ display: 'flex', justifyContent: 'space-between', padding: '1rem', backgroundColor: 'rgba(0,0,0,0.8)' }}>
            <div style={{ display: 'flex', gap: '1rem', color: 'white', alignItems: 'center' }}>
              <span style={{ fontSize: '0.875rem' }}>{currentIndex + 1} of {session.images.length}</span>
              <button className="btn-icon" style={{ color: 'white' }} onClick={() => setZoomLevel(Math.max(0.5, zoomLevel - 0.25))}>
                <ZoomOut size={20} />
              </button>
              <span style={{ fontSize: '0.875rem' }}>{Math.round(zoomLevel * 100)}%</span>
              <button className="btn-icon" style={{ color: 'white' }} onClick={() => setZoomLevel(Math.min(3, zoomLevel + 0.25))}>
                <ZoomIn size={20} />
              </button>
              <button className="btn btn-primary" style={{ padding: '0.25rem 0.75rem' }} onClick={() => setZoomLevel(1)}>
                Reset
              </button>
            </div>
            <div style={{ display: 'flex', gap: '1rem' }}>
              <button className="btn btn-secondary" style={{ backgroundColor: 'white', color: 'black' }} onClick={() => handleDownload(session.images[currentIndex].url!, session.images[currentIndex].id)}>
                <Download size={18} /> Download
              </button>
              <button className="btn-icon" style={{ color: 'white' }} onClick={() => setIsFullscreen(false)}>
                <X size={24} />
              </button>
            </div>
          </div>
          
          <div className="fullscreen-img-container">
            <img 
              src={session.images[currentIndex].url} 
              alt="Fullscreen view" 
              style={{ transform: `scale(${zoomLevel})`, transition: 'transform 0.2s', maxHeight: '100%', maxWidth: '100%', objectFit: 'contain' }} 
            />
            
            {session.images.length > 1 && (
              <>
                <button 
                  className="btn-icon" 
                  style={{ position: 'absolute', left: '2rem', top: '50%', transform: 'translateY(-50%)', backgroundColor: 'rgba(255,255,255,0.8)' }}
                  onClick={() => { setCurrentIndex(i => Math.max(0, i - 1)); setZoomLevel(1); }}
                  disabled={currentIndex === 0}
                >
                  <ChevronLeft size={32} />
                </button>
                <button 
                  className="btn-icon" 
                  style={{ position: 'absolute', right: '2rem', top: '50%', transform: 'translateY(-50%)', backgroundColor: 'rgba(255,255,255,0.8)' }}
                  onClick={() => { setCurrentIndex(i => Math.min(session.images.length - 1, i + 1)); setZoomLevel(1); }}
                  disabled={currentIndex === session.images.length - 1}
                >
                  <ChevronRight size={32} />
                </button>
              </>
            )}
          </div>
        </div>
      )}

      {showPdfExport && (
        <div className="modal-overlay" onClick={() => setShowPdfExport(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
              <h2 style={{ margin: 0, fontSize: '1.25rem', color: 'var(--accent-primary)' }}>Export to PDF</h2>
              <button className="btn-icon" onClick={() => setShowPdfExport(false)}>
                <X size={20} />
              </button>
            </div>
            
            <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
              Export {session.images.filter(i => i.status === 'Completed').length} completed image(s) to a printable PDF document.
            </p>
            
            <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
              One finished image per page, in the page size of this material, followed by a resource page with neurons used, cost and the saving against maximum quality.
            </p>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem' }}>
              <button className="btn btn-secondary" onClick={() => setShowPdfExport(false)}>Cancel</button>
              <button className="btn btn-primary" disabled={pdfBusy || !session.planId} onClick={handleExportPdf}>
                <FileText size={18} /> Download PDF
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const Plus = ({ size }: { size: number }) => (
  <svg xmlns="http://www.w3.org/2000/svg" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
);
