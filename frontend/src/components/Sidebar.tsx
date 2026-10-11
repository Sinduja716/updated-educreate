import { useState, useEffect, useCallback } from 'react';
import type { ViewState, CreationSession } from '../types';
import { Settings, MessageSquare, Search, MoreVertical, Trash2, Edit2, X, PanelLeftClose, PanelLeftOpen, Sparkles, Folder, History, Activity } from 'lucide-react';

interface SidebarProps {
  isOpen: boolean;
  isMobileOpen: boolean;
  onCloseMobile: () => void;
  viewState: ViewState;
  sessions: CreationSession[];
  onNavigate: (view: ViewState) => void;
  onNewCreation: () => void;
  onLoadSession: (session: CreationSession) => void;
  onRenameSession: (id: string, newTitle: string) => void;
  onDeleteSession: (id: string) => void;
  onGoHome: () => void;
  onToggleSidebar: () => void;
}

export function Sidebar({ isOpen, isMobileOpen, onCloseMobile, viewState, sessions, onNavigate, onNewCreation, onLoadSession, onRenameSession, onDeleteSession, onGoHome, onToggleSidebar }: SidebarProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [filterCategory, setFilterCategory] = useState<string>('All');
  const [contextMenuId, setContextMenuId] = useState<string | null>(null);
  
  const [sidebarWidth, setSidebarWidth] = useState(260);
  const [isResizing, setIsResizing] = useState(false);

  const startResizing = useCallback(() => {
    setIsResizing(true);
  }, []);

  const stopResizing = useCallback(() => {
    setIsResizing(false);
  }, []);

  const resize = useCallback(
    (mouseMoveEvent: MouseEvent) => {
      if (isResizing) {
        setSidebarWidth(mouseMoveEvent.clientX);
      }
    },
    [isResizing]
  );

  useEffect(() => {
    window.addEventListener("mousemove", resize);
    window.addEventListener("mouseup", stopResizing);
    return () => {
      window.removeEventListener("mousemove", resize);
      window.removeEventListener("mouseup", stopResizing);
    };
  }, [resize, stopResizing]);
  
  // Removed early return for desktop collapse
  if (!isOpen && !isMobileOpen && window.innerWidth < 768) return null;

  const filteredSessions = sessions.filter(s => {
    const matchesSearch = s.title.toLowerCase().includes(searchQuery.toLowerCase()) || 
                          s.prompt.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = filterCategory === 'All' || s.category === filterCategory;
    return matchesSearch && matchesCategory;
  });

  const handleRename = (id: string, currentTitle: string) => {
    const newTitle = prompt('Enter new title:', currentTitle);
    if (newTitle && newTitle.trim()) {
      onRenameSession(id, newTitle.trim());
    }
    setContextMenuId(null);
  };

  const handleDelete = (id: string) => {
    if (confirm('Are you sure you want to delete this conversation?')) {
      onDeleteSession(id);
    }
    setContextMenuId(null);
  };

  return (
    <>
      {isMobileOpen && (
        <div className="sidebar-overlay" onClick={onCloseMobile}></div>
      )}
      <aside 
        className={`sidebar ${isMobileOpen ? 'mobile-open' : ''} ${!isOpen && !isMobileOpen ? 'collapsed' : ''}`}
        style={{ 
          width: isMobileOpen ? undefined : (isOpen ? `${Math.max(200, Math.min(600, sidebarWidth))}px` : '64px'), 
          position: 'relative', 
          transition: isResizing ? 'none' : 'width 0.3s ease',
          overflow: 'hidden'
        }}
      >
        {isOpen && (
          <div 
            style={{ position: 'absolute', top: 0, right: 0, width: '4px', height: '100%', cursor: 'col-resize', background: isResizing ? 'var(--accent-primary)' : 'transparent', zIndex: 100 }}
            onMouseDown={startResizing}
          />
        )}
        <div className="sidebar-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1rem' }}>
          <h2 
            style={{ fontSize: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem', margin: 0, color: 'var(--accent-primary)', cursor: 'pointer', opacity: (!isOpen && !isMobileOpen) ? 0 : 1, transition: 'opacity 0.2s', width: (!isOpen && !isMobileOpen) ? 0 : 'auto', whiteSpace: 'nowrap', overflow: 'hidden' }}
            onClick={() => { onGoHome(); onCloseMobile(); }}
          >
            <div style={{ width: '24px', height: '24px', backgroundColor: 'var(--accent-primary)', borderRadius: '4px', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
              <span style={{ color: 'white', fontSize: '14px', fontWeight: 'bold' }}>E</span>
            </div>
            <span>EduCreate AI</span>
          </h2>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
            {!isMobileOpen && (
              <button 
                className="btn-icon" 
                onClick={onToggleSidebar} 
                style={{ padding: '0.25rem', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                title={isOpen ? "Collapse sidebar" : "Expand sidebar"}
              >
                {isOpen ? <PanelLeftClose size={20} /> : <PanelLeftOpen size={20} />}
              </button>
            )}
            
            {isMobileOpen && (
              <button className="btn-icon" onClick={onCloseMobile} style={{ padding: '0.25rem' }}>
                <X size={20} />
              </button>
            )}
          </div>
        </div>

        <div className="sidebar-content" style={{ display: 'flex', flexDirection: 'column', padding: '0 1rem', flex: 1, minHeight: 0 }}>
          {isOpen || isMobileOpen ? (
            <button 
              className="btn btn-primary" 
              style={{ width: '100%', marginBottom: '1.5rem', justifyContent: 'flex-start' }}
              onClick={() => {
                onNewCreation();
                onCloseMobile();
              }}
            >
              <Sparkles size={18} style={{ color: '#E2E8F0' }} />
              New Creation
            </button>
          ) : (
            <button 
              className="btn btn-primary" 
              style={{ width: '100%', marginBottom: '1.5rem', justifyContent: 'center', padding: '0.5rem' }}
              onClick={onNewCreation}
              title="New Creation"
            >
              <Sparkles size={18} style={{ color: '#E2E8F0' }} />
            </button>
          )}

          <div style={{ marginBottom: '2rem' }}>
            {isOpen || isMobileOpen ? (
              <p style={{ fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>
                Main Menu
              </p>
            ) : null}
            <button 
              className={`nav-item ${viewState === 'LIBRARY' ? 'active' : ''}`}
              onClick={() => { onNavigate('LIBRARY'); onCloseMobile(); }}
              style={{ width: '100%', background: viewState === 'LIBRARY' ? 'var(--selected-bg)' : 'transparent', border: 'none', textAlign: (isOpen || isMobileOpen) ? 'left' : 'center', justifyContent: (isOpen || isMobileOpen) ? 'flex-start' : 'center' }}
              title="Saved Images"
            >
              <Folder size={18} style={{ color: '#0D9488' }} />
              {(isOpen || isMobileOpen) && "Saved Images"}
            </button>
            <button 
              className={`nav-item ${viewState === 'USAGE' ? 'active' : ''}`}
              onClick={() => { onNavigate('USAGE'); onCloseMobile(); }}
              style={{ width: '100%', background: viewState === 'USAGE' ? 'var(--selected-bg)' : 'transparent', border: 'none', textAlign: (isOpen || isMobileOpen) ? 'left' : 'center', justifyContent: (isOpen || isMobileOpen) ? 'flex-start' : 'center' }}
              title="Usage & Savings"
            >
              <Activity size={18} style={{ color: '#059669' }} />
              {(isOpen || isMobileOpen) && "Usage & Savings"}
            </button>
          </div>

          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
            {isOpen || isMobileOpen ? (
              <>
                <p style={{ fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', marginBottom: '0.5rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <History size={14} style={{ color: '#3B82F6' }} /> Recent Conversations
                </p>
                <div style={{ position: 'relative', marginBottom: '0.75rem' }}>
                  <Search size={14} style={{ position: 'absolute', left: '0.5rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-secondary)' }} />
                  <input 
                    type="text" 
                    placeholder="Search history..." 
                    className="input" 
                    style={{ paddingLeft: '2rem', paddingRight: '0.5rem', paddingTop: '0.375rem', paddingBottom: '0.375rem', fontSize: '0.875rem' }}
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                  />
                </div>
                
                <select 
                  className="select-input" 
                  style={{ padding: '0.375rem 0.5rem', fontSize: '0.875rem', marginBottom: '1rem' }}
                  value={filterCategory}
                  onChange={e => setFilterCategory(e.target.value)}
                >
                  <option value="All">All Categories</option>
                  <option value="Posters">Posters</option>
                  <option value="Flashcards">Flashcards</option>
                  <option value="Worksheets">Worksheets</option>
                  <option value="Images">Images</option>
                </select>
              </>
            ) : null}
            
            <div style={{ flex: 1, overflowY: 'auto' }}>
              {filteredSessions.length === 0 ? (
                <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', padding: '0.5rem' }}>No sessions found.</p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  {filteredSessions.map(session => (
                    <div key={session.id} style={{ position: 'relative', display: 'flex', alignItems: 'center' }} onMouseLeave={() => setContextMenuId(null)}>
                      <button
                        className="nav-item"
                        style={{ flex: 1, border: 'none', background: 'transparent', textAlign: 'left', overflow: 'hidden', paddingRight: (isOpen || isMobileOpen) ? '2rem' : '0', justifyContent: (isOpen || isMobileOpen) ? 'flex-start' : 'center' }}
                        onClick={() => { onLoadSession(session); onCloseMobile(); }}
                        title={session.title}
                      >
                        <div style={{ flexShrink: 0, width: '20px', height: '20px', display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: '4px', overflow: 'hidden', backgroundColor: 'var(--bg-color)', border: '1px solid var(--border-color)' }}>
                          {session.images && session.images.filter(i => i.status === 'Completed' && i.url).length > 0 ? (
                            <img 
                              src={session.images.filter(i => i.status === 'Completed' && i.url).pop()!.url} 
                              alt="" 
                              style={{ width: '100%', height: '100%', objectFit: 'cover' }} 
                            />
                          ) : (
                            <MessageSquare size={14} style={{ color: 'var(--text-secondary)' }} />
                          )}
                        </div>
                        {(isOpen || isMobileOpen) && (
                          <div style={{ overflow: 'hidden', display: 'flex', flexDirection: 'column', paddingLeft: '0.5rem' }}>
                            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                              {session.title || 'Untitled'}
                            </span>
                            <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>
                              {new Date(session.timestamp).toLocaleDateString()} &middot; {session.category || 'Draft'}
                            </span>
                          </div>
                        )}
                      </button>
                      
                      {(isOpen || isMobileOpen) && (
                        <>
                          <button 
                            className="btn-icon" 
                            style={{ position: 'absolute', right: '0.25rem', padding: '0.25rem' }}
                            onClick={(e) => {
                              e.stopPropagation();
                              setContextMenuId(contextMenuId === session.id ? null : session.id);
                            }}
                          >
                            <MoreVertical size={14} />
                          </button>
                          
                          {contextMenuId === session.id && (
                            <div style={{ position: 'absolute', right: '1rem', top: '2rem', background: 'var(--surface-color)', border: '1px solid var(--border-color)', borderRadius: '6px', boxShadow: '0 4px 12px rgba(0,0,0,0.1)', zIndex: 10, display: 'flex', flexDirection: 'column', padding: '0.25rem' }}>
                              <button 
                                style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem 1rem', background: 'transparent', border: 'none', textAlign: 'left', cursor: 'pointer', fontSize: '0.875rem', borderRadius: '4px' }}
                                onClick={() => handleRename(session.id, session.title)}
                              >
                                <Edit2 size={14} /> Rename
                              </button>
                              <button 
                                style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem 1rem', background: 'transparent', border: 'none', textAlign: 'left', cursor: 'pointer', fontSize: '0.875rem', color: 'var(--warning-color)', borderRadius: '4px' }}
                                onClick={() => handleDelete(session.id)}
                              >
                                <Trash2 size={14} /> Delete
                              </button>
                            </div>
                          )}
                        </>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="sidebar-footer" style={{ padding: '1rem' }}>
          <button 
            className={`nav-item ${viewState === 'SETTINGS' ? 'active' : ''}`}
            onClick={() => { onNavigate('SETTINGS'); onCloseMobile(); }}
            style={{ width: '100%', background: viewState === 'SETTINGS' ? 'var(--selected-bg)' : 'transparent', border: 'none', textAlign: (isOpen || isMobileOpen) ? 'left' : 'center', justifyContent: (isOpen || isMobileOpen) ? 'flex-start' : 'center' }}
            title="Settings"
          >
            <Settings size={18} style={{ color: '#475569' }} />
            {(isOpen || isMobileOpen) && "Settings"}
          </button>
        </div>
      </aside>
    </>
  );
}
