import { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { PromptEntry } from './components/PromptEntry';
import { RequiredOptions } from './components/RequiredOptions';
import { CreationWorkspace } from './components/CreationWorkspace';
import { UsageSavingsDashboard } from './components/UsageSavingsDashboard';
import { SavedImageLibrary } from './components/SavedImageLibrary';
import { SettingsPage } from './components/SettingsPage';
import type { WorkflowStage, ViewState, CreationSession, OutputCategory, AgeGroup, UserPreferences, Tier, ColourMode } from './types';
import { apiService } from './services/apiService';
import { Menu } from 'lucide-react';

function App() {
  const [viewState, setViewState] = useState<ViewState>('CREATE');
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  
  // Creation Workflow State
  const [workflowStage, setWorkflowStage] = useState<WorkflowStage>('STAGE_1_PROMPT');
  const [currentSession, setCurrentSession] = useState<CreationSession | null>(null);
  
  const [prompt, setPrompt] = useState('');
  const [category, setCategory] = useState<OutputCategory | undefined>(undefined);
  const [ageGroup, setAgeGroup] = useState<AgeGroup | undefined>(undefined);
  const [quantity, setQuantity] = useState<number>(1);

  // History State
  const [sessions, setSessions] = useState<CreationSession[]>([]);
  const [prefs, setPrefs] = useState<UserPreferences | null>(null);
  const [libraryQuery, setLibraryQuery] = useState('');

  useEffect(() => {
    loadSessions();
    apiService.getPreferences().then(setPrefs);
  }, []);

  const loadSessions = async () => {
    const data = await apiService.getSessions();
    setSessions(data);
  };

  const handleStartNew = () => {
    setPrompt('');
    setCategory(prefs?.defaultCategory || undefined);
    setAgeGroup(undefined);
    setQuantity(prefs?.defaultQuantity || 1);
    setCurrentSession(null);
    setWorkflowStage('STAGE_1_PROMPT');
    setViewState('CREATE');
  };

  const handleReuse = (p: string, cat: OutputCategory) => {
    setPrompt(p);
    setCategory(cat);
    setAgeGroup(undefined);
    setQuantity(prefs?.defaultQuantity || 1);
    setCurrentSession(null);
    setWorkflowStage('STAGE_2_OPTIONS');
    setViewState('CREATE');
  };

  const handleGoHome = () => {
    setWorkflowStage('STAGE_1_PROMPT');
    setViewState('CREATE');
  };

  const handleRenameSession = async (id: string, newTitle: string) => {
    await apiService.renameSession(id, newTitle);
    loadSessions();
  };

  const handleDeleteSession = async (id: string) => {
    await apiService.deleteSession(id);
    if (currentSession?.id === id) {
      handleStartNew();
    }
    loadSessions();
  };

  // Enter on the prompt screen: start at once. Nothing is asked; the planner works everything out from the words.
  const handlePromptSubmit = (p: string) => {
    setPrompt(p);
    const session: CreationSession = {
      id: `session-${Date.now()}`,
      title: p,
      timestamp: new Date().toISOString(),
      prompt: p,
      category: prefs?.defaultCategory || undefined,
      quantity: prefs?.defaultQuantity && prefs.defaultQuantity > 1 ? prefs.defaultQuantity : undefined,
      images: []
    };
    setCurrentSession(session);
    setWorkflowStage('STAGE_3_WORKSPACE');
  };

  const handleChooseOptions = (p: string) => {
    setPrompt(p);
    setWorkflowStage('STAGE_2_OPTIONS');
  };

  const handleOptionsSubmit = (cat: OutputCategory, age: AgeGroup, qty: number, tier?: Tier, colourMode?: ColourMode, material?: string) => {
    setCategory(cat);
    setAgeGroup(age);
    setQuantity(qty);
    
    // Generate new session ID if it doesn't exist
    const newSession: CreationSession = currentSession || {
      id: `session-${Date.now()}`,
      title: prompt,
      timestamp: new Date().toISOString(),
      prompt,
      category: cat,
      ageGroup: age,
      quantity: qty,
      tier,
      colourMode,
      material,
      images: []
    };
    
    setCurrentSession(newSession);
    setWorkflowStage('STAGE_3_WORKSPACE');
  };

  const handleLoadSession = (session: CreationSession) => {
    setCurrentSession(session);
    setPrompt(session.prompt);
    setCategory(session.category);
    setAgeGroup(session.ageGroup);
    setQuantity(session.quantity || 1);
    setWorkflowStage('STAGE_3_WORKSPACE');
    setViewState('CREATE');
  };

  const renderContent = () => {
    switch (viewState) {
      case 'USAGE':
        return <UsageSavingsDashboard />;
      case 'LIBRARY':
        return <SavedImageLibrary onSessionClick={handleLoadSession} onNewCreation={handleStartNew} onReuse={handleReuse} initialQuery={libraryQuery} />;
      case 'SETTINGS':
        return <SettingsPage onClearSessions={() => { setSessions([]); handleStartNew(); }} />;
      case 'CREATE':
      default:
        if (workflowStage === 'STAGE_1_PROMPT') {
          return <PromptEntry initialPrompt={prompt} onSubmit={handlePromptSubmit} onChooseOptions={handleChooseOptions} />;
        }
        if (workflowStage === 'STAGE_2_OPTIONS') {
          return (
            <RequiredOptions
              prompt={prompt}
              initialCategory={category}
              initialAgeGroup={ageGroup}
              initialQuantity={quantity}
              onBack={() => setWorkflowStage('STAGE_1_PROMPT')}
              onSubmit={handleOptionsSubmit}
            />
          );
        }
        if (workflowStage === 'STAGE_3_WORKSPACE' && currentSession) {
          return (
            <CreationWorkspace
              session={currentSession}
              onUpdateSession={(updated) => {
                setCurrentSession(prev => {
                  if (!prev) return prev;
                  const newSession = typeof updated === 'function' ? updated(prev) : updated;
                  apiService.saveSession(newSession).then(loadSessions);
                  return newSession;
                });
              }}
              onCreateAnother={handleStartNew}
            />
          );
        }
        return null;
    }
  };

  return (
    <div className="app-layout">
      <Sidebar
        isOpen={isSidebarOpen}
        isMobileOpen={isMobileOpen}
        onCloseMobile={() => setIsMobileOpen(false)}
        viewState={viewState}
        sessions={sessions}
        onNavigate={(v) => { if (v === 'LIBRARY') setLibraryQuery(''); setViewState(v); }}
        onOpenLibrary={(q) => { setLibraryQuery(q); setViewState('LIBRARY'); }}
        onNewCreation={handleStartNew}
        onLoadSession={handleLoadSession}
        onRenameSession={handleRenameSession}
        onDeleteSession={handleDeleteSession}
        onGoHome={handleGoHome}
        onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
      />
      
      <main className="main-content" style={{ position: 'relative' }}>
        <button 
          className="btn-icon mobile-menu-btn" 
          style={{ position: 'absolute', top: '1rem', left: '1rem', zIndex: 10 }}
          onClick={() => setIsMobileOpen(true)}
        >
          <Menu size={24} />
        </button>
        
        {renderContent()}
      </main>
    </div>
  );
}

export default App;
