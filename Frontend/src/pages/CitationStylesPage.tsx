import React, { useCallback, useEffect, useState } from 'react';
import { Check, FileText, LoaderCircle, Pencil, Plus, RefreshCw, Search, Sparkles, Trash2 } from 'lucide-react';
import { Navbar } from '@/components/layout/Navbar';
import { Sidebar } from '@/components/layout/Sidebar';
import { CitationStyle, createCitationStyle, deleteCitationStyle, listCitationStyles, transformCitation, updateCitationStyle } from '@/api/citationStyles';
import { useAppDispatch } from '@/store/hooks';
import { addToast } from '@/store/slices/uiSlice';

const SAMPLE = '\\\\bibitem{sample2024}\\nJ. Smith and A. Patel, "A Sample Research Paper," \\\\textit{Journal of Example Studies}, vol. 12, no. 3, pp. 45--58, 2024.';
const SOURCE = '\\\\bibitem{source2023}\\nJones, Robert and Emily Chen. Improving Reliable Systems. International Journal of Computing, 8(2): 101-119, 2023.';
const errorText = (error: unknown) => error instanceof Error ? error.message : 'Request failed. Please try again.';

export const CitationStylesPage: React.FC = () => {
  const dispatch = useAppDispatch();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [styles, setStyles] = useState<CitationStyle[]>([]);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [selectedId, setSelectedId] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [sample, setSample] = useState('');
  const [source, setSource] = useState(SOURCE);
  const [result, setResult] = useState('');
  const [error, setError] = useState('');
  const [transformError, setTransformError] = useState('');
  const [warnings, setWarnings] = useState<string[]>([]);

  const selectedStyle = styles.find((style) => style.id === selectedId);

  const loadStyles = useCallback(async (search = query) => {
    setLoading(true);
    setError('');
    try {
      const response = await listCitationStyles({ q: search, limit: 100 });
      setStyles(response.items);
      setSelectedId((current) => response.items.some((style) => style.id === current) ? current : (response.items[0]?.id ?? ''));
    } catch (reason) { setError(errorText(reason)); }
    finally { setLoading(false); }
  }, [query]);

  useEffect(() => { void loadStyles(''); }, []);

  const clearForm = () => { setEditingId(null); setName(''); setDescription(''); setSample(''); };

  const saveStyle = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');
    if (!name.trim() || !sample.trim()) { setError('Enter a style name and a LaTeX bibitem sample.'); return; }
    setBusy(true);
    try {
      const payload = { style_name: name.trim(), description: description.trim() || null, sample_string: sample.trim() };
      const saved = editingId ? await updateCitationStyle(editingId, payload) : await createCitationStyle(payload);
      await loadStyles(query);
      setSelectedId(saved.id);
      dispatch(addToast({ type: 'success', message: editingId ? 'Citation style updated.' : 'Citation style saved and analyzed by Gemini.' }));
      clearForm();
    } catch (reason) { setError(errorText(reason)); }
    finally { setBusy(false); }
  };

  const editStyle = (style: CitationStyle) => {
    setEditingId(style.id); setName(style.style_name); setDescription(style.description || ''); setSample(style.sample_string); setError('');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const removeStyle = async (style: CitationStyle) => {
    if (!window.confirm('Delete "' + style.style_name + '"? This cannot be undone.')) return;
    setBusy(true);
    try {
      await deleteCitationStyle(style.id);
      setStyles((current) => current.filter((item) => item.id !== style.id));
      if (selectedId === style.id) setSelectedId('');
      if (editingId === style.id) clearForm();
      dispatch(addToast({ type: 'success', message: 'Citation style deleted.' }));
    } catch (reason) { dispatch(addToast({ type: 'error', message: errorText(reason) })); }
    finally { setBusy(false); }
  };

  const runTransform = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setTransformError(''); setResult(''); setWarnings([]);
    if (!selectedId) { setTransformError('Create or select a citation style first.'); return; }
    setBusy(true);
    try {
      const response = await transformCitation(selectedId, source.trim());
      setResult(response.reformatted_citation);
      setWarnings(response.diff_summary?.warnings || []);
    } catch (reason) { setTransformError(errorText(reason)); }
    finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen bg-cream flex flex-col font-sans">
      <Navbar onToggleSidebar={() => setSidebarOpen((open) => !open)} />
      <div className="flex flex-1 min-w-0">
        <div id="folder-navigation"><Sidebar mobileOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} /></div>
        <main className="flex-1 min-w-0 px-3 py-4 sm:px-8 sm:py-7">
          <div className="mx-auto max-w-7xl space-y-6">
            <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
              <div><span className="mb-2 inline-flex items-center gap-2 rounded-full border border-indigo-brand/15 bg-white px-3 py-1 text-xs font-mono uppercase tracking-widest text-indigo-brand"><Sparkles className="h-3.5 w-3.5" /> Gemini-powered</span><h1 className="text-2xl font-serif font-bold text-charcoal-900 sm:text-3xl">Custom Citation Styles</h1><p className="mt-2 max-w-2xl text-sm leading-6 text-charcoal-700">Save a LaTeX bibliography example, let Gemini learn its formatting, and reuse that style for citation transformations.</p></div>
              <div className="text-xs font-mono text-charcoal/60">{styles.length} saved styles</div>
            </header>
            <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
              <section className="rounded-2xl border border-border-light bg-white p-4 shadow-sm sm:p-6">
                <div className="mb-5 flex items-center justify-between"><div><h2 className="text-lg font-semibold text-charcoal-900">{editingId ? 'Edit style' : 'Create a style'}</h2><p className="mt-1 text-xs text-charcoal/60">Use a real bibliography entry as the formatting reference.</p></div>{editingId && <button type="button" onClick={clearForm} className="text-xs text-indigo-brand">Cancel edit</button>}</div>
                <form onSubmit={saveStyle} className="space-y-4">
                  <div><label htmlFor="style-name" className="mb-1.5 block text-xs font-semibold">Style name</label><input id="style-name" required maxLength={120} value={name} onChange={(event) => setName(event.target.value)} placeholder="e.g. My University IEEE Variant" className="w-full rounded-xl border border-border-light bg-cream/40 px-3.5 py-3 text-sm outline-none focus:border-indigo-brand" /></div>
                  <div><label htmlFor="style-description" className="mb-1.5 block text-xs font-semibold">Description (optional)</label><input id="style-description" maxLength={255} value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Where this style is used" className="w-full rounded-xl border border-border-light bg-cream/40 px-3.5 py-3 text-sm outline-none focus:border-indigo-brand" /></div>
                  <div><label htmlFor="style-sample" className="mb-1.5 block text-xs font-semibold">Example bibliography entry</label><textarea id="style-sample" required minLength={10} maxLength={12000} rows={7} value={sample} onChange={(event) => setSample(event.target.value)} placeholder={SAMPLE} className="w-full resize-y rounded-xl border border-border-light bg-[#171923] px-3.5 py-3 font-mono text-xs leading-6 text-slate-100 outline-none focus:border-indigo-brand" /><button type="button" onClick={() => setSample(SAMPLE)} className="mt-1 text-[11px] text-indigo-brand hover:underline">Use example</button></div>
                  {error && <p role="alert" className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">{error}</p>}
                  <button type="submit" disabled={busy} className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-brand px-4 py-3 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-60">{busy ? <LoaderCircle className="h-4 w-4 animate-spin" /> : editingId ? <Check className="h-4 w-4" /> : <Plus className="h-4 w-4" />}{busy ? 'Working…' : editingId ? 'Save changes' : 'Save citation style'}</button>
                  <p className="text-[11px] leading-5 text-charcoal/50">Gemini analyzes the sample on save. Keep your API key on the backend only.</p>
                </form>
              </section>
              <section className="rounded-2xl border border-border-light bg-white p-4 shadow-sm sm:p-6">
                <div className="mb-4 flex items-center justify-between gap-3"><div><h2 className="text-lg font-semibold text-charcoal-900">Your style library</h2><p className="mt-1 text-xs text-charcoal/60">Search, select, edit, or delete saved styles.</p></div><button type="button" onClick={() => void loadStyles(query)} disabled={loading} aria-label="Refresh styles" className="rounded-lg border border-border-light p-2 text-charcoal-700 hover:bg-cream-100"><RefreshCw className={loading ? 'h-4 w-4 animate-spin' : 'h-4 w-4'} /></button></div>
                <form onSubmit={(event) => { event.preventDefault(); void loadStyles(query); }} className="mb-4 flex gap-2"><div className="relative min-w-0 flex-1"><Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-charcoal/40" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search styles…" className="w-full rounded-xl border border-border-light bg-cream/40 py-2.5 pl-9 pr-3 text-sm outline-none focus:border-indigo-brand" /></div><button type="submit" className="rounded-xl border border-border-light px-3 text-xs font-semibold hover:bg-cream-100">Search</button></form>
                {loading ? <div className="flex min-h-48 items-center justify-center gap-2 text-sm text-charcoal/60"><LoaderCircle className="h-5 w-5 animate-spin" /> Loading styles…</div> : styles.length === 0 ? <div className="flex min-h-48 flex-col items-center justify-center rounded-xl border border-dashed border-border-light p-5 text-center"><FileText className="mb-3 h-7 w-7 text-indigo-brand" /><p className="text-sm font-semibold">No citation styles found</p><p className="mt-1 text-xs text-charcoal/60">Create your first style using the form.</p></div> : <div className="max-h-[520px] space-y-2 overflow-y-auto pr-1">{styles.map((style) => <div key={style.id} className={style.id === selectedId ? 'rounded-xl border border-indigo-brand/40 bg-indigo-brand/[0.04] p-3.5' : 'rounded-xl border border-border-light p-3.5'}><div className="flex items-start gap-3"><button type="button" onClick={() => setSelectedId(style.id)} className="flex min-w-0 flex-1 items-start gap-3 text-left"><span className="mt-0.5 rounded-lg bg-cream-100 p-2 text-indigo-brand"><FileText className="h-4 w-4" /></span><span className="min-w-0 flex-1"><span className="block text-sm font-semibold text-charcoal-900">{style.style_name}</span><span className="mt-1 block text-xs text-charcoal/60">{style.description || 'No description provided'}</span><span className="mt-2 block truncate rounded-md bg-cream-100 px-2 py-1.5 font-mono text-[10px] text-charcoal/70">{style.sample_string}</span></span></button><div className="flex shrink-0 gap-1"><button type="button" onClick={() => editStyle(style)} aria-label={'Edit ' + style.style_name} className="rounded-lg p-2 text-charcoal/50 hover:bg-cream-100 hover:text-indigo-brand"><Pencil className="h-3.5 w-3.5" /></button><button type="button" onClick={() => void removeStyle(style)} disabled={busy} aria-label={'Delete ' + style.style_name} className="rounded-lg p-2 text-charcoal/50 hover:bg-red-50 hover:text-red-600"><Trash2 className="h-3.5 w-3.5" /></button></div></div></div>)}</div>}
              </section>
            </div>
            <section className="overflow-hidden rounded-2xl border border-border-light bg-white shadow-sm">
              <div className="border-b border-border-light px-4 py-4 sm:px-6"><h2 className="text-lg font-semibold text-charcoal-900">Reformat a citation</h2><p className="mt-1 text-xs text-charcoal/60">Transform a bibliography entry using the selected saved style.</p></div>
              <div className="border-b border-border-light bg-cream-50/60 px-4 py-3 sm:px-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                <div className="flex items-center gap-2.5 flex-1">
                  <Sparkles className="h-4 w-4 text-indigo-brand shrink-0" />
                  <label htmlFor="reformat-style-select" className="text-xs font-semibold text-charcoal-800 shrink-0">
                    Target style:
                  </label>
                  <select
                    id="reformat-style-select"
                    value={selectedId}
                    onChange={(e) => setSelectedId(e.target.value)}
                    disabled={styles.length === 0}
                    className="w-full sm:max-w-md rounded-xl border border-border-light bg-white px-3 py-1.5 text-xs font-medium text-charcoal-900 shadow-xs outline-none focus:border-indigo-brand focus:ring-1 focus:ring-indigo-brand disabled:bg-cream-100"
                  >
                    {styles.length === 0 ? (
                      <option value="">No styles available - save a style above first</option>
                    ) : (
                      styles.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.style_name} {s.description ? `(${s.description})` : ''}
                        </option>
                      ))
                    )}
                  </select>
                </div>
                {selectedStyle && (
                  <span className="text-xs font-mono text-charcoal/70 shrink-0">
                    Selected: <strong className="text-indigo-brand font-semibold">{selectedStyle.style_name}</strong>
                  </span>
                )}
              </div>
              <form onSubmit={runTransform} className="grid grid-cols-1 gap-4 p-4 sm:p-6 lg:grid-cols-2">
                <div>
                  <div className="mb-2 flex items-center justify-between">
                    <label htmlFor="source-citation" className="block text-xs font-semibold">Original citation</label>
                    <div className="flex items-center gap-2">
                      <button type="button" onClick={() => setSource(SOURCE)} className="text-[11px] text-indigo-brand hover:underline">Use example</button>
                      {source && <button type="button" onClick={() => setSource('')} className="text-[11px] text-charcoal/50 hover:text-red-600 hover:underline">Clear</button>}
                    </div>
                  </div>
                  <textarea id="source-citation" required maxLength={12000} rows={9} value={source} onChange={(event) => setSource(event.target.value)} className="w-full resize-y rounded-xl border border-border-light bg-[#171923] px-3.5 py-3 font-mono text-xs leading-6 text-slate-100 outline-none focus:border-indigo-brand" />
                  <button type="submit" disabled={busy || !selectedId} className="mt-3 inline-flex items-center gap-2 rounded-xl bg-indigo-brand px-4 py-3 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50">
                    {busy ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                    Reformat with Gemini {selectedStyle ? `(${selectedStyle.style_name})` : ''}
                  </button>
                </div>
                <div>
                  <div className="mb-2 flex items-center justify-between">
                    <label htmlFor="formatted-result" className="block text-xs font-semibold">Formatted result</label>
                    {result && <button type="button" onClick={() => navigator.clipboard.writeText(result).then(() => dispatch(addToast({ type: 'success', message: 'Citation copied.' }))).catch(() => dispatch(addToast({ type: 'error', message: 'Clipboard access was blocked.' })))} className="text-xs font-semibold text-indigo-brand">Copy result</button>}
                  </div>
                  <textarea id="formatted-result" readOnly rows={9} value={result} placeholder="Your formatted citation will appear here…" className="w-full resize-y rounded-xl border border-border-light bg-cream-50 px-3.5 py-3 font-mono text-xs leading-6 text-charcoal-900 outline-none" />
                  {warnings.length > 0 && (
                    <div className="mt-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 space-y-1">
                      {warnings.map((w, idx) => (
                        <p key={idx}>⚠️ {w}</p>
                      ))}
                    </div>
                  )}
                  {transformError && <p role="alert" className="mt-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">{transformError}</p>}
                </div>
              </form>
            </section>
          </div>
        </main>
      </div>
    </div>
  );
};
