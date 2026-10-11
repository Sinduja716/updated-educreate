import React, { useState, useEffect } from 'react';
import type { OutputCategory, AgeGroup, Tier, ColourMode } from '../types';
import { apiService, fmtNeurons, fmtUsd } from '../services/apiService';
import type { PlanView } from '../services/apiService';
import { ArrowLeft, BookOpen, Image as ImageIcon, Layout, Layers } from 'lucide-react';

interface RequiredOptionsProps {
  prompt: string;
  initialCategory?: OutputCategory;
  initialAgeGroup?: AgeGroup;
  initialQuantity: number;
  onBack: () => void;
  onSubmit: (category: OutputCategory, ageGroup: AgeGroup, quantity: number, tier?: Tier, colourMode?: ColourMode) => void;
}

const CATEGORIES: { label: OutputCategory; desc: string; icon: React.ReactNode }[] = [
  { label: 'Posters', desc: 'Educational posters, visual summaries, and classroom displays.', icon: <Layout size={24} /> },
  { label: 'Flashcards', desc: 'Learning and revision cards.', icon: <Layers size={24} /> },
  { label: 'Worksheets', desc: 'Educational exercises and printable learning pages.', icon: <BookOpen size={24} /> },
  { label: 'Images', desc: 'General educational illustrations and learning visuals.', icon: <ImageIcon size={24} /> },
];

const AGE_GROUPS: AgeGroup[] = [
  '3-5',
  '6-8',
  '9-11',
  '12-14',
  '15-18'
];

export function RequiredOptions({
  prompt,
  initialCategory,
  initialAgeGroup,
  initialQuantity,
  onBack,
  onSubmit
}: RequiredOptionsProps) {
  const [category, setCategory] = useState<OutputCategory | undefined>(initialCategory);
  const [ageGroup, setAgeGroup] = useState<AgeGroup | undefined>(initialAgeGroup);
  const [quantity, setQuantity] = useState<number>(initialQuantity);
  const [tierOverride, setTierOverride] = useState<Tier | ''>('');
  const [colourOverride, setColourOverride] = useState<ColourMode | ''>('');
  const [plan, setPlan] = useState<PlanView | null>(null);
  const [planError, setPlanError] = useState('');
  const [planning, setPlanning] = useState(false);
  const [detectedAge, setDetectedAge] = useState<string>('');

  // 1. Read the words once: the planner may recognise the age group.
  useEffect(() => {
    if (initialAgeGroup) return;
    apiService.inferFromPrompt(prompt, initialCategory ?? 'Images').then(p => {
      const src = p.resolved.age_band?.source;
      if (p.ageGroup && src && src !== 'default') {
        setAgeGroup(prev => prev ?? p.ageGroup);
        setDetectedAge(`Detected from your words (${p.ageGroup}). Change it if that is wrong.`);
      }
    }).catch(() => undefined);
  }, [prompt]);

  // 2. Ask the planner for a proposal every time the choices change.
  useEffect(() => {
    if (!category) { setPlan(null); return; }
    let cancelled = false;
    setPlanning(true);
    apiService.plan(prompt, { category, ageGroup, quantity, tier: tierOverride || undefined, colourMode: colourOverride || undefined })
      .then(p => { if (!cancelled) { setPlan(p); setPlanError(''); } })
      .catch(e => { if (!cancelled) { setPlan(null); setPlanError(e.message); } })
      .finally(() => { if (!cancelled) setPlanning(false); });
    return () => { cancelled = true; };
  }, [prompt, category, ageGroup, quantity, tierOverride, colourOverride]);

  useEffect(() => {
    if (category) {
      if (category === 'Flashcards' && quantity === 1 && !initialCategory) {
        setQuantity(6);
      }
    }
  }, [category]);

  const getQuantityLabel = () => {
    switch (category) {
      case 'Posters': return 'Number of posters';
      case 'Flashcards': return 'Number of flashcards';
      case 'Worksheets': return 'Number of worksheet pages';
      case 'Images': return 'Number of images';
      default: return 'Quantity';
    }
  };

  const handleDecrease = () => setQuantity(q => Math.max(1, q - 1));
  const handleIncrease = () => setQuantity(q => Math.min(20, q + 1));

  const isValid = category && ageGroup && quantity > 0;

  return (
    <div className="workspace animate-fade-in">
      <div className="container">
        
        <div className="compact-summary">
          <div>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Your Request</span>
            <p>"{prompt}"</p>
          </div>
          <button className="btn btn-secondary" style={{ padding: '0.25rem 0.75rem', fontSize: '0.875rem' }} onClick={onBack}>
            Edit
          </button>
        </div>

        <h2 style={{ marginBottom: '1.5rem', color: 'var(--accent-primary)' }}>Configure Details</h2>

        <div className="form-group">
          <label className="form-label">1. Output Category *</label>
          <div className="category-grid">
            {CATEGORIES.map(cat => (
              <div 
                key={cat.label} 
                className={`category-card ${category === cat.label ? 'selected' : ''}`}
                onClick={() => setCategory(cat.label)}
              >
                <div className="category-icon">{cat.icon}</div>
                <div className="category-title">{cat.label}</div>
                <p className="category-desc">{cat.desc}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="form-group">
          <label className="form-label">2. Target Age Group *</label>
          <select 
            className="select-input" 
            value={ageGroup || ''} 
            onChange={e => { setAgeGroup(e.target.value as AgeGroup); setDetectedAge(''); }}
            required
          >
            <option value="" disabled>Select an age group...</option>
            {AGE_GROUPS.map(age => (
              <option key={age} value={age}>{age}</option>
            ))}
          </select>
          {detectedAge && <p style={{ marginTop: '0.5rem', fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>{detectedAge}</p>}
        </div>

        <div className="form-group">
          <label className="form-label">3. {getQuantityLabel()} *</label>
          <div className="stepper">
            <button className="stepper-btn" onClick={handleDecrease} disabled={quantity <= 1}>-</button>
            <div className="stepper-value">{quantity}</div>
            <button className="stepper-btn" onClick={handleIncrease} disabled={quantity >= 20}>+</button>
          </div>
          <p style={{ marginTop: '0.5rem', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
            Set the required {getQuantityLabel().toLowerCase()}.
          </p>
        </div>


        {category && (
          <div className="card" style={{ marginTop: '2rem' }}>
            <h3 style={{ fontSize: '1rem', marginBottom: '0.75rem' }}>4. Proposed quality and estimated cost</h3>
            {planning && !plan && <p style={{ margin: 0 }}>Working out a proposal...</p>}
            {planError && <p style={{ margin: 0, color: 'var(--warning-color)' }}>Could not reach the planner: {planError}</p>}
            {plan && (
              <>
                <p style={{ margin: '0 0 0.75rem 0' }}>
                  <strong>{plan.tier}</strong> quality ({plan.steps} steps){tierOverride ? ' - chosen by you' : ' - proposed'}: {plan.tierReason}
                </p>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '1rem', fontSize: '0.875rem' }}>
                  <div><span style={{ color: 'var(--text-secondary)' }}>Compute</span><strong style={{ display: 'block' }}>{fmtNeurons(plan.totalNeurons)}</strong></div>
                  <div><span style={{ color: 'var(--text-secondary)' }}>Estimated cost</span><strong style={{ display: 'block' }}>{fmtUsd(plan.totalCostUsd)}</strong></div>
                  <div><span style={{ color: 'var(--text-secondary)' }}>Time per image</span><strong style={{ display: 'block' }}>{plan.estimate.seconds != null ? `${plan.estimate.seconds} s` : '-'}</strong></div>
                  <div><span style={{ color: 'var(--text-secondary)' }}>Maximum quality would use</span><strong style={{ display: 'block' }}>{fmtNeurons(plan.maxTotalNeurons)}</strong></div>
                  <div><span style={{ color: 'var(--text-secondary)' }}>Saving</span><strong style={{ display: 'block', color: 'var(--success-color)' }}>{plan.estimate.savingPercent != null ? `${plan.estimate.savingPercent}%` : '-'}</strong></div>
                </div>
                <p style={{ margin: '0.75rem 0 0 0', fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
                  Estimate only. Pictures already in the library are reused and cost 0 neurons.{plan.estimate.placeholder ? ' Time numbers are placeholders until measured.' : ''} {plan.estimate.notes.join(' ')}
                </p>
                {plan.warnings.map(w => <p key={w} style={{ margin: '0.5rem 0 0 0', fontSize: '0.8125rem', color: 'var(--warning-color)' }}>{w}</p>)}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginTop: '1rem' }}>
                  <div>
                    <label className="form-label" style={{ fontSize: '0.875rem' }}>Quality (override)</label>
                    <select className="select-input" value={tierOverride} onChange={e => setTierOverride(e.target.value as Tier | '')}>
                      <option value="">Use the proposal</option>
                      <option value="draft">Draft (2 steps, fastest)</option>
                      <option value="standard">Standard (4 steps)</option>
                      <option value="high">High (8 steps, maximum)</option>
                    </select>
                  </div>
                  {category !== 'Worksheets' && (
                    <div>
                      <label className="form-label" style={{ fontSize: '0.875rem' }}>Colour (override) - now: {plan.colourMode === 'outline' ? 'black & white outline' : 'colour'}</label>
                      <select className="select-input" value={colourOverride} onChange={e => setColourOverride(e.target.value as ColourMode | '')}>
                        <option value="">Use the proposal</option>
                        <option value="colour">Colour</option>
                        <option value="outline">Black and white outline</option>
                      </select>
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        )}

        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '3rem', paddingTop: '1.5rem', borderTop: '1px solid var(--border-color)' }}>
          <button className="btn btn-secondary" onClick={onBack}>
            <ArrowLeft size={18} />
            Back
          </button>
          <button 
            className="btn btn-primary" 
            disabled={!isValid || !plan}
            onClick={() => {
              if (category && ageGroup) {
                onSubmit(category, ageGroup, quantity, tierOverride || undefined, colourOverride || undefined);
              }
            }}
          >
            Generate
          </button>
        </div>
      </div>
    </div>
  );
}
