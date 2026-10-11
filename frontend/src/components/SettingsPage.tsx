import { useEffect, useState } from 'react';
import { apiService } from '../services/apiService';
import type { UserPreferences } from '../types';
import { Monitor, Image as ImageIcon, Zap, Download, Shield, Info, Trash2, RotateCcw } from 'lucide-react';

interface SettingsPageProps {
  onClearSessions: () => void;
}

export function SettingsPage({ onClearSessions }: SettingsPageProps) {
  const [prefs, setPrefs] = useState<UserPreferences | null>(null);
  const [loading, setLoading] = useState(true);
  const [saveMessage, setSaveMessage] = useState('');

  useEffect(() => {
    loadPrefs();
  }, []);

  const loadPrefs = async () => {
    const data = await apiService.getPreferences();
    setPrefs(data);
    setLoading(false);
  };

  const handleChange = async (key: keyof UserPreferences, value: any) => {
    if (!prefs) return;
    const updated = { ...prefs, [key]: value };
    setPrefs(updated);
    await apiService.savePreferences({ [key]: value });
    
    setSaveMessage('Preference saved');
    setTimeout(() => setSaveMessage(''), 2000);
  };

  const handleResetDefaults = async () => {
    if (confirm('Are you sure you want to reset all preferences to default?')) {
      const defaults: Partial<UserPreferences> = {
        theme: 'System',
        density: 'Comfortable',
        defaultCategory: undefined,
        defaultOrientation: 'Portrait',
        defaultQuantity: 1,
        showCostEstimates: true,
        defaultDownloadFormat: 'PNG',
        defaultExportSize: 'A4'
      };
      setPrefs(prefs ? { ...prefs, ...defaults } : null);
      await apiService.savePreferences(defaults);
      setSaveMessage('Reset to defaults');
      setTimeout(() => setSaveMessage(''), 2000);
    }
  };

  const handleClearConversations = async () => {
    if (confirm('Are you sure you want to delete all recent conversations? This action cannot be undone.')) {
      await apiService.clearAllSessions();
      onClearSessions();
      alert('All conversations have been cleared.');
    }
  };

  const handleClearSavedImages = async () => {
    if (confirm('Are you sure you want to delete all saved images? This action cannot be undone.')) {
      await apiService.clearSavedImages();
      alert('All saved images have been cleared.');
    }
  };

  if (loading || !prefs) {
    return <div className="workspace"><div className="container" style={{ textAlign: 'center', marginTop: '4rem' }}>Loading settings...</div></div>;
  }

  return (
    <div className="workspace animate-fade-in" style={{ overflowY: 'auto' }}>
      <div className="container" style={{ maxWidth: '800px', paddingBottom: '4rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
          <h1 style={{ color: 'var(--accent-primary)', margin: 0 }}>Settings</h1>
          {saveMessage && (
            <span style={{ fontSize: '0.875rem', color: 'var(--success-color)', backgroundColor: 'rgba(71, 122, 98, 0.1)', padding: '0.25rem 0.75rem', borderRadius: '12px' }}>
              {saveMessage}
            </span>
          )}
        </div>

        {/* A. Appearance */}
        <section style={{ marginBottom: '3rem' }}>
          <h2 style={{ fontSize: '1.125rem', display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem', color: 'var(--text-primary)' }}>
            <Monitor size={18} /> Appearance
          </h2>
          <div style={{ paddingLeft: '1.5rem', borderLeft: '2px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            <div>
              <label className="form-label" style={{ fontSize: '0.875rem' }}>Theme</label>
              <select className="select-input" style={{ maxWidth: '300px' }} value={prefs.theme} onChange={e => handleChange('theme', e.target.value)}>
                <option value="Light">Light</option>
                <option value="Dark">Dark</option>
                <option value="System">System (Default)</option>
              </select>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem', margin: 0 }}>Select your preferred interface theme.</p>
            </div>
            <div>
              <label className="form-label" style={{ fontSize: '0.875rem' }}>Interface Density</label>
              <select className="select-input" style={{ maxWidth: '300px' }} value={prefs.density} onChange={e => handleChange('density', e.target.value)}>
                <option value="Comfortable">Comfortable (Default)</option>
                <option value="Compact">Compact</option>
              </select>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem', margin: 0 }}>Adjust the spacing and size of interface elements.</p>
            </div>
          </div>
        </section>

        {/* B. Image Generation Preferences */}
        <section style={{ marginBottom: '3rem' }}>
          <h2 style={{ fontSize: '1.125rem', display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem', color: 'var(--text-primary)' }}>
            <ImageIcon size={18} /> Image Generation
          </h2>
          <div style={{ paddingLeft: '1.5rem', borderLeft: '2px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            <div>
              <label className="form-label" style={{ fontSize: '0.875rem' }}>Default Output Category</label>
              <select className="select-input" style={{ maxWidth: '300px' }} value={prefs.defaultCategory || ''} onChange={e => handleChange('defaultCategory', e.target.value || undefined)}>
                <option value="">None (Ask every time)</option>
                <option value="Posters">Posters</option>
                <option value="Flashcards">Flashcards</option>
                <option value="Worksheets">Worksheets</option>
                <option value="Images">Images</option>
              </select>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem', margin: 0 }}>Pre-selects this category in the options stage.</p>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.5rem', maxWidth: '600px' }}>
              <div>
                <label className="form-label" style={{ fontSize: '0.875rem' }}>Default Orientation</label>
                <select className="select-input" value={prefs.defaultOrientation} onChange={e => handleChange('defaultOrientation', e.target.value)}>
                  <option value="Portrait">Portrait</option>
                  <option value="Landscape">Landscape</option>
                  <option value="Square">Square</option>
                </select>
              </div>
              <div>
                <label className="form-label" style={{ fontSize: '0.875rem' }}>Default Quantity</label>
                <input type="number" className="input" min="1" max="20" value={prefs.defaultQuantity} onChange={e => handleChange('defaultQuantity', parseInt(e.target.value) || 1)} />
              </div>
            </div>
            <div>
              <button className="btn btn-secondary" style={{ padding: '0.375rem 0.75rem', fontSize: '0.875rem' }} onClick={handleResetDefaults}>
                <RotateCcw size={16} /> Reset defaults
              </button>
            </div>
          </div>
        </section>

        {/* C. Resource and Savings */}
        <section style={{ marginBottom: '3rem' }}>
          <h2 style={{ fontSize: '1.125rem', display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem', color: 'var(--text-primary)' }}>
            <Zap size={18} /> Resource & Savings
          </h2>
          <div style={{ paddingLeft: '1.5rem', borderLeft: '2px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            <div>
              <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', margin: '0 0 1rem 0', maxWidth: '600px', lineHeight: 1.5 }}>
                EduCreate AI optimizes generation by retrieving existing educational visuals from our library when they match your prompt. Our baseline calculations compare this optimized workflow against the cost and energy of unconditionally generating new images at maximum supported quality.
              </p>
              <label className="form-label" style={{ fontSize: '0.875rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <input type="checkbox" checked={prefs.showCostEstimates} onChange={e => handleChange('showCostEstimates', e.target.checked)} />
                Display monetary cost estimates
              </label>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem', margin: 0, paddingLeft: '1.5rem' }}>
                Shows estimated USD cost and savings alongside neuron usage in dashboards.
              </p>
            </div>
          </div>
        </section>

        {/* D. Library and Download */}
        <section style={{ marginBottom: '3rem' }}>
          <h2 style={{ fontSize: '1.125rem', display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem', color: 'var(--text-primary)' }}>
            <Download size={18} /> Library & Download
          </h2>
          <div style={{ paddingLeft: '1.5rem', borderLeft: '2px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.5rem', maxWidth: '600px' }}>
              <div>
                <label className="form-label" style={{ fontSize: '0.875rem' }}>Default Download Format</label>
                <select className="select-input" value={prefs.defaultDownloadFormat} onChange={e => handleChange('defaultDownloadFormat', e.target.value)}>
                  <option value="PNG">PNG (Image)</option>
                  <option value="PDF">PDF (Document)</option>
                </select>
              </div>
              <div>
                <label className="form-label" style={{ fontSize: '0.875rem' }}>Default PDF Export Size</label>
                <select className="select-input" value={prefs.defaultExportSize} onChange={e => handleChange('defaultExportSize', e.target.value)}>
                  <option value="A4">A4</option>
                  <option value="A3">A3</option>
                  <option value="Letter">US Letter</option>
                </select>
              </div>
            </div>
          </div>
        </section>

        {/* E. Data and Privacy */}
        <section style={{ marginBottom: '3rem' }}>
          <h2 style={{ fontSize: '1.125rem', display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem', color: 'var(--text-primary)' }}>
            <Shield size={18} /> Data & Privacy
          </h2>
          <div style={{ paddingLeft: '1.5rem', borderLeft: '2px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            <div>
              <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', margin: '0 0 1rem 0', maxWidth: '600px', lineHeight: 1.5 }}>
                Your creation sessions, preferences, and saved images are stored locally in your browser to respect your privacy and provide immediate access. Clearing this data removes it permanently from this device.
              </p>
              <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                <button className="btn btn-secondary" style={{ padding: '0.5rem 1rem', color: 'var(--warning-color)', borderColor: 'var(--warning-color)' }} onClick={handleClearConversations}>
                  <Trash2 size={16} /> Clear recent conversations
                </button>
                <button className="btn btn-secondary" style={{ padding: '0.5rem 1rem', color: 'var(--warning-color)', borderColor: 'var(--warning-color)' }} onClick={handleClearSavedImages}>
                  <Trash2 size={16} /> Clear saved images
                </button>
              </div>
            </div>
          </div>
        </section>

        {/* F. About */}
        <section>
          <h2 style={{ fontSize: '1.125rem', display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem', color: 'var(--text-primary)' }}>
            <Info size={18} /> About EduCreate AI
          </h2>
          <div style={{ paddingLeft: '1.5rem', borderLeft: '2px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <h3 style={{ margin: 0, fontSize: '1rem' }}>EduCreate AI</h3>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', backgroundColor: 'var(--selected-bg)', padding: '0.125rem 0.5rem', borderRadius: '12px', alignSelf: 'flex-start' }}>Version 1.0.0</span>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', margin: '0.5rem 0 0 0', maxWidth: '600px', lineHeight: 1.5 }}>
              An educational image creation platform that helps teachers create posters, flashcards, and learning visuals. EduCreate AI dynamically adapts computational effort by seamlessly reusing existing high-quality library images when appropriate, saving energy and providing transparent resource metrics.
            </p>
          </div>
        </section>

      </div>
    </div>
  );
}
