import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Trash2, FileText, ChevronRight } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { useHistory } from '../hooks/useHistory';
import { formatDate, truncate } from '../lib/utils';
import { DiagnosisRecord, CriticalityLevel } from '../types/nidaan';

export default function HistoryPage() {
  const navigate = useNavigate();
  const { records, clearAll } = useHistory();
  const [filter, setFilter] = useState<'all' | CriticalityLevel>('all');
  
  const filteredRecords = filter === 'all' 
    ? records 
    : records.filter(r => r.result?.criticality === filter);

  const stats = {
    total: records.length,
    high: records.filter(r => r.result?.criticality === 'high').length,
    medium: records.filter(r => r.result?.criticality === 'medium').length,
    low: records.filter(r => r.result?.criticality === 'low').length,
  };

  const handleClear = () => {
    if (window.confirm("Aap sabhi pichle cases delete karna chahte hain?")) {
      clearAll();
    }
  };

  const handleView = (record: DiagnosisRecord) => {
    navigate('/result', { state: { symptoms: record.symptoms, result: record.result, id: record.id } });
  };

  return (
    <div className="flex flex-col min-h-full pb-20">
      <header className="sticky top-0 z-10 bg-background/80 backdrop-blur-md border-b border-border flex items-center justify-between p-4 px-4 h-16 shadow-sm">
        <h2 className="font-bold text-lg font-display text-white">Pichle Cases / Past Cases</h2>
        {records.length > 0 && (
          <button onClick={handleClear} className="p-2 -mr-2 rounded-full text-text-muted hover:text-danger hover:bg-danger/10 transition-colors">
            <Trash2 className="w-5 h-5" />
          </button>
        )}
      </header>

      <div className="p-4">
        {records.length === 0 ? (
          <motion.div 
            initial={{ opacity: 0 }} 
            animate={{ opacity: 1 }}
            className="text-center py-20 flex flex-col items-center"
          >
            <div className="w-20 h-20 bg-surface rounded-full flex items-center justify-center mb-4">
              <FileText className="w-10 h-10 text-border" />
            </div>
            <h3 className="text-white font-medium text-lg mb-1">Abhi tak koi case nahi</h3>
            <p className="text-text-muted">No past cases found. Go to Home to diagnose symptoms.</p>
            <button 
              onClick={() => navigate('/')}
              className="mt-6 px-6 py-2 bg-surface-elevated text-white rounded-full font-medium"
            >
              Go to Home
            </button>
          </motion.div>
        ) : (
          <>
            {/* Stats */}
            {records.length >= 3 && (
              <div className="flex gap-2 bg-surface p-2.5 rounded-xl border border-border mb-4 overflow-x-auto snap-x no-scrollbar">
                 <div className="flex-1 min-w-[70px] snap-start bg-surface-elevated rounded-lg p-2 text-center border border-border/50">
                    <div className="text-xl font-bold text-white">{stats.total}</div>
                    <div className="text-[10px] text-text-muted uppercase tracking-wider">Total</div>
                 </div>
                 <div className="flex-1 min-w-[70px] snap-start bg-danger-bg rounded-lg p-2 text-center border border-danger/20">
                    <div className="text-xl font-bold text-danger">{stats.high}</div>
                    <div className="text-[10px] text-danger/80 uppercase tracking-wider">High</div>
                 </div>
                 <div className="flex-1 min-w-[70px] snap-start bg-warning-bg rounded-lg p-2 text-center border border-warning/20">
                    <div className="text-xl font-bold text-warning">{stats.medium}</div>
                    <div className="text-[10px] text-warning/80 uppercase tracking-wider">Med</div>
                 </div>
                 <div className="flex-1 min-w-[70px] snap-start bg-success-bg rounded-lg p-2 text-center border border-success/20">
                    <div className="text-xl font-bold text-success">{stats.low}</div>
                    <div className="text-[10px] text-success/80 uppercase tracking-wider">Low</div>
                 </div>
              </div>
            )}

            {/* Filters */}
            <div className="flex gap-2 mb-4 overflow-x-auto no-scrollbar pb-1">
              {['all', 'high', 'medium', 'low'].map((f) => (
                <button
                  key={f}
                  onClick={() => setFilter(f as any)}
                  className={`px-4 py-1.5 rounded-full text-xs font-medium uppercase tracking-wider whitespace-nowrap transition-colors ${
                    filter === f 
                      ? 'bg-text-secondary text-background font-bold' 
                      : 'bg-surface border border-border text-text-muted hover:text-white'
                  }`}
                >
                  {f}
                </button>
              ))}
            </div>

            {/* List */}
            <div className="flex flex-col gap-3">
               <AnimatePresence>
                 {filteredRecords.map((record, i) => (
                    <motion.div
                      key={record.id}
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, scale: 0.95 }}
                      transition={{ delay: i * 0.05 }}
                      onClick={() => handleView(record)}
                      className="bg-surface border border-border hover:border-text-muted/30 rounded-xl p-4 cursor-pointer transition-colors group relative overflow-hidden"
                    >
                      <div className="flex gap-3 relative z-10">
                        <div className={`mt-1 w-2.5 h-2.5 rounded-full shrink-0 ${
                          record.result?.criticality === 'high' ? 'bg-danger shadow-[0_0_8px_rgba(239,68,68,0.8)]' : 
                          record.result?.criticality === 'medium' ? 'bg-warning' : 'bg-success'
                        }`} />
                        <div className="flex-1 min-w-0 pr-6">
                           <p className="text-sm text-text-primary mb-1 line-clamp-2 leading-relaxed">
                             "{truncate(record.symptoms, 80)}"
                           </p>
                           <div className="flex items-center gap-2 text-xs font-medium">
                             <span className={`uppercase tracking-wider ${
                               record.result?.criticality === 'high' ? 'text-danger' : 
                               record.result?.criticality === 'medium' ? 'text-warning' : 'text-success'
                             }`}>
                               {record.result?.criticality}
                             </span>
                             <span className="text-border">•</span>
                             <span className="text-text-muted">{formatDate(record.timestamp)}</span>
                           </div>
                        </div>
                        <div className="absolute right-0 top-1/2 -translate-y-1/2 text-text-muted opacity-0 group-hover:opacity-100 transition-opacity">
                          <ChevronRight className="w-5 h-5" />
                        </div>
                      </div>
                    </motion.div>
                 ))}
               </AnimatePresence>
               {filteredRecords.length === 0 && records.length > 0 && (
                 <div className="text-center py-10 text-text-muted text-sm">
                   No cases match the selected filter.
                 </div>
               )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
