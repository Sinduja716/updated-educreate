import React, { useState } from 'react';
import { ArrowRight } from 'lucide-react';

interface PromptEntryProps {
  initialPrompt: string;
  onSubmit: (prompt: string) => void;          // generate right away, everything automatic
  onChooseOptions: (prompt: string) => void;   // optional: pick category, age, count, quality first
}

export function PromptEntry({ initialPrompt, onSubmit, onChooseOptions }: PromptEntryProps) {
  const [prompt, setPrompt] = useState(initialPrompt);

  const handleSubmit = () => {
    if (prompt.trim()) {
      onSubmit(prompt);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="workspace animate-fade-in">
      <div className="container" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', height: '100%', paddingBottom: '10vh' }}>
        <div style={{ textAlign: 'center', marginBottom: '3rem' }}>
          <h1 style={{ fontSize: '2.5rem', marginBottom: '1rem', color: 'var(--accent-primary)' }}>What would you like to create?</h1>
          <p style={{ fontSize: '1.125rem', maxWidth: '600px', margin: '0 auto' }}>
            Describe the educational image or learning material you need. Press Enter and it starts right away: the material, age group, count and quality are worked out from your words, and a quick low-cost draft is made first. You can upgrade it later.
          </p>
        </div>

        <div className="prompt-composer">
          <textarea
            className="prompt-textarea"
            placeholder="Describe the educational image or learning material you want to create... (e.g. A detailed diagram of the water cycle)"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={handleKeyDown}
            autoFocus
          />
          <button 
            className="composer-btn"
            onClick={handleSubmit}
            disabled={!prompt.trim()}
            title="Generate (Enter)"
          >
            <ArrowRight size={20} />
          </button>
        </div>

        <div style={{ textAlign: 'center', marginTop: '1rem' }}>
          <button
            className="btn btn-secondary"
            style={{ padding: '0.375rem 1rem', fontSize: '0.875rem' }}
            disabled={!prompt.trim()}
            onClick={() => prompt.trim() && onChooseOptions(prompt)}
          >
            Choose options first (optional)
          </button>
        </div>

      </div>
    </div>
  );
}
