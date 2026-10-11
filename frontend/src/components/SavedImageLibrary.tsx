import { useEffect, useState } from 'react';
import type { CreationSession } from '../types';
import { apiService } from '../services/apiService';
import { Download, Image as ImageIcon } from 'lucide-react';

interface SavedImage {
  id: string;
  url: string;
  title: string;
  category: string;
  date: string;
}

interface SavedImageLibraryProps {
  onSessionClick: (session: CreationSession) => void;
  onNewCreation: () => void;
}

export function SavedImageLibrary({ onNewCreation }: SavedImageLibraryProps) {
  const [images, setImages] = useState<SavedImage[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      const data = await apiService.getSavedImages();
      setImages(data);
      setLoading(false);
    }
    load();
  }, []);

  const handleDownload = (url: string, id: string) => {
    const a = document.createElement('a');
    a.href = url;
    a.download = `educreate-lib-${id}.png`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  if (loading) {
    return <div className="workspace"><div className="container" style={{ textAlign: 'center', marginTop: '4rem' }}>Loading library...</div></div>;
  }

  return (
    <div className="workspace animate-fade-in">
      <div className="full-container">
        <h1 style={{ color: 'var(--accent-primary)', marginBottom: '2rem' }}>Saved Images</h1>

        {images.length === 0 ? (
          <div className="card" style={{ textAlign: 'center', padding: '4rem 2rem' }}>
            <div style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>
              <ImageIcon size={48} style={{ margin: '0 auto', display: 'block', opacity: 0.5 }} />
            </div>
            <h3 style={{ marginBottom: '0.5rem' }}>Your library is empty</h3>
            <p style={{ margin: 0, maxWidth: '400px', marginInline: 'auto' }}>
              Images you generate or retrieve will automatically be saved here for future reference.
            </p>
            <div style={{ marginTop: '1.5rem', display: 'flex', justifyContent: 'center' }}>
              <button className="btn btn-primary" onClick={onNewCreation}>
                Create your first image
              </button>
            </div>
          </div>
        ) : (
          <div className="image-grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))' }}>
            {images.map(img => (
              <div key={img.id} className="image-card">
                <img src={img.url} alt={img.title} className="image-preview" style={{ height: '150px' }} />
                <div className="image-details" style={{ padding: '0.75rem' }}>
                  <p style={{ margin: '0 0 0.5rem 0', fontSize: '0.875rem', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={img.title}>
                    {img.title || 'Untitled'}
                  </p>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                    <span className="badge" style={{ backgroundColor: 'var(--bg-color)', fontSize: '0.7rem' }}>{img.category}</span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                      {new Date(img.date).toLocaleDateString()}
                    </span>
                  </div>
                  <button 
                    className="btn btn-secondary" 
                    style={{ width: '100%', padding: '0.375rem', fontSize: '0.875rem' }}
                    onClick={() => handleDownload(img.url, img.id)}
                  >
                    <Download size={14} /> Download
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
