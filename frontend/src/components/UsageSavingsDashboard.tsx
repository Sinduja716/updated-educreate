import { useEffect, useState } from 'react';
import type { GlobalMetrics, CreationSession, UserPreferences } from '../types';
import { apiService } from '../services/apiService';
import { DollarSign, Image as ImageIcon, CheckCircle, Layers, Activity } from 'lucide-react';

export function UsageSavingsDashboard() {
  const [metrics, setMetrics] = useState<GlobalMetrics | null>(null);
  const [history, setHistory] = useState<CreationSession[]>([]);
  const [timeFilter, setTimeFilter] = useState('all-time');
  const [prefs, setPrefs] = useState<UserPreferences | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    async function load() {
      try {
        const [m, h, p] = await Promise.all([apiService.getGlobalMetrics(), apiService.getSessions(), apiService.getPreferences()]);
        setMetrics(m);
        setHistory(h.filter(s => s.metrics));
        setPrefs(p);
      } catch (e: any) {
        setError(e?.message || 'Could not load usage numbers.');
      }
      setLoading(false);
    }
    load();
  }, []);

  if (loading) {
    return <div className="workspace"><div className="container" style={{ textAlign: 'center', marginTop: '4rem' }}>Loading metrics...</div></div>;
  }

  if (!metrics) {
    return <div className="workspace"><div className="container"><h3>Usage numbers are not available</h3><p>{error || 'No data.'}</p><p>Check that the backend is running on port 8000 and was restarted after the update (it must have the /api/v1/metrics/global route).</p></div></div>;
  }

  return (
    <div className="workspace animate-fade-in">
      <div className="full-container">
        <h1 style={{ color: 'var(--accent-primary)', marginBottom: '2rem' }}>Usage & Savings</h1>
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem', marginBottom: '3rem' }}>
          
          {/* Total Creations */}
          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', height: '100%', padding: '1.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <div style={{ padding: '0.5rem', backgroundColor: '#F1F5F9', borderRadius: '6px', color: '#475569', display: 'flex' }}>
                <Layers size={18} />
              </div>
              <span style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-primary)' }}>Total Creations</span>
            </div>
            <h2 style={{ margin: '0.25rem 0', fontSize: '2rem', fontWeight: 700, color: 'var(--text-primary)' }}>{metrics.totalRequested}</h2>
            <p style={{ margin: 0, fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Total images requested across all educational materials.</p>
          </div>
          
          {/* Images Generated */}
          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', height: '100%', padding: '1.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <div style={{ padding: '0.5rem', backgroundColor: '#EDE9FE', borderRadius: '6px', color: '#8B5CF6', display: 'flex' }}>
                <ImageIcon size={18} />
              </div>
              <span style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-primary)' }}>Images Generated</span>
            </div>
            <h2 style={{ margin: '0.25rem 0', fontSize: '2rem', fontWeight: 700, color: 'var(--text-primary)' }}>{metrics.totalGenerated}</h2>
            <p style={{ margin: 0, fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Newly created visual assets that were not in the library.</p>
          </div>
          
          {/* Images Reused */}
          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', height: '100%', padding: '1.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <div style={{ padding: '0.5rem', backgroundColor: '#D1FAE5', borderRadius: '6px', color: '#059669', display: 'flex' }}>
                <CheckCircle size={18} />
              </div>
              <span style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-primary)' }}>Images Reused</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.75rem', margin: '0.25rem 0' }}>
              <h2 style={{ margin: 0, fontSize: '2rem', fontWeight: 700, color: 'var(--text-primary)' }}>{metrics.totalReused}</h2>
              {metrics.totalRequested > 0 && (
                <span style={{ fontSize: '0.875rem', fontWeight: 500, color: 'var(--success-color)', backgroundColor: 'rgba(71, 122, 98, 0.1)', padding: '0.125rem 0.5rem', borderRadius: '12px' }}>
                  {((metrics.totalReused / metrics.totalRequested) * 100).toFixed(0)}%
                </span>
              )}
            </div>
            <p style={{ margin: 0, fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Existing images retrieved from the library to save resources.</p>
          </div>
          
          {/* Estimated Savings */}
          {prefs?.showCostEstimates && (
            <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', height: '100%', padding: '1.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <div style={{ padding: '0.5rem', backgroundColor: '#FEF3C7', borderRadius: '6px', color: '#D97706', display: 'flex' }}>
                  <DollarSign size={18} />
                </div>
                <span style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-primary)' }}>Estimated Savings</span>
              </div>
              <h2 style={{ margin: '0.25rem 0', fontSize: '2rem', fontWeight: 700, color: 'var(--text-primary)' }}>{metrics.totalCostSaved}</h2>
              <p style={{ margin: 0, fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Estimated monetary cost saved against the baseline.</p>
            </div>
          )}
          
          {/* Resource Efficiency */}
          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', height: '100%', padding: '1.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <div style={{ padding: '0.5rem', backgroundColor: '#CCFBF1', borderRadius: '6px', color: '#0D9488', display: 'flex' }}>
                <Activity size={18} />
              </div>
              <span style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-primary)' }}>Resource Efficiency</span>
            </div>
            <h2 style={{ margin: '0.25rem 0', fontSize: '2rem', fontWeight: 700, color: 'var(--text-primary)' }}>{metrics.totalResourceSaved}</h2>
            <p style={{ margin: 0, fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Estimated compute (Cloudflare neurons) saved against making every picture at maximum quality.</p>
          </div>
          
        </div>

        <h3 style={{ marginBottom: '1.5rem' }}>Estimated Savings Overview</h3>
        
        {metrics.totalRequested > 0 ? (
          <div style={{ marginBottom: '3rem', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            
            {/* Prominent Savings Summary */}
            <div className="card" style={{ backgroundColor: 'var(--bg-color)', border: '1px solid var(--border-color)', padding: '1.5rem' }}>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '2rem', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ flex: '1 1 min-content' }}>
                  <h4 style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '1rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Total Savings</h4>
                  <div style={{ display: 'flex', gap: '3rem', flexWrap: 'wrap' }}>
                    {prefs?.showCostEstimates && (
                      <div>
                        <span style={{ display: 'block', fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Estimated Amount</span>
                        <strong style={{ fontSize: '1.75rem', color: 'var(--success-color)' }}>{metrics.totalCostSaved}</strong>
                      </div>
                    )}
                    <div>
                      <span style={{ display: 'block', fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Percentage Saved</span>
                      <strong style={{ fontSize: '1.75rem', color: 'var(--success-color)' }}>{metrics.savingsPercentage}</strong>
                    </div>
                  </div>
                </div>
                
                <div style={{ flex: '1 1 min-content', minWidth: '250px', paddingLeft: '2rem', borderLeft: '1px solid var(--border-color)' }}>
                  <h4 style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '1rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Image Reuse</h4>
                  {(() => {
                     const reused = metrics.totalReused;
                     const generated = metrics.totalGenerated;
                     const total = reused + generated;
                     const pctReused = total > 0 ? (reused / total) * 100 : 0;
                     return (
                       <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                         <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.5rem' }}>
                           <strong style={{ fontSize: '1.75rem', color: 'var(--text-primary)' }}>{reused}</strong>
                           <span style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>reused images</span>
                         </div>
                         <div style={{ display: 'flex', width: '100%', height: '8px', borderRadius: '4px', overflow: 'hidden', backgroundColor: 'var(--border-color)' }}>
                            <div style={{ width: `${pctReused}%`, backgroundColor: 'var(--success-color)' }} title={`Reused: ${reused}`}></div>
                            <div style={{ width: `${100 - pctReused}%`, backgroundColor: 'var(--accent-primary)' }} title={`Generated: ${generated}`}></div>
                         </div>
                         <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem' }}>
                           <span style={{ color: 'var(--success-color)', fontWeight: 500 }}>Reused ({pctReused.toFixed(0)}%)</span>
                           <span style={{ color: 'var(--accent-primary)', fontWeight: 500 }}>Generated ({(100 - pctReused).toFixed(0)}%)</span>
                         </div>
                       </div>
                     );
                  })()}
                </div>
              </div>
            </div>

            {/* Horizontal Bar Charts */}
            <div className="card" style={{ padding: '2rem' }}>
              <div style={{ display: 'grid', gridTemplateColumns: prefs?.showCostEstimates ? '1fr 1fr' : '1fr', gap: '4rem' }}>
                {prefs?.showCostEstimates && (
                  <div>
                    <h4 style={{ fontSize: '1rem', color: 'var(--text-primary)', marginBottom: '1.5rem', fontWeight: 600 }}>Estimated Cost Comparison</h4>
                    
                    {(() => {
                      const actualCost = parseFloat(metrics.totalCost.replace(/[^0-9.]/g, '')) || 0;
                      const savedCost = parseFloat(metrics.totalCostSaved.replace(/[^0-9.]/g, '')) || 0;
                      const baselineCost = actualCost + savedCost;
                      const actualPct = baselineCost > 0 ? (actualCost / baselineCost) * 100 : 0;
                      
                      return (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                          <div style={{ position: 'relative' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', fontSize: '0.875rem' }}>
                              <span style={{ color: 'var(--text-secondary)' }}>Maximum-quality baseline</span>
                              <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>${baselineCost.toFixed(4)}</span>
                            </div>
                            <div style={{ width: '100%', height: '24px', backgroundColor: 'var(--bg-color)', borderRadius: '4px' }} title="Baseline Cost (No reuse)">
                              <div style={{ width: '100%', height: '100%', backgroundColor: '#94A3B8', borderRadius: '4px' }}></div>
                            </div>
                          </div>
                          
                          <div style={{ position: 'relative' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', fontSize: '0.875rem' }}>
                              <span style={{ color: 'var(--text-secondary)' }}>Optimized workflow</span>
                              <span style={{ fontWeight: 600, color: 'var(--success-color)' }}>${actualCost.toFixed(4)}</span>
                            </div>
                            <div style={{ width: '100%', height: '24px', backgroundColor: 'var(--bg-color)', borderRadius: '4px' }} title="Actual Cost (With reuse)">
                              <div style={{ width: `${actualPct}%`, height: '100%', backgroundColor: 'var(--success-color)', borderRadius: '4px', minWidth: '4px' }}></div>
                            </div>
                          </div>
                        </div>
                      );
                    })()}
                  </div>
                )}
                
                <div>
                  <h4 style={{ fontSize: '1rem', color: 'var(--text-primary)', marginBottom: '1.5rem', fontWeight: 600 }}>Resource Usage Comparison</h4>
                  
                  {(() => {
                    const actualRes = parseFloat(metrics.totalResourceUsage.replace(/[^0-9.]/g, '')) || 0;
                    const savedRes = parseFloat(metrics.totalResourceSaved.replace(/[^0-9.]/g, '')) || 0;
                    const baselineRes = actualRes + savedRes;
                    const actualPct = baselineRes > 0 ? (actualRes / baselineRes) * 100 : 0;
                    
                    return (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                        <div style={{ position: 'relative' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', fontSize: '0.875rem' }}>
                            <span style={{ color: 'var(--text-secondary)' }}>Maximum-quality baseline</span>
                            <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{baselineRes.toFixed(1)} neurons</span>
                          </div>
                          <div style={{ width: '100%', height: '24px', backgroundColor: 'var(--bg-color)', borderRadius: '4px' }} title="Baseline Resource Usage">
                            <div style={{ width: '100%', height: '100%', backgroundColor: '#94A3B8', borderRadius: '4px' }}></div>
                          </div>
                        </div>
                        
                        <div style={{ position: 'relative' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', fontSize: '0.875rem' }}>
                            <span style={{ color: 'var(--text-secondary)' }}>Optimized workflow</span>
                            <span style={{ fontWeight: 600, color: '#0D9488' }}>{actualRes.toFixed(1)} neurons</span>
                          </div>
                          <div style={{ width: '100%', height: '24px', backgroundColor: 'var(--bg-color)', borderRadius: '4px' }} title="Actual Resource Usage">
                            <div style={{ width: `${actualPct}%`, height: '100%', backgroundColor: '#0D9488', borderRadius: '4px', minWidth: '4px' }}></div>
                          </div>
                        </div>
                      </div>
                    );
                  })()}
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="card" style={{ textAlign: 'center', padding: '3rem 1rem', marginBottom: '3rem' }}>
            <p style={{ margin: 0, color: 'var(--text-secondary)' }}>No usage data available to generate charts.</p>
          </div>
        )}

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
          <h3 style={{ margin: 0 }}>Usage Over Time</h3>
          <select 
            className="select-input" 
            style={{ padding: '0.25rem 0.5rem', fontSize: '0.875rem', width: 'auto' }}
            value={timeFilter}
            onChange={e => setTimeFilter(e.target.value)}
          >
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
            <option value="all-time">All time</option>
          </select>
        </div>
        
        {history.length === 0 ? (
          <div className="card" style={{ textAlign: 'center', padding: '3rem 1rem' }}>
            <p style={{ margin: 0 }}>No usage history available yet.</p>
          </div>
        ) : (
          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)' }}>
                  <th style={{ padding: '1rem', fontWeight: 500, fontSize: '0.875rem' }}>Session</th>
                  <th style={{ padding: '1rem', fontWeight: 500, fontSize: '0.875rem' }}>Date</th>
                  <th style={{ padding: '1rem', fontWeight: 500, fontSize: '0.875rem' }}>Requested</th>
                  <th style={{ padding: '1rem', fontWeight: 500, fontSize: '0.875rem' }}>Generated</th>
                  <th style={{ padding: '1rem', fontWeight: 500, fontSize: '0.875rem' }}>Reused</th>
                  <th style={{ padding: '1rem', fontWeight: 500, fontSize: '0.875rem' }}>Savings</th>
                </tr>
              </thead>
              <tbody>
                {history.map(session => (
                  <tr key={session.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                    <td style={{ padding: '1rem', fontSize: '0.875rem', fontWeight: 500 }}>{session.title || 'Untitled'}</td>
                    <td style={{ padding: '1rem', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                      {new Date(session.timestamp).toLocaleDateString()}
                    </td>
                    <td style={{ padding: '1rem', fontSize: '0.875rem' }}>{session.metrics?.requested || 0}</td>
                    <td style={{ padding: '1rem', fontSize: '0.875rem' }}>{session.metrics?.generated || 0}</td>
                    <td style={{ padding: '1rem', fontSize: '0.875rem', color: 'var(--success-color)' }}>{session.metrics?.reused || 0}</td>
                    <td style={{ padding: '1rem', fontSize: '0.875rem', color: 'var(--success-color)' }}>{session.metrics?.savings || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
