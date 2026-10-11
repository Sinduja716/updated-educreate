import React, { useState } from 'react';
import { ArrowRight } from 'lucide-react';

interface PromptEntryProps {
  initialPrompt: string;
  onSubmit: (prompt: string) => void;
}

export function PromptEntry({ initialPrompt, onSubmit }: PromptEntryProps) {
  const [prompt, setPrompt] = useState(initialPrompt);

  const handleSubmit = () => {
    if (prompt.trim()) {
      onSubmit(prompt);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && e.ctrlKey) {
      handleSubmit();
    }
  };

  return (
    <div className="workspace animate-fade-in">
      <div className="container" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', height: '100%', paddingBottom: '10vh' }}>
        <div style={{ textAlign: 'center', marginBottom: '3rem' }}>
          <h1 style={{ fontSize: '2.5rem', marginBottom: '1rem', color: 'var(--accent-primary)' }}>What would you like to create?</h1>
          <p style={{ fontSize: '1.125rem', maxWidth: '600px', margin: '0 auto' }}>
            Describe the educational image or learning material you need. EduCreate AI will help you generate or find the perfect visual.
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
            title="Next (Ctrl + Enter)"
          >
            <ArrowRight size={20} />
          </button>
        </div>

      </div>
    </div>
  );
}
